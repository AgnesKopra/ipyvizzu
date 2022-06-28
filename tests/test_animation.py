"""A module for testing the ipyvizzu.animation module."""


import json
import pathlib
import unittest
import jsonschema
import pandas as pd

from ipyvizzu import (
    PlainAnimation,
    Data,
    Config,
    Style,
    Snapshot,
    AnimationMerger,
)


class TestPlainAnimation(unittest.TestCase):
    """A class for testing PlainAnimation() class."""

    def test_plainanimation(self) -> None:
        """A method for testing PlainAnimation().build()."""

        animation = PlainAnimation(geometry="circle")
        self.assertEqual({"geometry": "circle"}, animation.build())


class TestDataSchema(unittest.TestCase):
    """
    A class for testing Data() class.
    It tests data schema validation.
    """

    def setUp(self) -> None:
        self.data = Data()

    def test_schema_dimension_only(self) -> None:
        """
        A method for testing Data().build().
        It raises an error if added dimension without measure.
        """

        self.data.add_dimension("Genres", ["Pop", "Rock"])
        with self.assertRaises(jsonschema.ValidationError):
            self.data.build()

    def test_schema_measure_only(self) -> None:
        """
        A method for testing Data().build().
        It raises an error if added measure without dimension.
        """

        self.data.add_measure("Popularity", [[114, 96]])
        with self.assertRaises(jsonschema.ValidationError):
            self.data.build()

    def test_schema_data_cube_and_series(self) -> None:
        """
        A method for testing Data().build().
        It raises an error if added both dimension/measure and series.
        """

        self.data.add_dimension("Genres", ["Pop", "Rock"])
        self.data.add_measure("Popularity", [[114, 96]])
        self.data.add_series("Kinds", ["Hard"])
        with self.assertRaises(jsonschema.ValidationError):
            self.data.build()

    def test_schema_data_cube_and_records(self) -> None:
        """
        A method for testing Data().build().
        It raises an error if added both dimension/measure and records.
        """

        self.data.add_dimension("Genres", ["Pop", "Rock"])
        self.data.add_measure("Popularity", [[114, 96]])
        self.data.add_records([["Rock", "Hard", 96], ["Pop", "Hard", 114]])
        with self.assertRaises(jsonschema.ValidationError):
            self.data.build()


class TestDataClassmethods(unittest.TestCase):
    """
    A class for testing Data() class.
    It tests classmethods.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.asset_dir = pathlib.Path(__file__).parent / "assets"

    def test_filter(self) -> None:
        """A method for testing Data.filter() method with string."""

        data = Data.filter("filter_expr")
        # instead of build() test with dump() because contains raw js
        self.assertEqual(
            '{"data": {"filter": record => { return (filter_expr) }}}',
            data.dump(),
        )

    def test_filter_can_be_none(self) -> None:
        """A method for testing Data.filter() method with None."""

        data = Data.filter(None)
        # instead of build() test with dump() because contains raw js
        self.assertEqual(
            '{"data": {"filter": null}}',
            data.dump(),
        )

    def test_from_json(self) -> None:
        """A method for testing Data.from_json() method."""

        data = Data.from_json(self.asset_dir / "data_from_json.json")
        self.assertEqual(
            {
                "data": {
                    "dimensions": [
                        {"name": "Genres", "values": ["Rock", "Pop"]},
                        {"name": "Kinds", "values": ["Hard"]},
                    ],
                    "measures": [{"name": "Popularity", "values": [[114, 96]]}],
                }
            },
            data.build(),
        )


class TestData(unittest.TestCase):
    """
    A class for testing Data() class.
    It tests instance methods.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.asset_dir = pathlib.Path(__file__).parent / "assets"

    def setUp(self) -> None:
        self.data = Data()

    def test_set_filter(self) -> None:
        """A method for testing Data().set_filter() method with string."""

        self.data.add_records([["Rock", "Hard", 96], ["Pop", "Hard", 114]])
        self.data.set_filter("filter_expr")
        self.assertEqual(
            '{"data": {"records": '
            + '[["Rock", "Hard", 96], ["Pop", "Hard", 114]], '
            + '"filter": record => { return (filter_expr) }}}',
            self.data.dump(),
        )

    def test_set_filter_can_be_none(self) -> None:
        """A method for testing Data().set_filter() method with None."""

        self.data.add_records([["Rock", "Hard", 96], ["Pop", "Hard", 114]])
        self.data.set_filter(None)
        self.assertEqual(
            '{"data": {"records": [["Rock", "Hard", 96], ["Pop", "Hard", 114]], "filter": null}}',
            self.data.dump(),
        )

    def test_record(self) -> None:
        """A method for testing Data().add_record() method."""

        self.data.add_record(["Rock", "Hard", 96])
        self.data.add_record(["Pop", "Hard", 114])
        self.assertEqual(
            {"data": {"records": [["Rock", "Hard", 96], ["Pop", "Hard", 114]]}},
            self.data.build(),
        )

    def test_records(self) -> None:
        """A method for testing Data().add_records() method."""

        self.data.add_records([["Rock", "Hard", 96], ["Pop", "Hard", 114]])
        self.assertEqual(
            {"data": {"records": [["Rock", "Hard", 96], ["Pop", "Hard", 114]]}},
            self.data.build(),
        )

    def test_series(self) -> None:
        """A method for testing Data().add_series() method with values."""

        self.data.add_series("Genres", ["Rock", "Pop"], type="dimension")
        self.data.add_series("Kinds", ["Hard"])
        self.data.add_series("Popularity", [96, 114], type="measure")
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {
                            "name": "Genres",
                            "type": "dimension",
                            "values": ["Rock", "Pop"],
                        },
                        {"name": "Kinds", "values": ["Hard"]},
                        {"name": "Popularity", "type": "measure", "values": [96, 114]},
                    ]
                }
            },
            self.data.build(),
        )

    def test_series_without_values(self) -> None:
        """A method for testing Data().add_series() method without values."""

        self.data.add_series("Genres", type="dimension")
        self.data.add_series("Kinds", type="dimension")
        self.data.add_series("Popularity", type="measure")
        records = [["Rock", "Hard", 96], ["Pop", "Hard", 114]]
        self.data.add_records(records)
        self.assertEqual(
            {
                "data": {
                    "records": [["Rock", "Hard", 96], ["Pop", "Hard", 114]],
                    "series": [
                        {"name": "Genres", "type": "dimension"},
                        {"name": "Kinds", "type": "dimension"},
                        {"name": "Popularity", "type": "measure"},
                    ],
                }
            },
            self.data.build(),
        )

    def test_data_cube(self) -> None:
        """A method for testing Data().add_dimension() and Data().add_measure() methods."""

        self.data.add_dimension("Genres", ["Pop", "Rock"])
        self.data.add_dimension("Kinds", ["Hard"])
        self.data.add_measure("Popularity", [[114, 96]])
        self.assertEqual(
            {
                "data": {
                    "dimensions": [
                        {"name": "Genres", "values": ["Pop", "Rock"]},
                        {"name": "Kinds", "values": ["Hard"]},
                    ],
                    "measures": [
                        {
                            "name": "Popularity",
                            "values": [[114, 96]],
                        }
                    ],
                }
            },
            self.data.build(),
        )

    def test_data_frame_with_not_df(self) -> None:
        """
        A method for testing Data().add_data_frame() method.
        It raises an error if called with not valid dataframe.
        """

        data = Data()
        with self.assertRaises(TypeError):
            data.add_data_frame("")

    def test_data_frame_with_none(self) -> None:
        """
        A method for testing Data().add_data_frame() method.
        It tests with None.
        """

        data = Data()
        data.add_data_frame(None)
        self.assertEqual(
            {"data": {}},
            data.build(),
        )

    def test_data_frame(self) -> None:
        """
        A method for testing Data().add_data_frame() method.
        It tests with dataframe.
        """

        with open(self.asset_dir / "data_frame_in.json", encoding="UTF-8") as fh_in:
            fc_in = json.load(fh_in)
        with open(self.asset_dir / "data_frame_out.json", encoding="UTF-8") as fh_out:
            fc_out = json.load(fh_out)

        data_frame = pd.DataFrame(fc_in)
        data_frame = data_frame.astype({"PopularityAsDimension": str})
        self.data.add_data_frame(data_frame)
        self.assertEqual(
            fc_out,
            self.data.build(),
        )

    def test_data_frame_na(self) -> None:
        """
        A method for testing Data().add_data_frame() method.
        It tests with dataframe that contains na values.
        """

        data_frame = pd.read_csv(
            self.asset_dir / "data_frame_na.csv", dtype={"PopularityAsDimension": str}
        )
        self.data.add_data_frame(data_frame)
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {
                            "name": "Popularity",
                            "type": "measure",
                            "values": [100.0, 0.0],
                        },
                        {
                            "name": "PopularityAsDimension",
                            "type": "dimension",
                            "values": ["", "100"],
                        },
                    ]
                }
            },
            self.data.build(),
        )

    def test_data_frame_with_pd_series(self) -> None:
        """
        A method for testing Data().add_data_frame() method.
        It tests with pd.Series().
        """

        data = Data()
        data.add_data_frame(pd.Series([1, 2], name="series1"))
        data.add_data_frame(
            pd.Series({"x": 3, "y": 4, "z": 5}, index=["x", "y"], name="series2")
        )
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {"name": "series1", "type": "measure", "values": [1.0, 2.0]},
                        {"name": "series2", "type": "measure", "values": [3.0, 4.0]},
                    ]
                }
            },
            data.build(),
        )

    def test_data_frame_index_with_not_df(self) -> None:
        """
        A method for testing Data().add_data_frame_index() method.
        It raises an error if called with not valid dataframe.
        """

        data = Data()
        with self.assertRaises(TypeError):
            data.add_data_frame_index(data_frame="", name="")

    def test_data_frame_index_with_none_and_none(self) -> None:
        """
        A method for testing Data().add_data_frame_index() method.
        It tests with (None, None).
        """

        data = Data()
        data.add_data_frame_index(data_frame=None, name=None)
        self.assertEqual(
            {"data": {}},
            data.build(),
        )

    def test_data_frame_index_with_df_and_none(self) -> None:
        """
        A method for testing Data().add_data_frame_index() method.
        It tests with (dataframe, None).
        """

        data = Data()
        data_frame = pd.DataFrame(
            pd.Series({"x": 1, "y": 2, "z": 3}, index=["x", "y"], name="series")
        )
        data.add_data_frame_index(data_frame=data_frame, name=None)
        data.add_data_frame(data_frame)
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {"name": "None", "type": "dimension", "values": ["x", "y"]},
                        {"name": "series", "type": "measure", "values": [1.0, 2.0]},
                    ]
                }
            },
            data.build(),
        )

    def test_data_frame_index_with_df_and_index(self) -> None:
        """
        A method for testing Data().add_data_frame_index() method.
        It tests with (dataframe, index).
        """

        data = Data()
        data_frame = pd.DataFrame({"series": [1, 2, 3]}, index=["x", "y", "z"])
        data.add_data_frame_index(data_frame=data_frame, name="Index")
        data.add_data_frame(data_frame)
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {
                            "name": "Index",
                            "type": "dimension",
                            "values": ["x", "y", "z"],
                        },
                        {
                            "name": "series",
                            "type": "measure",
                            "values": [1.0, 2.0, 3.0],
                        },
                    ]
                }
            },
            data.build(),
        )

    def test_data_frame_index_with_pd_series(self) -> None:
        """
        A method for testing Data().add_data_frame_index() method.
        It tests with (pd.Series(), index).
        """

        data = Data()
        data_frame = pd.Series(
            {"x": 1, "y": 2, "z": 3}, index=["x", "y"], name="series"
        )
        data.add_data_frame_index(data_frame=data_frame, name="Index")
        data.add_data_frame(data_frame)
        self.assertEqual(
            {
                "data": {
                    "series": [
                        {"name": "Index", "type": "dimension", "values": ["x", "y"]},
                        {"name": "series", "type": "measure", "values": [1.0, 2.0]},
                    ]
                }
            },
            data.build(),
        )


class TestConfig(unittest.TestCase):
    """A class for testing Config()."""

    def test_config(self) -> None:
        """A method for testing Config().build() method."""

        animation = Config({"color": {"set": ["Genres"]}})
        self.assertEqual({"config": {"color": {"set": ["Genres"]}}}, animation.build())


class TestStyle(unittest.TestCase):
    """A class for testing Style()."""

    def test_style(self) -> None:
        """A method for testing Style().build() with dictionary."""

        animation = Style({"title": {"backgroundColor": "#A0A0A0"}})
        self.assertEqual(
            {"style": {"title": {"backgroundColor": "#A0A0A0"}}}, animation.build()
        )

    def test_style_can_be_none(self) -> None:
        """A method for testing Style().build() with None."""

        animation = Style(None)
        self.assertEqual({"style": None}, animation.build())


class TestSnapshot(unittest.TestCase):
    """A class for testing Snapshot()."""

    def test_snapshot(self) -> None:
        """A method for testing Snapshot().dump()."""

        animation = Snapshot("abc1234")
        self.assertEqual("'abc1234'", animation.dump())

    def test_snapshot_can_not_be_built(self) -> None:
        """
        A method for testing Snapshot().build().
        It raises an error if called.
        """

        animation = Snapshot("abc1234")
        self.assertRaises(NotImplementedError, animation.build)


class TestMerger(unittest.TestCase):
    """A class for testing AnimationMerger()."""

    def setUp(self) -> None:
        self.merger = AnimationMerger()

        self.data = Data()
        self.data.add_record(["Rock", "Hard", 96])

        self.config = Config({"channels": {"label": {"attach": ["Popularity"]}}})

    def test_merge(self) -> None:
        """A method for testing AnimationMerger().merge() with animations."""

        self.merger.merge(self.data)
        self.merger.merge(self.config)
        self.merger.merge(Style({"title": {"backgroundColor": "#A0A0A0"}}))
        self.assertEqual(
            json.dumps(
                {
                    "data": {"records": [["Rock", "Hard", 96]]},
                    "config": {"channels": {"label": {"attach": ["Popularity"]}}},
                    "style": {"title": {"backgroundColor": "#A0A0A0"}},
                }
            ),
            self.merger.dump(),
        )

    def test_merge_none(self) -> None:
        """A method for testing AnimationMerger().merge() with animation that contains None."""

        self.merger.merge(self.config)
        self.merger.merge(Style(None))
        self.assertEqual(
            '{"config": {"channels": {"label": {"attach": ["Popularity"]}}}, "style": null}',
            self.merger.dump(),
        )

    def test_snapshot_can_not_be_merged(self) -> None:
        """
        A method for testing AnimationMerger().merge() with Snapshot().
        It raises an error if called.
        """

        self.merger.merge(self.data)
        self.merger.merge(self.config)
        self.merger.merge(Style({"title": {"backgroundColor": "#A0A0A0"}}))
        self.assertRaises(NotImplementedError, self.merger.merge, Snapshot("abc1234"))

    def test_only_different_animations_can_be_merged(self) -> None:
        """
        A method for testing AnimationMerger().merge() with same types of animations.
        It raises an error if called.
        """

        self.merger.merge(self.data)
        self.merger.merge(self.config)
        self.merger.merge(Style({"title": {"backgroundColor": "#A0A0A0"}}))

        data = Data()
        data.add_record(["Pop", "Hard", 114])

        self.assertRaises(ValueError, self.merger.merge, data)
        self.assertRaises(ValueError, self.merger.merge, Config({"title": "Test"}))
        self.assertRaises(ValueError, self.merger.merge, Style(None))
