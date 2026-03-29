import unittest

from core.game import GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario
from core.tutorial import TutorialDirector


class TutorialDirectorTestCase(unittest.TestCase):
    def test_tutorial_advances_after_move_and_combat(self) -> None:
        scenario = load_builtin_scenario("tutorial")
        game = GameState.from_scenario(scenario, rng_seed=1)
        tutorial = TutorialDirector()

        self.assertEqual(tutorial.current_step.title, "Move")

        game.order_book.issue_move("blue-inf-1", HexCoord(2, 2), current_turn=1)
        game.advance_turn()
        tutorial.update(game)
        self.assertEqual(tutorial.current_step.title, "Attack")

        game.units["red-inf-1"].position = HexCoord(3, 2)
        game.order_book.issue_attack("blue-inf-1", "red-inf-1", current_turn=2)
        game.advance_turn()
        tutorial.update(game)
        self.assertEqual(tutorial.current_step.title, "Rally & Hold")


if __name__ == "__main__":
    unittest.main()
