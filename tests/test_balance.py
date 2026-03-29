"""Tests for extended BalancePlaytester stats and balance report."""

import unittest

from ai.playtest import BalancePlaytester, PlaytestResult, generate_balance_report


class PlaytestResultStatsTestCase(unittest.TestCase):
    def _make_result(self, blue_wins: int, red_wins: int, draws: int) -> PlaytestResult:
        n = blue_wins + red_wins + draws
        return PlaytestResult(
            scenario_name="test_scenario",
            games_played=n,
            blue_wins=blue_wins,
            red_wins=red_wins,
            draws=draws,
            avg_turns=5.0,
            avg_blue_units_remaining=3.0,
            avg_red_units_remaining=2.0,
        )

    def test_win_rate_blue_equal_split(self) -> None:
        r = self._make_result(blue_wins=5, red_wins=5, draws=0)
        self.assertAlmostEqual(r.win_rate_blue, 0.5)

    def test_win_rate_blue_all_blue(self) -> None:
        r = self._make_result(blue_wins=10, red_wins=0, draws=0)
        self.assertAlmostEqual(r.win_rate_blue, 1.0)

    def test_balance_score_perfectly_balanced(self) -> None:
        r = self._make_result(blue_wins=5, red_wins=5, draws=0)
        self.assertAlmostEqual(r.balance_score, 0.0)

    def test_balance_score_one_sided(self) -> None:
        r = self._make_result(blue_wins=10, red_wins=0, draws=0)
        self.assertAlmostEqual(r.balance_score, 0.5)

    def test_win_rate_blue_zero_games_does_not_crash(self) -> None:
        r = PlaytestResult(
            scenario_name="empty",
            games_played=0,
            blue_wins=0,
            red_wins=0,
            draws=0,
            avg_turns=0.0,
            avg_blue_units_remaining=0.0,
            avg_red_units_remaining=0.0,
        )
        self.assertEqual(r.win_rate_blue, 0.0)


class BalancePlaytesterStatsTestCase(unittest.TestCase):
    def test_aggregate_stats_fields_present(self) -> None:
        playtester = BalancePlaytester(("tutorial",), games_per_scenario=2, turn_limit=3)
        results = playtester.run()
        r = results[0]
        self.assertEqual(r.games_played, 2)
        self.assertEqual(r.blue_wins + r.red_wins + r.draws, 2)
        self.assertGreaterEqual(r.avg_turns, 1.0)

    def test_units_remaining_non_negative(self) -> None:
        playtester = BalancePlaytester(("tutorial",), games_per_scenario=1, turn_limit=3)
        results = playtester.run()
        r = results[0]
        self.assertGreaterEqual(r.avg_blue_units_remaining, 0.0)
        self.assertGreaterEqual(r.avg_red_units_remaining, 0.0)


class GenerateBalanceReportTestCase(unittest.TestCase):
    def _sample_results(self) -> list[PlaytestResult]:
        return [
            PlaytestResult(
                scenario_name="tutorial",
                games_played=10,
                blue_wins=4,
                red_wins=6,
                draws=0,
                avg_turns=8.2,
                avg_blue_units_remaining=2.0,
                avg_red_units_remaining=3.0,
            ),
            PlaytestResult(
                scenario_name="skirmish_small",
                games_played=10,
                blue_wins=5,
                red_wins=4,
                draws=1,
                avg_turns=6.5,
                avg_blue_units_remaining=3.5,
                avg_red_units_remaining=3.2,
            ),
        ]

    def test_report_contains_scenario_names(self) -> None:
        report = generate_balance_report(self._sample_results())
        self.assertIn("tutorial", report)
        self.assertIn("skirmish_small", report)

    def test_report_marks_balanced_scenario(self) -> None:
        """skirmish_small (balance_score=0.05) should get a ★."""
        report = generate_balance_report(self._sample_results())
        lines = report.splitlines()
        skirmish_line = next(l for l in lines if "skirmish_small" in l)
        self.assertIn("★", skirmish_line)

    def test_report_does_not_mark_imbalanced_scenario(self) -> None:
        """tutorial (balance_score=0.10) is <0.15 so it also gets ★; test a truly imbalanced one."""
        results = [
            PlaytestResult(
                scenario_name="lopsided",
                games_played=10,
                blue_wins=9,
                red_wins=1,
                draws=0,
                avg_turns=4.0,
                avg_blue_units_remaining=4.0,
                avg_red_units_remaining=0.5,
            )
        ]
        report = generate_balance_report(results)
        lines = report.splitlines()
        lopsided_line = next(l for l in lines if "lopsided" in l)
        self.assertNotIn("★", lopsided_line)

    def test_report_includes_header(self) -> None:
        report = generate_balance_report(self._sample_results())
        self.assertIn("Scenario", report)
        self.assertIn("Balance", report)
        self.assertIn("AvgTurns", report)


if __name__ == "__main__":
    unittest.main()
