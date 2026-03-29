"""Tests for the lightweight MCTS planner."""
import unittest

from ai.difficulty import AIDifficulty
from ai.evaluation import BattlefieldEvaluator
from ai.mcts import MCTSPlanner
from ai.opponent import SimpleAICommander
from core.game import GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario
from core.units import Side


class MCTSPlannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        self.game = GameState.from_scenario(scenario, rng_seed=42)
        self.evaluator = BattlefieldEvaluator()
        # Pick a RED unit with a position for testing
        self.unit = next(
            u
            for u in self.game.units.values()
            if u.side is Side.RED and not u.is_removed and u.position is not None
        )

    def test_planner_does_not_crash(self) -> None:
        """MCTSPlanner.best_move_destination should not raise on a valid game."""
        planner = MCTSPlanner(
            Side.RED, self.evaluator, lookahead_depth=1, n_simulations=5, rng=__import__("random").Random(1)
        )
        candidates = self.game.battle_map.neighbors(self.unit.position)
        # Must not raise
        planner.best_move_destination(self.game, self.unit.id, candidates)

    def test_planner_returns_valid_candidate(self) -> None:
        """best_move_destination should return one of the supplied candidates."""
        planner = MCTSPlanner(
            Side.RED, self.evaluator, lookahead_depth=1, n_simulations=5, rng=__import__("random").Random(2)
        )
        candidates = self.game.battle_map.neighbors(self.unit.position)
        if not candidates:
            self.skipTest("unit has no neighbours on this map")
        result = planner.best_move_destination(self.game, self.unit.id, candidates)
        self.assertIn(result, candidates)

    def test_empty_candidates_returns_none(self) -> None:
        """best_move_destination with an empty list should return None."""
        planner = MCTSPlanner(Side.RED, self.evaluator, lookahead_depth=1, n_simulations=5)
        result = planner.best_move_destination(self.game, self.unit.id, [])
        self.assertIsNone(result)

    def test_lookahead_depth_zero_no_planner(self) -> None:
        """SimpleAICommander with lookahead_depth=0 profile (EASY) should have mcts=None."""
        ai = SimpleAICommander(Side.RED, difficulty=AIDifficulty.EASY, seed=1)
        self.assertIsNone(ai.mcts)


if __name__ == "__main__":
    unittest.main()
