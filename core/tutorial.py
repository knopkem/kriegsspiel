"""Headless tutorial step tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

from .orders import OrderStatus, OrderType


@dataclass(frozen=True, slots=True)
class TutorialStep:
    title: str
    message: str


@dataclass(slots=True)
class TutorialDirector:
    steps: list[TutorialStep] = field(
        default_factory=lambda: [
            TutorialStep("Move", "Select your infantry and right-click a destination to queue a move order."),
            TutorialStep("Attack", "Once the enemy is near, right-click it to queue an attack order."),
            TutorialStep("Rally & Hold", "Try the H and R hotkeys to recover fatigue or rally shaken units."),
        ]
    )
    current_index: int = 0

    @property
    def current_step(self) -> TutorialStep:
        return self.steps[min(self.current_index, len(self.steps) - 1)]

    def update(self, game) -> TutorialStep:
        if self.current_index == 0 and any(
            order.order_type is OrderType.MOVE and order.status is OrderStatus.RESOLVED
            for order in game.order_book.all_orders()
        ):
            self.current_index = 1
        if self.current_index == 1 and any(event.category == "combat" for event in game.event_log):
            self.current_index = 2
        return self.current_step
