import unittest

from core.game import GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario


class ReplayRecorderTestCase(unittest.TestCase):
    def test_replay_captures_initial_and_post_turn_frames(self) -> None:
        scenario = load_builtin_scenario("skirmish_small")
        game = GameState.from_scenario(scenario, rng_seed=1)

        self.assertEqual(len(game.replay.frames), 1)

        game.order_book.issue_move("blue-inf-1", HexCoord(3, 2), current_turn=1)
        game.advance_turn()

        self.assertEqual(len(game.replay.frames), 2)
        self.assertEqual(game.replay.frames[1].turn, 1)
        self.assertIn("blue-inf-1", game.replay.frames[1].units)


if __name__ == "__main__":
    unittest.main()
