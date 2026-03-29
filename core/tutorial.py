"""Headless tutorial step tracking.

:class:`TutorialDirector` drives a 10-step guided walkthrough.  Each step
exposes a ``title`` and ``message`` for the UI to render, and a
``hint_highlights`` list of (q, r) hex coordinates that the renderer can
optionally highlight to focus the player's attention.

The director inspects :class:`~core.game.GameState` after each turn-end to
detect whether the current step's completion condition has been met, then
advances ``current_index`` accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .orders import OrderStatus, OrderType
from .units import MoraleState, UnitType


@dataclass(frozen=True)
class TutorialStep:
    title: str
    message: str
    #: Optional hex coords (q, r) to highlight in the UI for this step.
    hint_highlights: tuple[tuple[int, int], ...] = ()


def _default_steps() -> list[TutorialStep]:
    return [
        # Step 0 — selection & movement
        TutorialStep(
            "1 / 10 — Select & Move",
            "Click one of your units (blue), then RIGHT-CLICK a nearby hex to queue a Move order. Press ENTER to end the turn.",
        ),
        # Step 1 — terrain awareness
        TutorialStep(
            "2 / 10 — Terrain Matters",
            "Move costs more through forests and marshes. Roads are fast. Watch the move-range overlay (green hexes) for clues.",
        ),
        # Step 2 — formation change
        TutorialStep(
            "3 / 10 — Change Formation",
            "Press F to cycle formations (Line → Column → Square → Skirmish). Column is fastest on roads; Line maximises firepower.",
        ),
        # Step 3 — attack (ranged fire)
        TutorialStep(
            "4 / 10 — Open Fire",
            "Right-click an enemy unit within range to queue an Attack order. Attack-range hexes glow red. Submit the turn with ENTER.",
        ),
        # Step 4 — fog of war
        TutorialStep(
            "5 / 10 — Fog of War",
            "You only see enemy units your troops can observe. Dark hexes are hidden. Advance scouts (cavalry) to gain visibility.",
        ),
        # Step 5 — morale
        TutorialStep(
            "6 / 10 — Morale",
            "A unit under fire may become SHAKEN (orange bar) or start ROUTING (red). Routing units flee — keep them near a commander to rally.",
        ),
        # Step 6 — rally
        TutorialStep(
            "7 / 10 — Rally Shaken Units",
            "Select a shaken or routing unit and press R to queue a Rally order. Units near friendly commanders rally more reliably.",
        ),
        # Step 7 — hold / defend
        TutorialStep(
            "8 / 10 — Hold Position",
            "Press H to order a unit to Hold. Holding units gain a +1 defense bonus and entrench if they hold for two consecutive turns.",
        ),
        # Step 8 — orders queue
        TutorialStep(
            "9 / 10 — Orders Queue",
            "All orders appear in the right panel before you end the turn. Click ✕ next to any order to cancel it. End turn with ENTER.",
        ),
        # Step 9 — victory conditions
        TutorialStep(
            "10 / 10 — Victory",
            "Capture and hold objective hexes (flags) to earn victory points. Reach the target score before the turn limit to win!",
        ),
    ]


@dataclass
class TutorialDirector:
    steps: list[TutorialStep] = field(default_factory=_default_steps)
    current_index: int = 0
    _completed_steps: set[int] = field(default_factory=set)

    @property
    def current_step(self) -> TutorialStep:
        idx = min(self.current_index, len(self.steps) - 1)
        return self.steps[idx]

    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.steps)

    @property
    def progress_fraction(self) -> float:
        return min(1.0, self.current_index / len(self.steps))

    def _advance(self) -> None:
        self.current_index += 1

    def update(self, game) -> TutorialStep:
        """Check game state and advance the tutorial step when conditions are met."""
        idx = self.current_index
        if idx in self._completed_steps or idx >= len(self.steps):
            return self.current_step

        orders = list(game.order_book.all_orders())
        events = game.event_log

        resolved_moves = [
            o for o in orders
            if o.order_type is OrderType.MOVE and o.status is OrderStatus.RESOLVED
        ]
        combat_events = [e for e in events if e.category == "combat"]
        morale_events = [e for e in events if e.category == "morale"]
        all_units = list(game.units.values())

        if idx == 0 and resolved_moves:
            self._mark_done(0)

        elif idx == 1 and game.current_turn >= 2:
            # Once they've taken a second turn they've experienced terrain
            self._mark_done(1)

        elif idx == 2:
            # Any FORMATION_CHANGE or HOLD order was queued (includes square/column)
            if any(o.order_type in (OrderType.CHANGE_FORMATION,) for o in orders):
                self._mark_done(2)

        elif idx == 3 and combat_events:
            self._mark_done(3)

        elif idx == 4 and game.current_turn >= 3:
            # Give them a couple turns to notice fog of war
            self._mark_done(4)

        elif idx == 5 and morale_events:
            # Any morale change event
            self._mark_done(5)

        elif idx == 6:
            if any(o.order_type is OrderType.RALLY for o in orders):
                self._mark_done(6)

        elif idx == 7:
            if any(o.order_type is OrderType.HOLD for o in orders):
                self._mark_done(7)

        elif idx == 8 and game.current_turn >= 4:
            # By turn 4 they've seen the queue
            self._mark_done(8)

        elif idx == 9:
            # Advance once they've captured an objective or the game is over
            objective_occupied = any(
                any(not unit.is_removed for unit in game.units_at(obj.position))
                for obj in game.objectives
            )
            report = game.victory_report()
            decisive_outcome = report.level.value != "draw"
            if decisive_outcome or objective_occupied:
                self._mark_done(9)

        return self.current_step

    def _mark_done(self, step_idx: int) -> None:
        self._completed_steps.add(step_idx)
        self.current_index = step_idx + 1
