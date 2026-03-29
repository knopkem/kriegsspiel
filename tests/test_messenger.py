import unittest

from core.map import HexCoord, HexGridMap
from core.messenger import MessengerSystem
from core.orders import OrderBook, OrderType
from core.units import Side, make_cavalry_squadron, make_commander, make_infantry_half_battalion, make_skirmisher_detachment


class MessengerSystemTestCase(unittest.TestCase):
    def test_delay_turns_scale_with_distance(self) -> None:
        system = MessengerSystem(HexGridMap(width=10, height=10))

        self.assertEqual(system.delay_turns(HexCoord(0, 0), HexCoord(2, 0)), 0)
        self.assertEqual(system.delay_turns(HexCoord(0, 0), HexCoord(4, 0)), 1)

    def test_issue_order_uses_commander_distance_to_recipient(self) -> None:
        battle_map = HexGridMap(width=10, height=10)
        system = MessengerSystem(battle_map)
        commander = make_commander("hq", "Maj. Braun", Side.BLUE, position=HexCoord(0, 0))
        infantry = make_infantry_half_battalion("inf", "3rd Fusiliers", Side.BLUE, position=HexCoord(4, 0))
        book = OrderBook()

        order = system.issue_order(
            book,
            commander=commander,
            recipient=infantry,
            order_type=OrderType.HOLD,
            current_turn=1
        )

        self.assertEqual(order.execute_turn, 2)

    def test_interception_risk_detects_enemy_scouts_near_path(self) -> None:
        system = MessengerSystem(HexGridMap(width=10, height=10))
        enemy_cav = make_cavalry_squadron("c", "1st Hussars", Side.RED, position=HexCoord(2, 0))
        enemy_skr = make_skirmisher_detachment("s", "Jaegers", Side.RED, position=HexCoord(3, 1))

        risk = system.interception_risk(HexCoord(0, 0), HexCoord(5, 0), enemy_units=[enemy_cav, enemy_skr])

        self.assertGreater(risk, 0.0)


if __name__ == "__main__":
    unittest.main()
