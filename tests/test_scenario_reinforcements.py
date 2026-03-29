"""Tests for scenario reinforcement waves (J1-J3)."""
from __future__ import annotations

import unittest

from core.scenario import load_builtin_scenario
from core.game import GameState
from core.units import Side


class ScenarioReinforcementsTest(unittest.TestCase):
    def _game(self, name: str) -> GameState:
        return GameState.from_scenario(load_builtin_scenario(name), rng_seed=1)

    def test_ligny_has_two_reinforcement_waves(self) -> None:
        game = self._game("ligny_1815")
        self.assertEqual(len(game.reinforcements), 2)

    def test_ligny_blue_reinforcements_at_turn_6(self) -> None:
        game = self._game("ligny_1815")
        blue_waves = [w for w in game.reinforcements if w.units and w.units[0].side is Side.BLUE]
        self.assertTrue(blue_waves)
        self.assertEqual(blue_waves[0].turn, 6)
        self.assertEqual(len(blue_waves[0].units), 3)  # 2 inf + 1 cav

    def test_ligny_red_reinforcements_at_turn_8(self) -> None:
        game = self._game("ligny_1815")
        red_waves = [w for w in game.reinforcements if w.units and w.units[0].side is Side.RED]
        self.assertTrue(red_waves)
        self.assertEqual(red_waves[0].turn, 8)
        self.assertEqual(len(red_waves[0].units), 2)  # 1 inf + 1 art

    def test_mockern_has_two_reinforcement_waves(self) -> None:
        game = self._game("mockern_1813")
        self.assertEqual(len(game.reinforcements), 2)

    def test_full_battle_has_four_waves(self) -> None:
        game = self._game("full_battle")
        self.assertEqual(len(game.reinforcements), 4)

    def test_reinforcements_arrive_at_correct_turn(self) -> None:
        """Units from a wave appear on the map exactly on the specified turn."""
        game = self._game("ligny_1815")
        initial_unit_count = len(game.units)
        # Reinforcements for turn 6 are processed during the advance from turn 6 to 7.
        for _ in range(5):
            game.advance_turn()
        self.assertEqual(len(game.units), initial_unit_count)
        # One more turn resolves turn-6 reinforcements.
        game.advance_turn()
        self.assertGreater(len(game.units), initial_unit_count)

    def test_supply_wagons_present_in_ligny(self) -> None:
        from core.units import UnitType
        game = self._game("ligny_1815")
        wagons = [u for u in game.units.values() if u.unit_type is UnitType.SUPPLY_WAGON]
        self.assertGreaterEqual(len(wagons), 2)  # 1 blue + 1 red

    def test_supply_wagons_on_both_sides(self) -> None:
        from core.units import UnitType
        game = self._game("full_battle")
        wagons = [u for u in game.units.values() if u.unit_type is UnitType.SUPPLY_WAGON]
        blue_wagons = [w for w in wagons if w.side is Side.BLUE]
        red_wagons = [w for w in wagons if w.side is Side.RED]
        self.assertGreaterEqual(len(blue_wagons), 1)
        self.assertGreaterEqual(len(red_wagons), 1)

    def test_difficulty_stars_in_all_scenarios(self) -> None:
        import json
        from pathlib import Path
        scenario_dir = Path("data/scenarios")
        for f in scenario_dir.glob("*.json"):
            data = json.loads(f.read_text())
            self.assertIn("difficulty_stars", data, f"{f.name} missing difficulty_stars")
            stars = data["difficulty_stars"]
            self.assertGreaterEqual(stars, 1)
            self.assertLessEqual(stars, 5)


if __name__ == "__main__":
    unittest.main()
