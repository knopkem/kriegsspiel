import unittest

from ai.playtest import BalancePlaytester


class BalancePlaytesterTestCase(unittest.TestCase):
    def test_playtester_returns_results_for_requested_scenarios(self) -> None:
        playtester = BalancePlaytester(("tutorial", "skirmish_small"), games_per_scenario=1, turn_limit=3)

        results = playtester.run()

        self.assertEqual(len(results), 2)
        self.assertEqual({result.scenario_name for result in results}, {"tutorial", "skirmish_small"})


if __name__ == "__main__":
    unittest.main()
