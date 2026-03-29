import unittest

from core.scenario import load_builtin_scenario
from core.units import UnitType


class ScenarioLoaderTestCase(unittest.TestCase):
    def test_builtin_scenarios_load_map_units_and_objectives(self) -> None:
        expectations = {
            "tutorial": (6, 5),
            "skirmish_small": (9, 6),
            "assault_on_hill": (10, 7),
            "full_battle": (12, 10),
        }

        for scenario_name, (width, height) in expectations.items():
            with self.subTest(scenario=scenario_name):
                scenario = load_builtin_scenario(scenario_name)
                battle_map = scenario.build_map()
                units = scenario.build_units()

                self.assertEqual(battle_map.width, width)
                self.assertEqual(battle_map.height, height)
                self.assertTrue(units)
                self.assertTrue(scenario.objectives)
                self.assertTrue(any(unit.unit_type is UnitType.ARTILLERY for unit in units.values()) or scenario_name == "tutorial")


if __name__ == "__main__":
    unittest.main()
