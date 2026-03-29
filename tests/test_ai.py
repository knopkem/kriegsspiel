import unittest

from ai.evaluation import BattlefieldEvaluator
from ai.opponent import SimpleAICommander
from core.game import GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario
from core.units import Formation, MoraleState, Side


class AITestCase(unittest.TestCase):
    def test_battlefield_evaluator_rewards_better_side_state(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        evaluator = BattlefieldEvaluator()
        baseline = evaluator.side_score(game, Side.BLUE)

        game.units["red-inf-1"].apply_damage(20)
        improved = evaluator.side_score(game, Side.BLUE)

        self.assertGreater(improved, baseline)

    def test_ai_attacks_visible_target_in_range(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        ai = SimpleAICommander(Side.RED, seed=1)

        game.units["red-inf-1"].position = HexCoord(4, 2)
        game.units["blue-inf-1"].position = HexCoord(3, 2)
        game.visibility = game.fog_engine.update(game.units.values(), current_turn=game.current_turn)
        orders = ai.issue_orders(game)

        self.assertTrue(any(order.target_unit_id == "blue-inf-1" for order in orders))

    def test_ai_retreats_routing_unit(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        ai = SimpleAICommander(Side.RED, seed=2)
        game.units["red-inf-1"].morale_state = MoraleState.ROUTING

        orders = ai.issue_orders(game)

        retreat_orders = [order for order in orders if order.unit_id == "red-inf-1"]
        self.assertEqual(retreat_orders[0].order_type.value, "retreat")

    def test_ai_unlimbers_artillery_before_ranged_attack(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)
        ai = SimpleAICommander(Side.RED, seed=3)
        game.units["red-gun-1"].position = HexCoord(5, 3)
        game.units["blue-inf-1"].position = HexCoord(4, 3)
        game.visibility = game.fog_engine.update(game.units.values(), current_turn=game.current_turn)

        orders = ai.issue_orders(game)

        artillery_orders = [order for order in orders if order.unit_id == "red-gun-1"]
        self.assertEqual(artillery_orders[0].formation, Formation.UNLIMBERED)


if __name__ == "__main__":
    unittest.main()
