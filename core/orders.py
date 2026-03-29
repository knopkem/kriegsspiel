"""Order models and delayed command queue for simultaneous turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

from .map import HexCoord
from .units import Formation


class OrderType(StrEnum):
    MOVE = "move"
    ATTACK = "attack"
    CHANGE_FORMATION = "change_formation"
    RALLY = "rally"
    HOLD = "hold"
    RETREAT = "retreat"
    COMMANDER_ABILITY = "commander_ability"


class OrderStatus(StrEnum):
    QUEUED = "queued"
    READY = "ready"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Order:
    """A single command issued to a unit."""

    order_id: str
    order_type: OrderType
    unit_id: str
    issued_turn: int
    execute_turn: int
    priority: int = 100
    destination: HexCoord | None = None
    target_unit_id: str | None = None
    formation: Formation | None = None
    notes: str = ""
    ability: str | None = None
    status: OrderStatus = OrderStatus.QUEUED

    def __post_init__(self) -> None:
        if self.issued_turn < 0 or self.execute_turn < 0:
            raise ValueError("Turn numbers must be non-negative.")
        if self.execute_turn < self.issued_turn:
            raise ValueError("execute_turn cannot be earlier than issued_turn.")
        self.validate()

    @property
    def delay_turns(self) -> int:
        return self.execute_turn - self.issued_turn

    def is_ready(self, current_turn: int) -> bool:
        return self.status is OrderStatus.QUEUED and self.execute_turn <= current_turn

    def validate(self) -> None:
        if self.order_type in {OrderType.MOVE, OrderType.RETREAT} and self.destination is None:
            raise ValueError(f"{self.order_type} orders require a destination.")
        if self.order_type is OrderType.ATTACK and self.target_unit_id is None:
            raise ValueError("attack orders require a target_unit_id.")
        if self.order_type is OrderType.CHANGE_FORMATION and self.formation is None:
            raise ValueError("change_formation orders require a formation.")


@dataclass(slots=True)
class OrderBook:
    """Tracks delayed orders and releases them when their turn arrives."""

    _orders: dict[str, Order] = field(default_factory=dict)
    _sequence: int = 0

    def issue(
        self,
        order_type: OrderType,
        unit_id: str,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        destination: HexCoord | None = None,
        target_unit_id: str | None = None,
        formation: Formation | None = None,
        notes: str = "",
    ) -> Order:
        if delay_turns < 0:
            raise ValueError("delay_turns must not be negative.")

        self._sequence += 1
        order = Order(
            order_id=f"t{current_turn:04d}-o{self._sequence:05d}",
            order_type=order_type,
            unit_id=unit_id,
            issued_turn=current_turn,
            execute_turn=current_turn + delay_turns,
            priority=priority,
            destination=destination,
            target_unit_id=target_unit_id,
            formation=formation,
            notes=notes,
        )
        self._orders[order.order_id] = order
        return order

    def issue_move(
        self,
        unit_id: str,
        destination: HexCoord,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.MOVE,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            destination=destination,
            notes=notes,
        )

    def issue_attack(
        self,
        unit_id: str,
        target_unit_id: str,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        destination: HexCoord | None = None,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.ATTACK,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            destination=destination,
            target_unit_id=target_unit_id,
            notes=notes,
        )

    def issue_change_formation(
        self,
        unit_id: str,
        formation: Formation,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.CHANGE_FORMATION,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            formation=formation,
            notes=notes,
        )

    def issue_rally(
        self,
        unit_id: str,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.RALLY,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            notes=notes,
        )

    def issue_hold(
        self,
        unit_id: str,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.HOLD,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            notes=notes,
        )

    def issue_retreat(
        self,
        unit_id: str,
        destination: HexCoord,
        *,
        current_turn: int,
        delay_turns: int = 0,
        priority: int = 100,
        notes: str = "",
    ) -> Order:
        return self.issue(
            OrderType.RETREAT,
            unit_id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            destination=destination,
            notes=notes,
        )

    def issue_commander_ability(
        self,
        commander_id: str,
        target_unit_id: str,
        ability: str,
        current_turn: int,
    ) -> Order:
        return self.issue(
            OrderType.COMMANDER_ABILITY,
            commander_id,
            current_turn=current_turn,
            delay_turns=0,
            priority=5,
            target_unit_id=target_unit_id,
            notes=f"ability:{ability}",
        )

    def get(self, order_id: str) -> Order:
        return self._orders[order_id]

    def all_orders(self) -> list[Order]:
        return sorted(self._orders.values(), key=_order_sort_key)

    def orders_for_unit(
        self,
        unit_id: str,
        *,
        include_cancelled: bool = False,
    ) -> list[Order]:
        return [
            order
            for order in self.all_orders()
            if order.unit_id == unit_id
            and (include_cancelled or order.status is not OrderStatus.CANCELLED)
        ]

    def release_orders(self, current_turn: int) -> list[Order]:
        ready = [
            order
            for order in self._orders.values()
            if order.is_ready(current_turn)
        ]
        ready.sort(key=_order_sort_key)
        for order in ready:
            order.status = OrderStatus.READY
        return ready

    def cancel(self, order_id: str) -> bool:
        order = self._orders[order_id]
        if order.status is OrderStatus.RESOLVED:
            return False
        order.status = OrderStatus.CANCELLED
        return True

    def cancel_future_orders_for_unit(self, unit_id: str, *, from_turn: int) -> int:
        cancelled = 0
        for order in self._orders.values():
            if order.unit_id != unit_id:
                continue
            if order.status is not OrderStatus.QUEUED:
                continue
            if order.execute_turn < from_turn:
                continue
            order.status = OrderStatus.CANCELLED
            cancelled += 1
        return cancelled

    def mark_resolved(self, order_id: str) -> None:
        order = self._orders[order_id]
        if order.status is OrderStatus.CANCELLED:
            raise ValueError("Cancelled orders cannot be resolved.")
        order.status = OrderStatus.RESOLVED


def _order_sort_key(order: Order) -> tuple[int, int, int, str]:
    return (order.execute_turn, order.priority, order.issued_turn, order.order_id)
