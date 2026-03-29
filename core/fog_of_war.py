"""Fog-of-war state tracking built on unit vision ranges and map LOS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Mapping

from .map import HexCoord, HexGridMap
from .units import Side, Unit, UnitType


class VisibilityState(StrEnum):
    VISIBLE = "visible"
    EXPLORED = "explored"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class LastKnownEnemy:
    unit_id: str
    position: HexCoord
    seen_on_turn: int


@dataclass(frozen=True, slots=True)
class VisibilitySnapshot:
    side: Side
    visible_hexes: frozenset[HexCoord]
    explored_hexes: frozenset[HexCoord]
    visible_enemy_units: frozenset[str]
    last_known_enemies: Mapping[str, LastKnownEnemy]

    def visibility_state(self, coord: HexCoord) -> VisibilityState:
        if coord in self.visible_hexes:
            return VisibilityState.VISIBLE
        if coord in self.explored_hexes:
            return VisibilityState.EXPLORED
        return VisibilityState.HIDDEN

    def can_see(self, coord: HexCoord) -> bool:
        return coord in self.visible_hexes


DEFAULT_VISION_RANGES: dict[UnitType, int] = {
    UnitType.INFANTRY: 4,
    UnitType.CAVALRY: 6,
    UnitType.ARTILLERY: 5,
    UnitType.SKIRMISHER: 5,
    UnitType.COMMANDER: 5,
}


@dataclass(slots=True)
class FogOfWarEngine:
    """Computes visible hexes and remembered enemy sightings by side."""

    battle_map: HexGridMap
    vision_ranges: Mapping[UnitType, int] = field(default_factory=lambda: DEFAULT_VISION_RANGES.copy())
    _explored: dict[Side, set[HexCoord]] = field(default_factory=dict)
    _last_known: dict[Side, dict[str, LastKnownEnemy]] = field(default_factory=dict)

    def update(
        self,
        units: Iterable[Unit],
        *,
        current_turn: int,
    ) -> dict[Side, VisibilitySnapshot]:
        all_units = list(units)
        units_by_side = self._group_active_units(all_units)
        known_sides = {unit.side for unit in all_units} | set(self._explored) | set(self._last_known)
        snapshots: dict[Side, VisibilitySnapshot] = {}

        for side in known_sides:
            friendly_units = units_by_side.get(side, [])
            visible_hexes: set[HexCoord] = set()
            for unit in friendly_units:
                visible_hexes.update(self.visible_hexes_for_unit(unit))

            explored = self._explored.setdefault(side, set())
            explored.update(visible_hexes)

            last_known = self._last_known.setdefault(side, {})
            visible_enemy_units: set[str] = set()

            for enemy in all_units:
                if enemy.side == side:
                    continue
                if enemy.is_removed:
                    last_known.pop(enemy.id, None)
                    continue
                if enemy.position is not None and enemy.position in visible_hexes:
                    visible_enemy_units.add(enemy.id)
                    last_known[enemy.id] = LastKnownEnemy(
                        unit_id=enemy.id,
                        position=enemy.position,
                        seen_on_turn=current_turn,
                    )

            snapshots[side] = VisibilitySnapshot(
                side=side,
                visible_hexes=frozenset(visible_hexes),
                explored_hexes=frozenset(explored),
                visible_enemy_units=frozenset(visible_enemy_units),
                last_known_enemies=dict(last_known),
            )

        return snapshots

    def visible_hexes_for_unit(self, unit: Unit) -> set[HexCoord]:
        if unit.position is None or unit.is_removed:
            return set()

        max_range = self.vision_range(unit)
        visible: set[HexCoord] = {unit.position}
        for coord in self.battle_map.coords():
            if coord == unit.position:
                continue
            if unit.position.distance_to(coord) > max_range:
                continue
            if self.battle_map.has_line_of_sight(unit.position, coord):
                visible.add(coord)
        return visible

    def vision_range(self, unit: Unit) -> int:
        return self.vision_ranges.get(unit.unit_type, 4)

    @staticmethod
    def _group_active_units(units: Iterable[Unit]) -> dict[Side, list[Unit]]:
        grouped: dict[Side, list[Unit]] = {}
        for unit in units:
            if unit.position is None or unit.is_removed:
                continue
            grouped.setdefault(unit.side, []).append(unit)
        return grouped
