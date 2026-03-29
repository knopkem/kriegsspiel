"""Heuristic battlefield evaluation for AI order selection."""

from __future__ import annotations

from dataclasses import dataclass

from core.game import GameState
from core.units import Side, Unit, UnitType


UNIT_WEIGHTS: dict[UnitType, float] = {
    UnitType.INFANTRY: 1.0,
    UnitType.CAVALRY: 1.15,
    UnitType.ARTILLERY: 1.3,
    UnitType.SKIRMISHER: 0.7,
    UnitType.COMMANDER: 1.5,
}


@dataclass(slots=True)
class BattlefieldEvaluator:
    """Scores unit and side states from a given side's perspective."""

    def unit_value(self, unit: Unit) -> float:
        base = unit.max_hit_points * UNIT_WEIGHTS[unit.unit_type]
        return base * unit.combat_effectiveness

    def side_score(self, game: GameState, side: Side) -> float:
        friendly = sum(self.unit_value(unit) for unit in game.units.values() if unit.side is side and not unit.is_removed)
        enemy = sum(self.unit_value(unit) for unit in game.units.values() if unit.side is not side and not unit.is_removed)
        objective = game.score_for_side(side) * 8
        return friendly - enemy + objective

    def best_target(self, game: GameState, attacker: Unit, enemy_units: list[Unit]) -> Unit | None:
        if not enemy_units:
            return None
        return min(
            enemy_units,
            key=lambda unit: (
                attacker.position.distance_to(unit.position),
                self.unit_value(unit),
            ),
        )

