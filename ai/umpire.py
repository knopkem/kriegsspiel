"""Digital umpire that sanitizes structured orders against game state."""

from __future__ import annotations

from dataclasses import dataclass

from core.game import GameState
from core.orders import Order, OrderType


@dataclass(slots=True)
class DigitalUmpire:
    """Conservative adjudication for impossible or stale orders."""

    def sanitize_order(self, game: GameState, order: Order) -> Order:
        unit = game.units[order.unit_id]
        if unit.is_removed or unit.position is None:
            raise ValueError("Removed units cannot receive orders.")

        if order.order_type in {OrderType.MOVE, OrderType.RETREAT} and order.destination is not None:
            path = game.battle_map.find_path(unit.position, order.destination, terrain_costs=unit.movement_costs())
            if not path:
                order.destination = unit.position

        if order.order_type is OrderType.ATTACK and order.target_unit_id is not None:
            target = game.units[order.target_unit_id]
            if target.is_removed or target.position is None:
                raise ValueError("Attack target is no longer valid.")
        return order

