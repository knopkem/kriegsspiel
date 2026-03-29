import unittest

from core.game import GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario
from core.tutorial import TutorialDirector


class TutorialDirectorTestCase(unittest.TestCase):
    def test_initial_step_is_step_zero(self) -> None:
        tutorial = TutorialDirector()
        self.assertEqual(tutorial.current_index, 0)
        self.assertIn("Select", tutorial.current_step.title)

    def test_tutorial_advances_after_move(self) -> None:
        scenario = load_builtin_scenario("tutorial")
        game = GameState.from_scenario(scenario, rng_seed=1)
        tutorial = TutorialDirector()

        game.order_book.issue_move("blue-inf-1", HexCoord(2, 2), current_turn=1)
        game.advance_turn()
        tutorial.update(game)
        # Should be on step 1 (terrain) or later
        self.assertGreaterEqual(tutorial.current_index, 1)

    def test_tutorial_advances_after_combat(self) -> None:
        scenario = load_builtin_scenario("tutorial")
        game = GameState.from_scenario(scenario, rng_seed=1)
        tutorial = TutorialDirector()

        # Step 0: resolve a move
        game.order_book.issue_move("blue-inf-1", HexCoord(2, 2), current_turn=1)
        game.advance_turn()
        tutorial.update(game)
        self.assertGreaterEqual(tutorial.current_index, 1)

        # Step 1 advances at turn >= 2 (already true)
        game.advance_turn()
        tutorial.update(game)
        self.assertGreaterEqual(tutorial.current_index, 2)

        # Step 2 needs formation change, skip manually for test speed
        tutorial.current_index = 3

        # Step 3: trigger combat
        game.units["red-inf-1"].position = HexCoord(3, 2)
        game.order_book.issue_attack("blue-inf-1", "red-inf-1", current_turn=3)
        game.advance_turn()
        tutorial.update(game)
        self.assertGreaterEqual(tutorial.current_index, 4)

    def test_tutorial_has_ten_steps(self) -> None:
        tutorial = TutorialDirector()
        self.assertEqual(len(tutorial.steps), 10)

    def test_progress_fraction(self) -> None:
        tutorial = TutorialDirector()
        self.assertEqual(tutorial.progress_fraction, 0.0)
        tutorial.current_index = 5
        self.assertAlmostEqual(tutorial.progress_fraction, 0.5, places=2)

    def test_is_complete_when_past_last_step(self) -> None:
        tutorial = TutorialDirector()
        tutorial.current_index = 10
        self.assertTrue(tutorial.is_complete)

    def test_final_step_update_does_not_require_is_over_attribute(self) -> None:
        scenario = load_builtin_scenario("tutorial")
        game = GameState.from_scenario(scenario, rng_seed=1)
        tutorial = TutorialDirector()
        tutorial.current_index = 9

        tutorial.update(game)

        self.assertEqual(tutorial.current_index, 9)

    def test_final_step_advances_when_objective_is_occupied(self) -> None:
        scenario = load_builtin_scenario("tutorial")
        game = GameState.from_scenario(scenario, rng_seed=1)
        tutorial = TutorialDirector()
        tutorial.current_index = 9

        objective = scenario.objectives[0]
        game.units["blue-inf-1"].position = objective.position
        tutorial.update(game)

        self.assertGreaterEqual(tutorial.current_index, 10)


if __name__ == "__main__":
    unittest.main()
