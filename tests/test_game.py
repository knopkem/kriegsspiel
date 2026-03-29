import unittest

from core.game import GameState
from core.map import HexCoord
from core.orders import OrderType
from core.scenario import load_builtin_scenario
from core.units import Formation, MoraleState, Side


class GameStateTestCase(unittest.TestCase):
    def test_turn_engine_resolves_movement_orders(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)

        game.order_book.issue_move("blue-inf-1", HexCoord(3, 9), current_turn=1)
        events = game.advance_turn()

        self.assertEqual(game.units["blue-inf-1"].position, HexCoord(3, 9))
        self.assertTrue(any(event.category == "movement" for event in events))

    def test_turn_engine_resolves_formation_then_attack(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=2)
        game.units["blue-gun-1"].change_formation(Formation.UNLIMBERED)
        game.units["red-gun-1"].change_formation(Formation.UNLIMBERED)

        game.units["blue-gun-1"].position = HexCoord(4, 3)
        game.units["red-inf-1"].position = HexCoord(5, 3)
        game.order_book.issue_attack("blue-gun-1", "red-inf-1", current_turn=1)
        events = game.advance_turn()

        self.assertLess(game.units["red-inf-1"].hit_points, game.units["red-inf-1"].max_hit_points)
        self.assertTrue(any(event.category == "combat" for event in events))

    def test_hold_order_recovers_fatigue(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=3)
        unit = game.units["blue-inf-1"]
        unit.add_fatigue(20)

        game.order_book.issue_hold("blue-inf-1", current_turn=1)
        game.advance_turn()

        self.assertLess(unit.fatigue, 20)

    def test_rally_order_can_improve_morale(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        unit = game.units["blue-inf-1"]
        unit.morale_state = MoraleState.ROUTING

        game.order_book.issue_rally("blue-inf-1", current_turn=1)
        game.advance_turn()

        self.assertIn(unit.morale_state, {MoraleState.ROUTING, MoraleState.SHAKEN})

    def test_score_for_side_counts_objectives_and_enemy_losses(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        game.units["blue-inf-1"].position = HexCoord(8, 9)
        game.units["red-inf-1"].apply_damage(20)

        score = game.score_for_side(Side.BLUE)

        self.assertGreaterEqual(score, 5)

    def test_from_scenario_copies_turn_limit(self) -> None:
        scenario = load_builtin_scenario("assault_on_hill")
        game = GameState.from_scenario(scenario, rng_seed=1)
        self.assertEqual(game.max_turns, 16)


if __name__ == "__main__":
    unittest.main()
