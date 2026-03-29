"""Tests for core/scenario_editor.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.map import HexCoord, TerrainType
from core.scenario_editor import EditorObjective, ScenarioEditor


def _make_editor(w: int = 8, h: int = 6) -> ScenarioEditor:
    return ScenarioEditor.blank(width=w, height=h, scenario_id="test", title="Test")


class TestBlankEditor(unittest.TestCase):

    def test_dimensions(self):
        ed = _make_editor(8, 6)
        self.assertEqual(ed.width, 8)
        self.assertEqual(ed.height, 6)

    def test_default_terrain_is_open(self):
        ed = _make_editor()
        self.assertEqual(ed.terrain_at(HexCoord(0, 0)), TerrainType.OPEN)

    def test_out_of_bounds_raises(self):
        ed = _make_editor(4, 4)
        with self.assertRaises(ValueError):
            ed.terrain_at(HexCoord(10, 10))


class TestPaintTerrain(unittest.TestCase):

    def test_paint_single_hex(self):
        ed = _make_editor()
        ed.paint_terrain(HexCoord(2, 3), TerrainType.FOREST)
        self.assertEqual(ed.terrain_at(HexCoord(2, 3)), TerrainType.FOREST)

    def test_paint_out_of_bounds_no_crash(self):
        ed = _make_editor(4, 4)
        ed.paint_terrain(HexCoord(99, 99), TerrainType.HILL)  # should silently skip

    def test_fill_rect(self):
        ed = _make_editor(8, 6)
        ed.fill_rect(HexCoord(1, 1), HexCoord(3, 3), TerrainType.HILL)
        self.assertEqual(ed.terrain_at(HexCoord(2, 2)), TerrainType.HILL)
        self.assertEqual(ed.terrain_at(HexCoord(0, 0)), TerrainType.OPEN)


class TestUnitManagement(unittest.TestCase):

    def _spec(self, uid="b1", side="blue", typ="infantry", pos=(2, 2)):
        return {"id": uid, "name": "1st", "side": side, "type": typ, "position": list(pos)}

    def test_place_unit(self):
        ed = _make_editor()
        ed.place_unit(self._spec())
        self.assertEqual(len(ed.units), 1)

    def test_place_replaces_duplicate_id(self):
        ed = _make_editor()
        ed.place_unit(self._spec(pos=(1, 1)))
        ed.place_unit(self._spec(pos=(2, 2)))
        self.assertEqual(len(ed.units), 1)
        self.assertEqual(ed.units[0]["position"], [2, 2])

    def test_remove_unit(self):
        ed = _make_editor()
        ed.place_unit(self._spec())
        self.assertTrue(ed.remove_unit("b1"))
        self.assertEqual(len(ed.units), 0)

    def test_remove_nonexistent_returns_false(self):
        ed = _make_editor()
        self.assertFalse(ed.remove_unit("xxx"))

    def test_move_unit(self):
        ed = _make_editor()
        ed.place_unit(self._spec(pos=(1, 1)))
        ed.move_unit("b1", HexCoord(3, 4))
        self.assertEqual(ed.units[0]["position"], [3, 4])

    def test_units_at(self):
        ed = _make_editor()
        ed.place_unit(self._spec(uid="b1", pos=(2, 2)))
        ed.place_unit(self._spec(uid="b2", pos=(3, 3)))
        self.assertEqual(len(ed.units_at(HexCoord(2, 2))), 1)
        self.assertEqual(len(ed.units_at(HexCoord(0, 0))), 0)

    def test_invalid_unit_type_raises(self):
        ed = _make_editor()
        with self.assertRaises(ValueError):
            ed.place_unit({"id": "x", "name": "x", "side": "blue", "type": "tank", "position": [1, 1]})

    def test_missing_field_raises(self):
        ed = _make_editor()
        with self.assertRaises(ValueError):
            ed.place_unit({"id": "x"})


class TestObjectiveManagement(unittest.TestCase):

    def _obj(self, oid="o1", q=2, r=2):
        return EditorObjective(objective_id=oid, label="HQ", q=q, r=r, points=3)

    def test_place_objective(self):
        ed = _make_editor()
        ed.place_objective(self._obj())
        self.assertEqual(len(ed.objectives), 1)

    def test_place_replaces_duplicate_id(self):
        ed = _make_editor()
        ed.place_objective(self._obj(q=1, r=1))
        ed.place_objective(self._obj(q=3, r=3))
        self.assertEqual(len(ed.objectives), 1)
        self.assertEqual(ed.objectives[0].q, 3)

    def test_remove_objective(self):
        ed = _make_editor()
        ed.place_objective(self._obj())
        self.assertTrue(ed.remove_objective("o1"))
        self.assertEqual(len(ed.objectives), 0)

    def test_objectives_at(self):
        ed = _make_editor()
        ed.place_objective(self._obj(q=2, r=2))
        self.assertEqual(len(ed.objectives_at(HexCoord(2, 2))), 1)
        self.assertEqual(len(ed.objectives_at(HexCoord(0, 0))), 0)


class TestUndo(unittest.TestCase):

    def test_undo_terrain(self):
        ed = _make_editor()
        ed.paint_terrain(HexCoord(1, 1), TerrainType.HILL)
        ed.undo()
        self.assertEqual(ed.terrain_at(HexCoord(1, 1)), TerrainType.OPEN)

    def test_undo_empty_stack_returns_false(self):
        ed = _make_editor()
        self.assertFalse(ed.undo())

    def test_undo_unit_placement(self):
        ed = _make_editor()
        spec = {"id": "b1", "name": "x", "side": "blue", "type": "infantry", "position": [1, 1]}
        ed.place_unit(spec)
        ed.undo()
        self.assertEqual(len(ed.units), 0)


class TestValidation(unittest.TestCase):

    def _valid_editor(self) -> ScenarioEditor:
        ed = _make_editor(8, 6)
        ed.place_unit({"id": "b1", "name": "Blue", "side": "blue", "type": "infantry", "position": [1, 1]})
        ed.place_unit({"id": "r1", "name": "Red", "side": "red", "type": "infantry", "position": [5, 4]})
        ed.place_objective(EditorObjective("o1", "Flag", 4, 3))
        return ed

    def test_valid_has_no_errors(self):
        ed = self._valid_editor()
        self.assertEqual(ed.validate(), [])

    def test_missing_blue_units(self):
        ed = self._valid_editor()
        ed.remove_unit("b1")
        errors = ed.validate()
        self.assertTrue(any("blue" in e for e in errors))

    def test_missing_objectives(self):
        ed = self._valid_editor()
        ed.remove_objective("o1")
        errors = ed.validate()
        self.assertTrue(any("objective" in e for e in errors))

    def test_duplicate_unit_ids(self):
        ed = _make_editor()
        spec = {"id": "dup", "name": "x", "side": "blue", "type": "infantry", "position": [1, 1]}
        ed.units = [spec, spec.copy()]
        errors = ed.validate()
        self.assertTrue(any("duplicate" in e for e in errors))


class TestSaveLoad(unittest.TestCase):

    def _valid_editor(self) -> ScenarioEditor:
        ed = _make_editor(8, 6)
        ed.paint_terrain(HexCoord(3, 2), TerrainType.FOREST)
        ed.place_unit({"id": "b1", "name": "Blue", "side": "blue", "type": "infantry", "position": [1, 1]})
        ed.place_unit({"id": "r1", "name": "Red", "side": "red", "type": "infantry", "position": [6, 4]})
        ed.place_objective(EditorObjective("o1", "Hill", 4, 3, points=5))
        return ed

    def test_save_roundtrip(self):
        ed = self._valid_editor()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ed.save(path)
        loaded = ScenarioEditor.from_json(path)
        self.assertEqual(loaded.scenario_id, "test")
        self.assertEqual(loaded.terrain_at(HexCoord(3, 2)), TerrainType.FOREST)
        self.assertEqual(len(loaded.units), 2)
        self.assertEqual(len(loaded.objectives), 1)
        self.assertEqual(loaded.objectives[0].points, 5)

    def test_save_invalid_raises(self):
        ed = ScenarioEditor.blank(width=8, height=6, scenario_id="x", title="X")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        with self.assertRaises(ValueError):
            ed.save(path)  # no units or objectives

    def test_to_dict_map_rows_correct_width(self):
        ed = _make_editor(8, 6)
        ed.place_unit({"id": "b1", "name": "B", "side": "blue", "type": "infantry", "position": [1, 1]})
        ed.place_unit({"id": "r1", "name": "R", "side": "red", "type": "infantry", "position": [6, 4]})
        ed.place_objective(EditorObjective("o1", "F", 4, 3))
        d = ed.to_dict()
        self.assertEqual(len(d["map_rows"]), 6)
        self.assertTrue(all(len(row) == 8 for row in d["map_rows"]))

    def test_saved_json_loadable_by_scenario_loader(self):
        """The saved file must be parseable by the official scenario loader."""
        from core.scenario import load_scenario
        ed = self._valid_editor()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        ed.save(path)
        scenario = load_scenario(Path(path))
        self.assertEqual(scenario.scenario_id, "test")
        self.assertEqual(len(scenario.units), 2)


if __name__ == "__main__":
    unittest.main()
