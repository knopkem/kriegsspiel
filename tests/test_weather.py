"""Tests for weather and time-of-day mechanics."""

import unittest
import random

from core.weather import (
    WeatherCondition,
    WeatherState,
    TimeOfDay,
    _hour_to_time_of_day,
)


class TestHourToTimeOfDay(unittest.TestCase):
    def test_dawn_range(self) -> None:
        self.assertEqual(_hour_to_time_of_day(4.0), TimeOfDay.DAWN)
        self.assertEqual(_hour_to_time_of_day(6.9), TimeOfDay.DAWN)

    def test_day_range(self) -> None:
        self.assertEqual(_hour_to_time_of_day(7.0), TimeOfDay.DAY)
        self.assertEqual(_hour_to_time_of_day(18.9), TimeOfDay.DAY)

    def test_dusk_range(self) -> None:
        self.assertEqual(_hour_to_time_of_day(19.0), TimeOfDay.DUSK)
        self.assertEqual(_hour_to_time_of_day(20.9), TimeOfDay.DUSK)

    def test_night_range(self) -> None:
        self.assertEqual(_hour_to_time_of_day(21.0), TimeOfDay.NIGHT)
        self.assertEqual(_hour_to_time_of_day(23.9), TimeOfDay.NIGHT)
        self.assertEqual(_hour_to_time_of_day(0.0), TimeOfDay.NIGHT)
        self.assertEqual(_hour_to_time_of_day(3.9), TimeOfDay.NIGHT)


class TestVisibilityRangeModifier(unittest.TestCase):
    def test_clear_day_is_full(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.DAY)
        self.assertAlmostEqual(w.visibility_range_modifier, 1.0)

    def test_heavy_rain_halves_visibility(self) -> None:
        w = WeatherState(WeatherCondition.HEAVY_RAIN, TimeOfDay.DAY)
        self.assertAlmostEqual(w.visibility_range_modifier, 0.5)

    def test_fog_low_visibility(self) -> None:
        w = WeatherState(WeatherCondition.FOG, TimeOfDay.DAY)
        self.assertAlmostEqual(w.visibility_range_modifier, 0.4)

    def test_night_drastically_reduces_visibility(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.visibility_range_modifier, 0.35)

    def test_fog_at_night_multiplicative(self) -> None:
        w = WeatherState(WeatherCondition.FOG, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.visibility_range_modifier, 0.4 * 0.35)

    def test_overcast_dawn(self) -> None:
        w = WeatherState(WeatherCondition.OVERCAST, TimeOfDay.DAWN)
        self.assertAlmostEqual(w.visibility_range_modifier, 0.9 * 0.8)


class TestMovementCostModifier(unittest.TestCase):
    def test_clear_no_penalty(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.DAY)
        self.assertAlmostEqual(w.movement_cost_modifier, 0.0)

    def test_light_rain_penalty(self) -> None:
        w = WeatherState(WeatherCondition.LIGHT_RAIN, TimeOfDay.DAY)
        self.assertAlmostEqual(w.movement_cost_modifier, 0.2)

    def test_heavy_rain_penalty(self) -> None:
        w = WeatherState(WeatherCondition.HEAVY_RAIN, TimeOfDay.DAY)
        self.assertAlmostEqual(w.movement_cost_modifier, 0.4)

    def test_night_adds_penalty(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.movement_cost_modifier, 0.3)

    def test_rain_plus_night(self) -> None:
        w = WeatherState(WeatherCondition.LIGHT_RAIN, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.movement_cost_modifier, 0.5)


class TestArtilleryEffectivenessModifier(unittest.TestCase):
    def test_clear_day_full(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.DAY)
        self.assertAlmostEqual(w.artillery_effectiveness_modifier, 1.0)

    def test_heavy_rain_reduces(self) -> None:
        w = WeatherState(WeatherCondition.HEAVY_RAIN, TimeOfDay.DAY)
        self.assertAlmostEqual(w.artillery_effectiveness_modifier, 0.6)

    def test_night_halves(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.artillery_effectiveness_modifier, 0.5)

    def test_fog_at_night_multiplicative(self) -> None:
        w = WeatherState(WeatherCondition.FOG, TimeOfDay.NIGHT)
        self.assertAlmostEqual(w.artillery_effectiveness_modifier, 0.7 * 0.5)

    def test_overcast_unchanged(self) -> None:
        w = WeatherState(WeatherCondition.OVERCAST, TimeOfDay.DAY)
        self.assertAlmostEqual(w.artillery_effectiveness_modifier, 1.0)


class TestWeatherAdvance(unittest.TestCase):
    def test_time_advances_each_call(self) -> None:
        w = WeatherState()
        rng = random.Random(42)
        # Default starts at hour 7 (DAY); 12 turns per day = 2h per turn
        w.advance(rng, turns_per_day=12)
        # After one advance: hour 9, still DAY
        self.assertEqual(w.time_of_day, TimeOfDay.DAY)

    def test_wraps_around_midnight(self) -> None:
        # Advance enough to get through a full day
        w = WeatherState()
        rng = random.Random(0)
        for _ in range(12):
            w.advance(rng, turns_per_day=12)
        # After 12 * 2h = 24h, should wrap back
        self.assertIn(w.time_of_day, list(TimeOfDay))

    def test_transitions_stay_valid(self) -> None:
        w = WeatherState(WeatherCondition.CLEAR, TimeOfDay.DAY)
        rng = random.Random(999)
        for _ in range(50):
            w.advance(rng)
            self.assertIn(w.condition, list(WeatherCondition))
            self.assertIn(w.time_of_day, list(TimeOfDay))

    def test_fog_transitions_to_clear_or_stays(self) -> None:
        outcomes: set[WeatherCondition] = set()
        for seed in range(200):
            w = WeatherState(WeatherCondition.FOG, TimeOfDay.DAY)
            w.advance(random.Random(seed))
            outcomes.add(w.condition)
        # FOG can only stay FOG or transition to CLEAR
        self.assertTrue(outcomes.issubset({WeatherCondition.FOG, WeatherCondition.CLEAR}))

    def test_heavy_rain_transitions_to_light_rain_or_stays(self) -> None:
        outcomes: set[WeatherCondition] = set()
        for seed in range(200):
            w = WeatherState(WeatherCondition.HEAVY_RAIN, TimeOfDay.DAY)
            w.advance(random.Random(seed))
            outcomes.add(w.condition)
        self.assertTrue(outcomes.issubset({WeatherCondition.HEAVY_RAIN, WeatherCondition.LIGHT_RAIN}))

    def test_night_reached_after_dusk(self) -> None:
        # Start at hour 19 (dusk boundary), advance 2h → 21 → NIGHT
        w = WeatherState()
        rng = random.Random(1)
        # Advance to just before dusk: hour 7 + N*2 steps
        # We want to reach hour 19 first, then 21
        # Start at 7, advance 6 steps → hour 19 (dusk)
        for _ in range(6):
            w.advance(rng, turns_per_day=12)
        self.assertEqual(w.time_of_day, TimeOfDay.DUSK)
        w.advance(rng, turns_per_day=12)
        self.assertEqual(w.time_of_day, TimeOfDay.NIGHT)


if __name__ == "__main__":
    unittest.main()
