"""Command delay calculations for written orders and couriers."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable

from .map import HexCoord, HexGridMap
from .orders import Order, OrderBook, OrderType
from .units import Unit, UnitType


@dataclass(slots=True)
class MessengerSystem:
    battle_map: HexGridMap
    courier_speed_paces_per_turn: int = 300
    interception_radius: int = 2

    def delay_turns(self, origin: HexCoord, destination: HexCoord) -> int:
        distance_paces = origin.distance_to(destination) * 100
        if distance_paces == 0:
            return 0
        return max(0, math.ceil(distance_paces / self.courier_speed_paces_per_turn) - 1)

    def issue_order(
        self,
        order_book: OrderBook,
        *,
        commander: Unit,
        recipient: Unit,
        order_type: OrderType,
        current_turn: int,
        priority: int = 100,
        destination: HexCoord | None = None,
        target_unit_id: str | None = None,
        formation=None,
        notes: str = "",
    ) -> Order:
        if commander.position is None or recipient.position is None:
            raise ValueError("Commander and recipient must both have positions.")

        delay_turns = self.delay_turns(commander.position, recipient.position)
        return order_book.issue(
            order_type,
            recipient.id,
            current_turn=current_turn,
            delay_turns=delay_turns,
            priority=priority,
            destination=destination,
            target_unit_id=target_unit_id,
            formation=formation,
            notes=notes,
        )

    def interception_risk(
        self,
        origin: HexCoord,
        destination: HexCoord,
        *,
        enemy_units: Iterable[Unit],
    ) -> float:
        path = origin.line_to(destination)
        risk = 0.0
        for enemy in enemy_units:
            if enemy.position is None or enemy.is_removed:
                continue
            if enemy.unit_type not in {UnitType.CAVALRY, UnitType.SKIRMISHER}:
                continue
            if any(enemy.position.distance_to(step) <= self.interception_radius for step in path):
                risk += 0.15 if enemy.unit_type is UnitType.SKIRMISHER else 0.25
        return min(0.75, risk)

    def was_intercepted(
        self,
        origin: HexCoord,
        destination: HexCoord,
        *,
        enemy_units: Iterable[Unit],
        rng: random.Random | None = None,
    ) -> bool:
        roller = rng or random.Random()
        return roller.random() < self.interception_risk(origin, destination, enemy_units=enemy_units)

