import unittest

from core.map import HexCoord
from core.orders import Order, OrderBook, OrderStatus, OrderType
from core.units import Formation


class OrderBookTestCase(unittest.TestCase):
    def test_move_order_is_released_only_when_delay_expires(self) -> None:
        book = OrderBook()
        order = book.issue_move(
            "3-fus",
            HexCoord(4, 3),
            current_turn=2,
            delay_turns=2,
        )

        self.assertEqual(book.release_orders(3), [])

        ready = book.release_orders(4)

        self.assertEqual([item.order_id for item in ready], [order.order_id])
        self.assertEqual(order.status, OrderStatus.READY)
        self.assertEqual(order.delay_turns, 2)

    def test_release_orders_sorts_by_priority(self) -> None:
        book = OrderBook()
        book.issue_hold("reserve", current_turn=1, priority=50)
        book.issue_rally("center", current_turn=1, priority=10)

        ready = book.release_orders(1)

        self.assertEqual([order.unit_id for order in ready], ["center", "reserve"])

    def test_cancel_future_orders_for_unit_only_cancels_matching_orders(self) -> None:
        book = OrderBook()
        future = book.issue_move("3-fus", HexCoord(3, 3), current_turn=1, delay_turns=2)
        immediate = book.issue_hold("3-fus", current_turn=1)
        other_unit = book.issue_hold("1-hus", current_turn=1, delay_turns=3)

        cancelled = book.cancel_future_orders_for_unit("3-fus", from_turn=2)

        self.assertEqual(cancelled, 1)
        self.assertEqual(book.get(future.order_id).status, OrderStatus.CANCELLED)
        self.assertEqual(book.get(immediate.order_id).status, OrderStatus.QUEUED)
        self.assertEqual(book.get(other_unit.order_id).status, OrderStatus.QUEUED)

    def test_change_formation_orders_require_a_formation(self) -> None:
        with self.assertRaises(ValueError):
            Order(
                order_id="bad",
                order_type=OrderType.CHANGE_FORMATION,
                unit_id="3-fus",
                issued_turn=1,
                execute_turn=1,
            )

    def test_attack_orders_require_a_target_unit(self) -> None:
        with self.assertRaises(ValueError):
            Order(
                order_id="bad",
                order_type=OrderType.ATTACK,
                unit_id="3-fus",
                issued_turn=1,
                execute_turn=1,
                destination=HexCoord(4, 4),
            )

    def test_issue_change_formation_sets_payload(self) -> None:
        book = OrderBook()
        order = book.issue_change_formation(
            "3-fus",
            Formation.LINE,
            current_turn=5,
            delay_turns=1,
        )

        self.assertEqual(order.formation, Formation.LINE)
        self.assertEqual(order.execute_turn, 6)


if __name__ == "__main__":
    unittest.main()
