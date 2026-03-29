"""Tactical decision helpers for the simple AI commander."""

from __future__ import annotations

from dataclasses import dataclass
import random

from core.game import GameState
from core.map import HexCoord
from core.units import Unit


@dataclass(slots=True)
class TacticalPlanner:
    rng: random.Random

    def choose_retreat_destination(self, game: GameState, unit: Unit) -> HexCoord:
        width = game.battle_map.width - 1
        if unit.side.value == "blue":
            return HexCoord(0, unit.position.r)
        return HexCoord(width, unit.position.r)

    def choose_approach_destination(self, game: GameState, unit: Unit, target: HexCoord) -> HexCoord:
        path = game.battle_map.find_path(unit.position, target, terrain_costs=unit.movement_costs())
        if len(path) >= 2:
            return path[min(2, len(path) - 1)]
        return target

