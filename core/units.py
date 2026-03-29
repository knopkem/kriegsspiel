"""Unit definitions and movement profiles for the core battlefield model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Mapping

from .map import TerrainType, DEFAULT_TERRAIN_COSTS, HexCoord


class Side(StrEnum):
    BLUE = "blue"
    RED = "red"
    NEUTRAL = "neutral"


class UnitType(StrEnum):
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARTILLERY = "artillery"
    SKIRMISHER = "skirmisher"
    COMMANDER = "commander"


class Formation(StrEnum):
    LINE = "line"
    COLUMN = "column"
    SQUARE = "square"
    SKIRMISH = "skirmish"
    LIMBERED = "limbered"
    UNLIMBERED = "unlimbered"
    STAFF = "staff"


class MoraleState(StrEnum):
    STEADY = "steady"
    SHAKEN = "shaken"
    ROUTING = "routing"
    BROKEN = "broken"


class FatigueLevel(StrEnum):
    FRESH = "fresh"
    TIRED = "tired"
    WEARY = "weary"
    EXHAUSTED = "exhausted"


class InfantryExchangeState(StrEnum):
    FULL = "full"
    FIVE_SIXTHS = "five_sixths"
    FOUR_SIXTHS = "four_sixths"
    BROKEN = "broken"


@dataclass(frozen=True, slots=True)
class MovementProfile:
    """Movement allowance by formation and terrain in paces per turn."""

    allowances: Mapping[Formation, Mapping[TerrainType, int]]
    default_formation: Formation

    def allowance(self, formation: Formation, terrain: TerrainType) -> int:
        formation_allowances = self.allowances.get(formation)
        if formation_allowances is None:
            raise ValueError(f"Formation {formation} is not supported by this unit profile.")
        return formation_allowances.get(terrain, 0)

    def supports(self, formation: Formation) -> bool:
        return formation in self.allowances

    def best_allowance(self, formation: Formation | None = None) -> int:
        selected = formation or self.default_formation
        formation_allowances = self.allowances[selected]
        return max(formation_allowances.values(), default=0)


@dataclass(slots=True)
class Unit:
    """Battlefield unit with historical movement and attrition rules."""

    id: str
    name: str
    side: Side
    unit_type: UnitType
    max_strength: int
    max_hit_points: int
    movement_profile: MovementProfile
    position: HexCoord | None = None
    formation: Formation | None = None
    morale_state: MoraleState = MoraleState.STEADY
    fatigue: int = 0
    commander_radius: int = 0
    hit_points: int | None = None
    tags: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.max_strength <= 0:
            raise ValueError("max_strength must be positive")
        if self.max_hit_points <= 0:
            raise ValueError("max_hit_points must be positive")

        if self.formation is None:
            self.formation = self.movement_profile.default_formation
        if not self.movement_profile.supports(self.formation):
            raise ValueError(f"Formation {self.formation} is not valid for {self.unit_type}.")

        if self.hit_points is None:
            self.hit_points = self.max_hit_points

        self.hit_points = max(0, min(self.hit_points, self.max_hit_points))
        self.fatigue = max(0, min(self.fatigue, 100))

    @property
    def strength_ratio(self) -> float:
        return self.hit_points / self.max_hit_points

    @property
    def current_strength(self) -> int:
        return max(0, round(self.max_strength * self.strength_ratio))

    @property
    def casualty_ratio(self) -> float:
        return 1.0 - self.strength_ratio

    @property
    def damage_taken(self) -> int:
        return self.max_hit_points - self.hit_points

    @property
    def fatigue_level(self) -> FatigueLevel:
        if self.fatigue < 25:
            return FatigueLevel.FRESH
        if self.fatigue < 50:
            return FatigueLevel.TIRED
        if self.fatigue < 75:
            return FatigueLevel.WEARY
        return FatigueLevel.EXHAUSTED

    @property
    def fatigue_multiplier(self) -> float:
        if self.fatigue < 25:
            return 1.0
        if self.fatigue < 50:
            return 0.9
        if self.fatigue < 75:
            return 0.75
        return 0.6

    @property
    def morale_multiplier(self) -> float:
        if self.morale_state is MoraleState.STEADY:
            return 1.0
        if self.morale_state is MoraleState.SHAKEN:
            return 0.85
        if self.morale_state is MoraleState.ROUTING:
            return 0.55
        return 0.0

    @property
    def combat_effectiveness(self) -> float:
        return self.strength_ratio * self.fatigue_multiplier * self.morale_multiplier

    @property
    def infantry_exchange_state(self) -> InfantryExchangeState | None:
        if self.unit_type is not UnitType.INFANTRY:
            return None

        one_sixth = math.ceil(self.max_hit_points / 6)
        two_sixths = math.ceil((2 * self.max_hit_points) / 6)
        half_strength = math.ceil(self.max_hit_points / 2)

        if self.damage_taken >= half_strength:
            return InfantryExchangeState.BROKEN
        if self.damage_taken >= two_sixths:
            return InfantryExchangeState.FOUR_SIXTHS
        if self.damage_taken >= one_sixth:
            return InfantryExchangeState.FIVE_SIXTHS
        return InfantryExchangeState.FULL

    @property
    def frontage_ratio(self) -> float:
        exchange_state = self.infantry_exchange_state
        if exchange_state is None:
            return 1.0
        if exchange_state is InfantryExchangeState.FULL:
            return 1.0
        if exchange_state is InfantryExchangeState.FIVE_SIXTHS:
            return 5 / 6
        if exchange_state is InfantryExchangeState.FOUR_SIXTHS:
            return 4 / 6
        return 0.0

    @property
    def is_removed(self) -> bool:
        if self.unit_type is UnitType.INFANTRY:
            return self.infantry_exchange_state is InfantryExchangeState.BROKEN
        return self.hit_points <= 0

    def apply_damage(self, damage: int) -> int:
        if damage < 0:
            raise ValueError("damage must not be negative")
        applied = min(damage, self.hit_points)
        self.hit_points -= applied
        return applied

    def recover_hit_points(self, amount: int) -> int:
        if amount < 0:
            raise ValueError("recovery amount must not be negative")
        recovered = min(amount, self.max_hit_points - self.hit_points)
        self.hit_points += recovered
        return recovered

    def add_fatigue(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("fatigue increase must not be negative")
        self.fatigue = min(100, self.fatigue + amount)

    def recover_fatigue(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("fatigue recovery must not be negative")
        self.fatigue = max(0, self.fatigue - amount)

    def change_formation(self, formation: Formation) -> None:
        if not self.movement_profile.supports(formation):
            raise ValueError(f"{self.unit_type} cannot adopt formation {formation}.")
        self.formation = formation

    def movement_allowance(self, terrain: TerrainType) -> int:
        base_allowance = self.movement_profile.allowance(self.formation, terrain)
        return math.floor(base_allowance * self.fatigue_multiplier)

    def can_enter(self, terrain: TerrainType) -> bool:
        return self.movement_allowance(terrain) > 0

    def turn_movement_budget(self) -> int:
        return math.floor(self.movement_profile.best_allowance(self.formation) * self.fatigue_multiplier)

    def movement_costs(self) -> dict[TerrainType, float]:
        best = max(self.movement_profile.best_allowance(self.formation), 1)
        costs: dict[TerrainType, float] = {}
        for terrain in TerrainType:
            allowance = self.movement_allowance(terrain)
            if allowance <= 0:
                costs[terrain] = math.inf
                continue
            costs[terrain] = max(DEFAULT_TERRAIN_COSTS.get(terrain, 1.0), best / allowance)
        return costs

    def degrade_morale(self, steps: int = 1) -> MoraleState:
        if steps < 0:
            raise ValueError("steps must not be negative")
        order = [
            MoraleState.STEADY,
            MoraleState.SHAKEN,
            MoraleState.ROUTING,
            MoraleState.BROKEN,
        ]
        index = order.index(self.morale_state)
        self.morale_state = order[min(len(order) - 1, index + steps)]
        return self.morale_state

    def improve_morale(self, steps: int = 1) -> MoraleState:
        if steps < 0:
            raise ValueError("steps must not be negative")
        order = [
            MoraleState.STEADY,
            MoraleState.SHAKEN,
            MoraleState.ROUTING,
            MoraleState.BROKEN,
        ]
        index = order.index(self.morale_state)
        self.morale_state = order[max(0, index - steps)]
        return self.morale_state


INFANTRY_MOVEMENT = MovementProfile(
    allowances={
        Formation.LINE: {
            TerrainType.OPEN: 150,
            TerrainType.ROAD: 150,
            TerrainType.FOREST: 75,
            TerrainType.HILL: 100,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 100,
            TerrainType.MARSH: 75,
            TerrainType.FORTIFICATION: 100,
        },
        Formation.COLUMN: {
            TerrainType.OPEN: 150,
            TerrainType.ROAD: 200,
            TerrainType.FOREST: 100,
            TerrainType.HILL: 100,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 100,
            TerrainType.MARSH: 75,
            TerrainType.FORTIFICATION: 100,
        },
        Formation.SQUARE: {
            TerrainType.OPEN: 75,
            TerrainType.ROAD: 75,
            TerrainType.FOREST: 0,
            TerrainType.HILL: 50,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 50,
            TerrainType.MARSH: 0,
            TerrainType.FORTIFICATION: 50,
        },
        Formation.SKIRMISH: {
            TerrainType.OPEN: 150,
            TerrainType.ROAD: 175,
            TerrainType.FOREST: 125,
            TerrainType.HILL: 125,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 125,
            TerrainType.MARSH: 75,
            TerrainType.FORTIFICATION: 100,
        },
    },
    default_formation=Formation.COLUMN,
)

CAVALRY_MOVEMENT = MovementProfile(
    allowances={
        Formation.LINE: {
            TerrainType.OPEN: 225,
            TerrainType.ROAD: 225,
            TerrainType.FOREST: 110,
            TerrainType.HILL: 150,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 100,
            TerrainType.MARSH: 0,
            TerrainType.FORTIFICATION: 75,
        },
        Formation.COLUMN: {
            TerrainType.OPEN: 225,
            TerrainType.ROAD: 300,
            TerrainType.FOREST: 150,
            TerrainType.HILL: 150,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 100,
            TerrainType.MARSH: 0,
            TerrainType.FORTIFICATION: 75,
        },
    },
    default_formation=Formation.COLUMN,
)

ARTILLERY_MOVEMENT = MovementProfile(
    allowances={
        Formation.LIMBERED: {
            TerrainType.OPEN: 150,
            TerrainType.ROAD: 200,
            TerrainType.FOREST: 75,
            TerrainType.HILL: 100,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 75,
            TerrainType.MARSH: 50,
            TerrainType.FORTIFICATION: 75,
        },
        Formation.UNLIMBERED: {
            TerrainType.OPEN: 25,
            TerrainType.ROAD: 25,
            TerrainType.FOREST: 0,
            TerrainType.HILL: 10,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 10,
            TerrainType.MARSH: 0,
            TerrainType.FORTIFICATION: 10,
        },
    },
    default_formation=Formation.LIMBERED,
)

SKIRMISHER_MOVEMENT = MovementProfile(
    allowances={
        Formation.SKIRMISH: {
            TerrainType.OPEN: 175,
            TerrainType.ROAD: 200,
            TerrainType.FOREST: 150,
            TerrainType.HILL: 125,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 150,
            TerrainType.MARSH: 100,
            TerrainType.FORTIFICATION: 125,
        }
    },
    default_formation=Formation.SKIRMISH,
)

COMMANDER_MOVEMENT = MovementProfile(
    allowances={
        Formation.STAFF: {
            TerrainType.OPEN: 225,
            TerrainType.ROAD: 300,
            TerrainType.FOREST: 125,
            TerrainType.HILL: 175,
            TerrainType.RIVER: 0,
            TerrainType.VILLAGE: 150,
            TerrainType.MARSH: 100,
            TerrainType.FORTIFICATION: 125,
        }
    },
    default_formation=Formation.STAFF,
)


def make_infantry_half_battalion(
    unit_id: str,
    name: str,
    side: Side,
    *,
    position: HexCoord | None = None,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        side=side,
        unit_type=UnitType.INFANTRY,
        max_strength=450,
        max_hit_points=90,
        movement_profile=INFANTRY_MOVEMENT,
        position=position,
        formation=Formation.COLUMN,
    )


def make_cavalry_squadron(
    unit_id: str,
    name: str,
    side: Side,
    *,
    position: HexCoord | None = None,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        side=side,
        unit_type=UnitType.CAVALRY,
        max_strength=90,
        max_hit_points=60,
        movement_profile=CAVALRY_MOVEMENT,
        position=position,
        formation=Formation.COLUMN,
    )


def make_artillery_battery(
    unit_id: str,
    name: str,
    side: Side,
    *,
    position: HexCoord | None = None,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        side=side,
        unit_type=UnitType.ARTILLERY,
        max_strength=8,
        max_hit_points=48,
        movement_profile=ARTILLERY_MOVEMENT,
        position=position,
        formation=Formation.LIMBERED,
    )


def make_skirmisher_detachment(
    unit_id: str,
    name: str,
    side: Side,
    *,
    position: HexCoord | None = None,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        side=side,
        unit_type=UnitType.SKIRMISHER,
        max_strength=120,
        max_hit_points=24,
        movement_profile=SKIRMISHER_MOVEMENT,
        position=position,
        formation=Formation.SKIRMISH,
    )


def make_commander(
    unit_id: str,
    name: str,
    side: Side,
    *,
    position: HexCoord | None = None,
    command_radius: int = 6,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        side=side,
        unit_type=UnitType.COMMANDER,
        max_strength=1,
        max_hit_points=10,
        movement_profile=COMMANDER_MOVEMENT,
        position=position,
        formation=Formation.STAFF,
        commander_radius=command_radius,
    )
