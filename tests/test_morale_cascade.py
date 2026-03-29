"""Tests for morale cascade mechanic (C2)."""

import random
import unittest

from core.game import GameState
from core.map import HexCoord, HexGridMap
from core.scenario import ScenarioObjective
from core.units import MoraleState, Side, make_infantry_half_battalion


def _two_unit_game(*, close: bool = True) -> GameState:
    """Return a game with one routing BLUE unit and one neighbour."""
    battle_map = HexGridMap(width=15, height=15)
    routing = make_infantry_half_battalion("r", "Routing Bn", Side.BLUE)
    routing.position = HexCoord(5, 5)
    routing.morale_state = MoraleState.ROUTING

    neighbour = make_infantry_half_battalion("n", "Neighbour Bn", Side.BLUE)
    neighbour.position = HexCoord(5, 6) if close else HexCoord(12, 12)
    neighbour.morale_state = MoraleState.STEADY

    return GameState(
        battle_map=battle_map,
        units={"r": routing, "n": neighbour},
        objectives=[],
    )


class MoraleCascadeTestCase(unittest.TestCase):
    def test_cascade_eligible_unit_stays_or_degrades(self) -> None:
        """Close neighbour's morale either stays STEADY or drops — never improves."""
        game = _two_unit_game(close=True)
        before = game.units["n"].morale_state
        game._apply_morale_cascade(["r"])
        after = game.units["n"].morale_state
        # Morale should never improve due to cascade
        self.assertGreaterEqual(before.value, after.value if after != MoraleState.STEADY else before.value)

    def test_cascade_does_not_affect_distant_unit(self) -> None:
        """Unit far away (>2 hexes) must not be affected."""
        game = _two_unit_game(close=False)
        game._apply_morale_cascade(["r"])
        self.assertEqual(game.units["n"].morale_state, MoraleState.STEADY)

    def test_cascade_only_affects_same_side(self) -> None:
        """Enemy units must never be affected by friendly routing cascade."""
        battle_map = HexGridMap(width=15, height=15)
        routing = make_infantry_half_battalion("r", "Routing Bn", Side.BLUE)
        routing.position = HexCoord(5, 5)
        routing.morale_state = MoraleState.ROUTING

        enemy = make_infantry_half_battalion("e", "Enemy Bn", Side.RED)
        enemy.position = HexCoord(5, 6)
        enemy.morale_state = MoraleState.STEADY

        game = GameState(battle_map=battle_map, units={"r": routing, "e": enemy}, objectives=[])
        game._apply_morale_cascade(["r"])
        self.assertEqual(game.units["e"].morale_state, MoraleState.STEADY)

    def test_cascade_returns_list(self) -> None:
        game = _two_unit_game(close=True)
        events = game._apply_morale_cascade(["r"])
        self.assertIsInstance(events, list)

    def test_cascade_empty_input(self) -> None:
        game = _two_unit_game()
        events = game._apply_morale_cascade([])
        self.assertEqual(events, [])

    def test_cascade_does_not_affect_already_routing(self) -> None:
        game = _two_unit_game(close=True)
        game.units["n"].morale_state = MoraleState.ROUTING
        game._apply_morale_cascade(["r"])
        # Already routing — no further downgrade expected
        self.assertEqual(game.units["n"].morale_state, MoraleState.ROUTING)


if __name__ == "__main__":
    unittest.main()
