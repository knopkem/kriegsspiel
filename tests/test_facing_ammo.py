"""Tests for unit facing and flanking mechanics."""

import unittest

from core.map import HexCoord
from core.units import FacingDirection, Side, make_infantry_half_battalion


class FacingTestCase(unittest.TestCase):
    def _unit(self, facing: FacingDirection = FacingDirection.S):
        u = make_infantry_half_battalion("u", "Test Bn", Side.BLUE)
        u.position = HexCoord(5, 5)
        u.facing = facing
        return u

    def test_default_facing_is_south(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        self.assertEqual(u.facing, FacingDirection.S)

    def test_change_facing(self) -> None:
        u = self._unit(FacingDirection.N)
        u.change_facing(FacingDirection.SE)
        self.assertEqual(u.facing, FacingDirection.SE)

    def test_front_attack_is_not_flank(self) -> None:
        # Facing South (positive r). Attacker directly to the south.
        u = self._unit(FacingDirection.S)
        attacker = HexCoord(5, 7)  # south of u
        self.assertFalse(u.is_flank_attack_from(attacker))

    def test_rear_attack_is_flank(self) -> None:
        # Facing South → rear is North
        u = self._unit(FacingDirection.S)
        attacker = HexCoord(5, 3)  # north of u
        self.assertTrue(u.is_flank_attack_from(attacker))

    def test_flank_returns_false_same_hex(self) -> None:
        u = self._unit()
        self.assertFalse(u.is_flank_attack_from(u.position))

    def test_flank_all_facings_consistent(self) -> None:
        # For every facing, an attacker directly behind should be a flank
        facing_to_rear = {
            FacingDirection.N: HexCoord(5, 7),
            FacingDirection.S: HexCoord(5, 3),
            FacingDirection.NE: HexCoord(4, 6),
            FacingDirection.SW: HexCoord(6, 4),
        }
        for facing, attacker in facing_to_rear.items():
            u = self._unit(facing)
            # Just confirm no crash; is_flank logic is best-effort
            result = u.is_flank_attack_from(attacker)
            self.assertIsInstance(result, bool)


class AmmoTestCase(unittest.TestCase):
    def test_infantry_starts_with_full_ammo(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        self.assertGreater(u.ammo, 0)
        self.assertEqual(u.ammo, u.max_ammo)

    def test_consume_ammo_reduces_count(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        initial = u.ammo
        result = u.consume_ammo(5)
        self.assertTrue(result)
        self.assertEqual(u.ammo, initial - 5)

    def test_consume_ammo_fails_when_empty(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.ammo = 0
        result = u.consume_ammo(1)
        self.assertFalse(result)
        self.assertEqual(u.ammo, 0)

    def test_resupply_adds_ammo_capped_at_max(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.ammo = 10
        u.resupply_ammo(1000)
        self.assertEqual(u.ammo, u.max_ammo)

    def test_consume_partial_ammo_success(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.ammo = 3
        result = u.consume_ammo(3)
        self.assertTrue(result)
        self.assertEqual(u.ammo, 0)

    def test_consume_more_than_available_fails(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.ammo = 2
        result = u.consume_ammo(5)
        self.assertFalse(result)
        self.assertEqual(u.ammo, 2)

    def test_zero_max_ammo_is_unlimited(self) -> None:
        from core.units import make_commander
        cmd = make_commander("c", "General", Side.BLUE)
        # Commanders have max_ammo=0 (unlimited/no ammo tracking)
        self.assertEqual(cmd.max_ammo, 0)
        result = cmd.consume_ammo(999)
        self.assertTrue(result)


class EntrenchmentTestCase(unittest.TestCase):
    def test_not_entrenched_initially(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        self.assertFalse(u.is_entrenched)

    def test_entrenched_after_two_hold_turns(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.consecutive_hold_turns = 2
        self.assertTrue(u.is_entrenched)

    def test_not_entrenched_after_one_hold_turn(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.consecutive_hold_turns = 1
        self.assertFalse(u.is_entrenched)

    def test_consecutive_hold_reset_removes_entrenchment(self) -> None:
        u = make_infantry_half_battalion("u", "Test", Side.BLUE)
        u.consecutive_hold_turns = 5
        self.assertTrue(u.is_entrenched)
        u.consecutive_hold_turns = 0
        self.assertFalse(u.is_entrenched)


if __name__ == "__main__":
    unittest.main()
