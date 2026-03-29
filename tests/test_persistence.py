"""Tests for save/load game persistence."""

import json
import os
import tempfile
import unittest

from core.game import GameState
from core.map import HexCoord, HexGridMap, TerrainType
from core.persistence import load_game, save_game
from core.scenario import ScenarioObjective
from core.units import Side, make_infantry_half_battalion


def _minimal_game() -> GameState:
    battle_map = HexGridMap(width=10, height=8)
    blue = make_infantry_half_battalion("b1", "Blue Bn", Side.BLUE)
    blue.position = HexCoord(2, 2)
    red = make_infantry_half_battalion("r1", "Red Bn", Side.RED)
    red.position = HexCoord(7, 5)
    obj = ScenarioObjective(
        objective_id="hill",
        label="Hill",
        position=HexCoord(5, 4),
        points=5,
    )
    return GameState(
        battle_map=battle_map,
        units={"b1": blue, "r1": red},
        objectives=[obj],
    )


class SaveLoadTestCase(unittest.TestCase):
    def test_save_creates_file(self) -> None:
        game = _minimal_game()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            os.unlink(path)

    def test_save_produces_valid_json(self) -> None:
        game = _minimal_game()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            save_game(game, path)
            with open(path) as fh:
                data = json.load(fh)
            self.assertIn("units", data)
            self.assertIn("map", data)
            self.assertIn("current_turn", data)
        finally:
            os.unlink(path)

    def test_roundtrip_turn(self) -> None:
        game = _minimal_game()
        game.current_turn = 7
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            loaded = load_game(path)
            self.assertEqual(loaded.current_turn, 7)
        finally:
            os.unlink(path)

    def test_roundtrip_unit_count(self) -> None:
        game = _minimal_game()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            loaded = load_game(path)
            self.assertEqual(len(loaded.units), 2)
        finally:
            os.unlink(path)

    def test_roundtrip_unit_positions(self) -> None:
        game = _minimal_game()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            loaded = load_game(path)
            self.assertEqual(loaded.units["b1"].position, HexCoord(2, 2))
            self.assertEqual(loaded.units["r1"].position, HexCoord(7, 5))
        finally:
            os.unlink(path)

    def test_roundtrip_objectives(self) -> None:
        game = _minimal_game()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            loaded = load_game(path)
            self.assertEqual(len(loaded.objectives), 1)
            self.assertEqual(loaded.objectives[0].objective_id, "hill")
        finally:
            os.unlink(path)

    def test_roundtrip_unit_hp(self) -> None:
        game = _minimal_game()
        game.units["b1"].hit_points = 40
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_game(game, path)
            loaded = load_game(path)
            self.assertEqual(loaded.units["b1"].hit_points, 40)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
