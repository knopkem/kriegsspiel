"""Tests for the procedural skirmish scenario generator (E3)."""

import unittest

from core.game import GameState
from core.scenario_generator import SkirmishConfig, generate_skirmish
from core.units import Side


class SkirmishGeneratorTestCase(unittest.TestCase):
    def test_generates_game_state(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="small", seed=1))
        self.assertIsInstance(game, GameState)

    def test_both_sides_have_units(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="small", seed=2))
        blues = [u for u in game.units.values() if u.side is Side.BLUE]
        reds  = [u for u in game.units.values() if u.side is Side.RED]
        self.assertGreater(len(blues), 0)
        self.assertGreater(len(reds), 0)

    def test_has_objectives(self) -> None:
        game = generate_skirmish(SkirmishConfig(objective_count=3, seed=3))
        self.assertGreaterEqual(len(game.objectives), 1)

    def test_medium_map_size(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="medium", seed=4))
        self.assertEqual(game.battle_map.width, 35)
        self.assertEqual(game.battle_map.height, 28)

    def test_large_map_size(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="large", seed=5))
        self.assertEqual(game.battle_map.width, 55)
        self.assertEqual(game.battle_map.height, 45)

    def test_deterministic_with_seed(self) -> None:
        g1 = generate_skirmish(SkirmishConfig(size="small", seed=99))
        g2 = generate_skirmish(SkirmishConfig(size="small", seed=99))
        self.assertEqual(len(g1.units), len(g2.units))
        ids1 = sorted(g1.units.keys())
        ids2 = sorted(g2.units.keys())
        self.assertEqual(ids1, ids2)

    def test_all_units_have_positions(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="small", seed=10))
        for unit in game.units.values():
            if not unit.is_removed:
                self.assertIsNotNone(unit.position, f"{unit.name} has no position")

    def test_infantry_force_type(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="medium", blue_force="infantry", seed=6))
        from core.units import UnitType
        blues = [u for u in game.units.values() if u.side is Side.BLUE]
        inf = [u for u in blues if u.unit_type is UnitType.INFANTRY]
        cav = [u for u in blues if u.unit_type is UnitType.CAVALRY]
        # Infantry force should have more infantry than cavalry
        self.assertGreaterEqual(len(inf), len(cav))

    def test_advance_turn_doesnt_crash(self) -> None:
        game = generate_skirmish(SkirmishConfig(size="small", seed=77))
        events = game.advance_turn()
        self.assertIsInstance(events, list)

    def test_different_seeds_differ(self) -> None:
        g1 = generate_skirmish(SkirmishConfig(size="small", seed=1))
        g2 = generate_skirmish(SkirmishConfig(size="small", seed=2))
        # Different seeds should produce different map terrain
        from core.map import HexCoord
        same = all(
            g1.battle_map.terrain_at(c) == g2.battle_map.terrain_at(c)
            for c in list(g1.battle_map.coords())[:20]
        )
        self.assertFalse(same, "Different seeds should differ")


if __name__ == "__main__":
    unittest.main()
