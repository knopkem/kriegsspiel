"""Tests for AdaptiveController difficulty adjustment."""
import os
import unittest

from ai.difficulty import AdaptiveController, AIDifficulty


class AdaptiveControllerTestCase(unittest.TestCase):
    def test_stays_at_base_with_mixed_results(self) -> None:
        """Mixed win/loss history leaves difficulty at base level."""
        ctrl = AdaptiveController(base_difficulty=AIDifficulty.MEDIUM)
        ctrl.record_result(True)
        ctrl.record_result(False)
        ctrl.record_result(True)
        self.assertEqual(ctrl.current_difficulty(), AIDifficulty.MEDIUM)

    def test_bumps_up_after_three_consecutive_wins(self) -> None:
        """Three consecutive player wins bump difficulty one level higher."""
        ctrl = AdaptiveController(base_difficulty=AIDifficulty.MEDIUM)
        ctrl.record_result(True)
        ctrl.record_result(True)
        ctrl.record_result(True)
        self.assertEqual(ctrl.current_difficulty(), AIDifficulty.HARD)

    def test_drops_down_after_three_consecutive_losses(self) -> None:
        """Three consecutive player losses drop difficulty one level lower."""
        ctrl = AdaptiveController(base_difficulty=AIDifficulty.MEDIUM)
        ctrl.record_result(False)
        ctrl.record_result(False)
        ctrl.record_result(False)
        self.assertEqual(ctrl.current_difficulty(), AIDifficulty.EASY)

    def test_clamps_at_highest_level(self) -> None:
        """Bumping from the highest difficulty stays at the top level."""
        ctrl = AdaptiveController(base_difficulty=AIDifficulty.HISTORICAL)
        for _ in range(3):
            ctrl.record_result(True)
        self.assertEqual(ctrl.current_difficulty(), AIDifficulty.HISTORICAL)

    def test_save_and_load_roundtrip(self) -> None:
        """Saving and loading preserves win_history and base_difficulty."""
        ctrl = AdaptiveController(base_difficulty=AIDifficulty.HARD)
        ctrl.record_result(True)
        ctrl.record_result(False)
        path = "adaptive_test_roundtrip.json"
        try:
            ctrl.save(path)
            loaded = AdaptiveController.load(path)
            self.assertEqual(loaded.win_history, ctrl.win_history)
            self.assertEqual(loaded.base_difficulty, ctrl.base_difficulty)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
