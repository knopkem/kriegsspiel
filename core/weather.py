"""Weather and time-of-day mechanics for battlefield effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random


class WeatherCondition(StrEnum):
    CLEAR = "clear"
    OVERCAST = "overcast"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"


class TimeOfDay(StrEnum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


_CONDITION_VISIBILITY: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 1.0,
    WeatherCondition.OVERCAST: 0.9,
    WeatherCondition.LIGHT_RAIN: 0.75,
    WeatherCondition.HEAVY_RAIN: 0.5,
    WeatherCondition.FOG: 0.4,
}

_TOD_VISIBILITY: dict[TimeOfDay, float] = {
    TimeOfDay.DAWN: 0.8,
    TimeOfDay.DAY: 1.0,
    TimeOfDay.DUSK: 0.8,
    TimeOfDay.NIGHT: 0.35,
}

_CONDITION_MOVEMENT: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 0.0,
    WeatherCondition.OVERCAST: 0.0,
    WeatherCondition.LIGHT_RAIN: 0.2,
    WeatherCondition.HEAVY_RAIN: 0.4,
    WeatherCondition.FOG: 0.0,
}

_CONDITION_ARTILLERY: dict[WeatherCondition, float] = {
    WeatherCondition.CLEAR: 1.0,
    WeatherCondition.OVERCAST: 1.0,
    WeatherCondition.LIGHT_RAIN: 0.85,
    WeatherCondition.HEAVY_RAIN: 0.6,
    WeatherCondition.FOG: 0.7,
}

# Cumulative transition probabilities: condition → [(next_condition, cumulative_prob), ...]
_TRANSITIONS: dict[WeatherCondition, list[tuple[WeatherCondition, float]]] = {
    WeatherCondition.CLEAR: [
        (WeatherCondition.CLEAR, 0.70),
        (WeatherCondition.OVERCAST, 0.90),
        (WeatherCondition.FOG, 1.00),
    ],
    WeatherCondition.OVERCAST: [
        (WeatherCondition.OVERCAST, 0.50),
        (WeatherCondition.CLEAR, 0.70),
        (WeatherCondition.LIGHT_RAIN, 0.90),
        (WeatherCondition.FOG, 1.00),
    ],
    WeatherCondition.LIGHT_RAIN: [
        (WeatherCondition.LIGHT_RAIN, 0.40),
        (WeatherCondition.OVERCAST, 0.70),
        (WeatherCondition.HEAVY_RAIN, 1.00),
    ],
    WeatherCondition.HEAVY_RAIN: [
        (WeatherCondition.HEAVY_RAIN, 0.50),
        (WeatherCondition.LIGHT_RAIN, 1.00),
    ],
    WeatherCondition.FOG: [
        (WeatherCondition.FOG, 0.60),
        (WeatherCondition.CLEAR, 1.00),
    ],
}


def _hour_to_time_of_day(hour: float) -> TimeOfDay:
    if 4.0 <= hour < 7.0:
        return TimeOfDay.DAWN
    if 7.0 <= hour < 19.0:
        return TimeOfDay.DAY
    if 19.0 <= hour < 21.0:
        return TimeOfDay.DUSK
    return TimeOfDay.NIGHT


@dataclass(slots=True)
class WeatherState:
    """Combined weather and time-of-day state with derived combat modifiers."""

    condition: WeatherCondition = WeatherCondition.CLEAR
    time_of_day: TimeOfDay = TimeOfDay.DAY
    _current_hour: float = field(default=7.0, init=False, repr=False)

    @property
    def visibility_range_modifier(self) -> float:
        """Multiplier for max visibility range (LOS range)."""
        return _CONDITION_VISIBILITY[self.condition] * _TOD_VISIBILITY[self.time_of_day]

    @property
    def movement_cost_modifier(self) -> float:
        """Additive modifier for all movement costs."""
        night_add = 0.3 if self.time_of_day is TimeOfDay.NIGHT else 0.0
        return _CONDITION_MOVEMENT[self.condition] + night_add

    @property
    def artillery_effectiveness_modifier(self) -> float:
        """Multiplier for artillery ranged damage."""
        night_mult = 0.5 if self.time_of_day is TimeOfDay.NIGHT else 1.0
        return _CONDITION_ARTILLERY[self.condition] * night_mult

    def advance(self, rng: random.Random, turns_per_day: int = 12) -> None:
        """Progress time of day and randomly evolve weather."""
        self._current_hour = (self._current_hour + 24.0 / turns_per_day) % 24.0
        self.time_of_day = _hour_to_time_of_day(self._current_hour)

        roll = rng.random()
        for condition, cumulative in _TRANSITIONS[self.condition]:
            if roll < cumulative:
                self.condition = condition
                break
