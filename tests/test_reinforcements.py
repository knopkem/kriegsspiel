"""Tests for reinforcement wave mechanics."""

import unittest

from core.game import GameState, ReinforcementWave
from core.map import HexCoord, HexGridMap
from core.units import Side, make_infantry_half_battalion, make_cavalry_squadron


def _make_game() -> GameState:
    grid = HexGridMap.from_terrain_rows(["........", "........", "........"])
    blue = make_infantry_half_battalion("b1", "Blue 1st", Side.BLUE, position=HexCoord(0, 0))
    red = make_infantry_half_battalion("r1", "Red 1st", Side.RED, position=HexCoord(7, 0))
    return GameState(battle_map=grid, units={"b1": blue, "r1": red}, rng_seed=1)


class TestReinforcementWaves(unittest.TestCase):
    def test_units_arrive_on_correct_turn(self) -> None:
        game = _make_game()
        reinf = make_infantry_half_battalion("b2", "Blue 2nd", Side.BLUE)
        wave = ReinforcementWave(turn=2, units=[reinf], entry_coords=[HexCoord(0, 1)])
        game.reinforcements.append(wave)

        # Turn 1: no arrival yet
        events = game.advance_turn()
        self.assertNotIn("b2", game.units)
        self.assertFalse(any(e.category == "ReinforcementArrival" for e in events))

        # Turn 2: unit arrives
        events = game.advance_turn()
        self.assertIn("b2", game.units)
        self.assertEqual(game.units["b2"].position, HexCoord(0, 1))
        self.assertTrue(any(e.category == "ReinforcementArrival" for e in events))

    def test_unit_placed_at_next_available_coord(self) -> None:
        game = _make_game()
        # Occupy the first entry coord with an existing unit
        game.units["b1"].position = HexCoord(0, 1)
        u1 = make_infantry_half_battalion("rw1", "Reinf 1", Side.BLUE)
        u2 = make_infantry_half_battalion("rw2", "Reinf 2", Side.BLUE)
        wave = ReinforcementWave(
            turn=2,
            units=[u1, u2],
            entry_coords=[HexCoord(0, 1), HexCoord(0, 2)],
        )
        game.reinforcements.append(wave)

        game.advance_turn()
        events = game.advance_turn()

        # u1 should skip occupied HexCoord(0,1) and land on HexCoord(0,2)
        self.assertIn("rw1", game.units)
        self.assertEqual(game.units["rw1"].position, HexCoord(0, 2))
        # u2 has no remaining coords
        self.assertIn("rw2", game.units)
        arrival_events = [e for e in events if e.category == "ReinforcementArrival"]
        self.assertEqual(len(arrival_events), 2)

    def test_multiple_waves_on_different_turns(self) -> None:
        game = _make_game()
        w1 = ReinforcementWave(
            turn=2,
            units=[make_cavalry_squadron("bc1", "Cav 1", Side.BLUE)],
            entry_coords=[HexCoord(1, 0)],
        )
        w2 = ReinforcementWave(
            turn=3,
            units=[make_cavalry_squadron("bc2", "Cav 2", Side.RED)],
            entry_coords=[HexCoord(6, 0)],
        )
        game.reinforcements.extend([w1, w2])

        game.advance_turn()  # turn 1
        self.assertNotIn("bc1", game.units)

        game.advance_turn()  # turn 2
        self.assertIn("bc1", game.units)
        self.assertNotIn("bc2", game.units)

        game.advance_turn()  # turn 3
        self.assertIn("bc2", game.units)
        self.assertEqual(game.units["bc2"].position, HexCoord(6, 0))

    def test_reinforcement_event_logged(self) -> None:
        game = _make_game()
        unit = make_infantry_half_battalion("b3", "Blue 3rd", Side.BLUE)
        wave = ReinforcementWave(turn=1, units=[unit], entry_coords=[HexCoord(0, 2)])
        game.reinforcements.append(wave)

        events = game.advance_turn()
        self.assertTrue(any(
            e.category == "ReinforcementArrival" and "Blue 3rd" in e.message
            for e in events
        ))
        self.assertTrue(any(
            e.category == "ReinforcementArrival" and "Blue 3rd" in e.message
            for e in game.event_log
        ))


if __name__ == "__main__":
    unittest.main()
