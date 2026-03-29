"""High-level objective selection for the AI."""

from __future__ import annotations

from dataclasses import dataclass

from core.game import GameState
from core.units import Side, Unit


@dataclass(slots=True)
class ObjectiveSelector:
    def choose_focus_objective(self, game: GameState, side: Side, unit: Unit):
        if not game.objectives:
            return None
        return max(
            game.objectives,
            key=lambda objective: (
                objective.points * 10 - unit.position.distance_to(objective.position)
            ),
        )

