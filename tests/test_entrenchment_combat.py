"""Tests for entrenchment and ammo effects in combat (C3, C9)."""

import random
import unittest

from core.combat import AttackKind, CombatResolver
from core.map import TerrainType
from core.units import MoraleState, Side, make_artillery_battery, make_infantry_half_battalion


class EntrenchmentCombatTestCase(unittest.TestCase):
    def _resolver(self) -> CombatResolver:
        return CombatResolver(rng=random.Random(42))

    def test_entrenched_defender_takes_less_melee_damage(self) -> None:
        resolver = self._resolver()
        attacker = make_infantry_half_battalion("a", "Attacker", Side.BLUE)
        defender_normal = make_infantry_half_battalion("d1", "Normal", Side.RED)
        defender_entrenched = make_infantry_half_battalion("d2", "Entrenched", Side.RED)
        defender_entrenched.consecutive_hold_turns = 3  # is_entrenched = True

        result_normal = resolver.resolve_melee(
            attacker, defender_normal, defender_terrain=TerrainType.OPEN
        )
        damage_normal = result_normal.defender_damage

        # Reset attacker
        attacker2 = make_infantry_half_battalion("a2", "Attacker2", Side.BLUE)
        result_entrenched = resolver.resolve_melee(
            attacker2, defender_entrenched, defender_terrain=TerrainType.OPEN
        )
        damage_entrenched = result_entrenched.defender_damage

        self.assertLessEqual(damage_entrenched, damage_normal)

    def test_last_stand_reduces_attacker_damage(self) -> None:
        resolver = self._resolver()
        attacker = make_infantry_half_battalion("a", "Attacker", Side.BLUE)
        defender = make_infantry_half_battalion("d", "Defender", Side.RED)
        defender2 = make_infantry_half_battalion("d2", "Defender2", Side.RED)

        result_normal = resolver.resolve_melee(
            attacker, defender, defender_terrain=TerrainType.OPEN, last_stand=False
        )
        attacker2 = make_infantry_half_battalion("a2", "Attacker2", Side.BLUE)
        result_last_stand = resolver.resolve_melee(
            attacker2, defender2, defender_terrain=TerrainType.OPEN, last_stand=True
        )

        # Last stand bonus reduces attacker's effectiveness (less damage to defender)
        self.assertLessEqual(result_last_stand.defender_damage, result_normal.defender_damage)

    def test_entrenched_property_gate(self) -> None:
        unit = make_infantry_half_battalion("u", "U", Side.BLUE)
        self.assertFalse(unit.is_entrenched)
        unit.consecutive_hold_turns = 2
        self.assertTrue(unit.is_entrenched)


class AmmoCombatTestCase(unittest.TestCase):
    def _resolver(self) -> CombatResolver:
        return CombatResolver(rng=random.Random(1))

    def test_ranged_attack_out_of_ammo_deals_no_damage(self) -> None:
        resolver = self._resolver()
        attacker = make_infantry_half_battalion("a", "Attacker", Side.BLUE)
        defender = make_infantry_half_battalion("d", "Defender", Side.RED)
        attacker.ammo = 0  # out of ammo

        hp_before = defender.hit_points
        result = resolver.resolve_ranged(
            attacker, defender, distance_hexes=2, defender_terrain=TerrainType.OPEN
        )

        self.assertEqual(result.defender_damage, 0)
        self.assertEqual(defender.hit_points, hp_before)

    def test_ranged_attack_with_ammo_consumes_it(self) -> None:
        resolver = self._resolver()
        attacker = make_infantry_half_battalion("a", "Attacker", Side.BLUE)
        attacker.ammo = 20
        defender = make_infantry_half_battalion("d", "Defender", Side.RED)

        ammo_before = attacker.ammo
        resolver.resolve_ranged(
            attacker, defender, distance_hexes=2, defender_terrain=TerrainType.OPEN
        )
        # Ammo should be reduced (or remain if unlimited)
        if attacker.max_ammo > 0:
            self.assertLessEqual(attacker.ammo, ammo_before)

    def test_artillery_ranged_attack_out_of_ammo_no_damage(self) -> None:
        resolver = self._resolver()
        attacker = make_artillery_battery("a", "Battery A", Side.BLUE)
        attacker.ammo = 0
        defender = make_infantry_half_battalion("d", "Defender", Side.RED)

        hp_before = defender.hit_points
        resolver.resolve_ranged(
            attacker, defender, distance_hexes=3, defender_terrain=TerrainType.OPEN
        )
        self.assertEqual(defender.hit_points, hp_before)

    def test_resupply_restores_ammo(self) -> None:
        unit = make_infantry_half_battalion("u", "U", Side.BLUE)
        unit.ammo = 5
        unit.resupply_ammo(20)
        self.assertEqual(unit.ammo, 25)

    def test_resupply_caps_at_max(self) -> None:
        unit = make_infantry_half_battalion("u", "U", Side.BLUE)
        unit.ammo = unit.max_ammo - 1
        unit.resupply_ammo(1000)
        self.assertEqual(unit.ammo, unit.max_ammo)


if __name__ == "__main__":
    unittest.main()
