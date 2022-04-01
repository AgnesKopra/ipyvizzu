"""
Jupyter notebook integration for Vizzu.
"""

import json
import abc
import typing
import uuid
import enum
import pkgutil
from textwrap import indent, dedent
import numpy as np

from IPython.display import display_html, display_javascript
from IPython import get_ipython


class DisplayTarget(str, enum.Enum):

    BEGIN = "begin"
    END = "end"
    ACTUAL = "actual"


class DisplayTemplate:

    INIT ="""
            {ipyjs}
            window.ipyvizzu = new window.IpyVizzu(element, "{c_id}", "{vizzu}", "{div_width}", "{div_height}");
        """

    CLEAR_INHIBITSCROLL = "window.IpyVizzu.clearInhibitScroll();"
    ANIMATE = "window.ipyvizzu.animate(element, '{display_target}','{c_id}', {scroll}, {chartTarget}, {chartAnimOpts});"
    STORE = "window.ipyvizzu.store('{id}', '{c_id}');"
    FEATURE = "window.ipyvizzu.feature('{c_id}', {name}, {enabled});"
    STORED = "window.ipyvizzu.stored('{id}')";


class RawJavaScript:
    def __init__(self, raw: typing.Optional[str]):
        self._raw = raw

    @property
    def raw(self):
        return self._raw


class RawJavaScriptEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self._raw_replacements = {}

    def default(self, o):
        if isinstance(o, RawJavaScript):
            key = uuid.uuid4().hex
            self._raw_replacements[key] = o.raw
            return key
        return json.JSONEncoder.default(self, o)

    def encode(self, o):
        result = json.JSONEncoder.encode(self, o)
        for key, val in self._raw_replacements.items():
            result = result.replace(f'"{key}"', val)
        return result


class Animation:
    def dump(self):
        return json.dumps(self.build(), cls=RawJavaScriptEncoder)

    @abc.abstractmethod
    def build(self) -> typing.Mapping:
        """
        Return a dict with native python values that can be converted into json.
        """


class PlainAnimation(dict, Animation):
    def build(self):
        return self


class InferType(enum.Enum):

    DIMENSION = "dimension"
    MEASURE = "measure"
    AUTO = None


class Data(dict, Animation):
    """
    Vizzu data with the required keys: records, series, dimensions or measures.
    """

    @classmethod
    def filter(cls, filter_expr):
        data = cls()
        data.set_filter(filter_expr)
        return data

    def set_filter(self, filter_expr):
        filter_expr = (
            RawJavaScript(f"record => {{ return ({filter_expr}) }}")
            if filter_expr is not None
            else filter_expr
        )
        self.update({"filter": filter_expr})

    @classmethod
    def from_json(cls, filename):
        with open(filename, "r", encoding="utf8") as file_desc:
            return cls(json.load(file_desc))

    def add_record(self, record):
        self._add_value("records", record)

    def add_records(self, records):
        list(map(self.add_record, records))

    def add_series(self, name, values=None, **kwargs):
        self._add_named_value("series", name, values, **kwargs)

    def add_dimension(self, name, values=None, **kwargs):
        self._add_named_value("dimensions", name, values, **kwargs)

    def add_measure(self, name, values=None, **kwargs):
        self._add_named_value("measures", name, values, **kwargs)

    def add_data_frame(
        self,
        data_frame,
        infer_types=None,
        default_measure_value=0,
        default_dimension_value="",
    ):
        if infer_types is None:
            infer_types = {}
        for name in data_frame.columns:
            infer_type = InferType(infer_types.get(name, InferType.AUTO))
            if infer_type == InferType.AUTO:
                if isinstance(data_frame[name].values[0], (np.float64, np.int64)):
                    infer_type = InferType.MEASURE
                else:
                    infer_type = InferType.DIMENSION

            values = []
            if infer_type == InferType.MEASURE:
                values = [
                    float(i)
                    for i in data_frame[name].fillna(default_measure_value).values
                ]
            else:
                values = [
                    str(i)
                    for i in data_frame[name].fillna(default_dimension_value).values
                ]

            self.add_series(
                name,
                values,
                type=infer_type.value,
            )

    def _add_named_value(self, dest, name, values=None, **kwargs):
        value = {"name": name, **kwargs}

        if values is not None:
            value["values"] = values

        self._add_value(dest, value)

    def _add_value(self, dest, value):
        self.setdefault(dest, []).append(value)

    def build(self):
        return {"data": self}


class Config(dict, Animation):
    def build(self):
        return {"config": self}


class Style(Animation):
    def __init__(self, data: typing.Optional[dict]):
        self._data = data

    def build(self):
        return {"style": self._data}


class Snapshot(Animation):
    def __init__(self, name: str):
        self._name = name

    def dump(self):
        return DisplayTemplate.STORED.format(id=self._name)

    def build(self):
        raise NotImplementedError("Snapshot cannot be merged with other Animations")


class AnimationMerger(dict, Animation):
    def build(self):
        return self

    def merge(self, animation: Animation):
        data = self._validate(animation)
        self.update(data)

    def _validate(self, animation):
        data = animation.build()
        common_keys = set(data).intersection(self)

        if common_keys:
            raise ValueError(f"Animation is already merged: {common_keys}")

        return data


class Method:
    @abc.abstractmethod
    def dump(self):
        pass


class Animate(Method):
    def __init__(self, data, option=None):
        self._data = data
        self._option = option

    def dumpConfig(self):
        return self._data.dump()

    def dumpAnimOpts(self):
        if self._option:
            return PlainAnimation(self._option).dump()
        else:
            return "undefined"


class Feature(Method):
    def __init__(self, name, value):
        self._name = name
        self._value = value

    def dumpName(self):
        return json.dumps(self._name)

    def dumpValue(self):
        return json.dumps(self._value)


class Chart:
    """
    Wrapper over Vizzu Chart
    """

    VIZZU = "https://cdn.jsdelivr.net/npm/vizzu@~0.4.0/dist/vizzu.min.js"

    def __init__(
        self,
        vizzu=VIZZU,
        width="800px",
        height="480px",
        display: DisplayTarget = DisplayTarget("actual"),
    ):
        self._c_id = uuid.uuid4().hex[:7]
        self._vizzu = vizzu
        self._div_width = width
        self._div_height = height
        self._display_target = DisplayTarget(display)
        self._scroll_into_view = True

        ipy = get_ipython()
        if ipy is not None:
            ipy.events.register("pre_run_cell", self._pre_run_cell)

        ipyjs = pkgutil.get_data(__name__, "templates/ipyvizzu.js").decode("utf-8")

        self._display(
            DisplayTemplate.INIT.format(
                ipyjs = ipyjs,
                c_id=self._c_id,
                vizzu=self._vizzu,
                div_width=self._div_width,
                div_height=self._div_height,
            )
        )

    def _pre_run_cell(self):
        self._display(DisplayTemplate.CLEAR_INHIBITSCROLL.format())

    @property
    def scroll_into_view(self):
        return self._scroll_into_view

    @scroll_into_view.setter
    def scroll_into_view(self, scroll_into_view):
        self._scroll_into_view = bool(scroll_into_view)

    def feature(self, name, value):
        feature = Feature(name, value)
        self._display(
            DisplayTemplate.FEATURE.format(
                c_id=self._c_id,
                name=feature.dumpName(),
                enabled=feature.dumpValue(),
            )
        )

    def animate(self, *animations: Animation, **options):
        """
        Show new animation.
        """
        if not animations:
            raise ValueError("No animation was set.")

        animation = self._merge_animations(animations)
        animate = Animate(animation, options)

        chartTarget = animate.dumpConfig()
        chartAnimOpts = animate.dumpAnimOpts()

        self._display(
            DisplayTemplate.ANIMATE.format(
                display_target=self._display_target,
                c_id=self._c_id,
                animation=animation,
                scroll=str(self._scroll_into_view).lower(),
                chartTarget=chartTarget,
                chartAnimOpts=chartAnimOpts,
            )
        )

    @staticmethod
    def _merge_animations(animations):
        if len(animations) == 1:
            return animations[0]

        merger = AnimationMerger()
        for animation in animations:
            merger.merge(animation)

        return merger

    def store(self) -> Snapshot:
        snapshot_id = uuid.uuid4().hex[:7]
        self._display(DisplayTemplate.STORE.format(id=snapshot_id, c_id=self._c_id))
        return Snapshot(snapshot_id)

    @staticmethod
    def _display(code):
        display_javascript(code, raw=True)
