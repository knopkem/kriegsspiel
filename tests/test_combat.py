import random
import unittest

from core.combat import AttackKind, CombatResolver
from core.map import TerrainType
from core.units import Formation, MoraleState, Side, make_artillery_battery, make_cavalry_squadron, make_infantry_half_battalion


class CombatResolverTestCase(unittest.TestCase):
    def test_infantry_ranged_attack_inflicts_damage(self) -> None:
        resolver = CombatResolver(rng=random.Random(1))
        attacker = make_infantry_half_battalion("a", "3rd Fusiliers", Side.BLUE)
        defender = make_infantry_half_battalion("d", "2nd Grenadiers", Side.RED)

        result = resolver.resolve_ranged(attacker, defender, distance_hexes=2, defender_terrain=TerrainType.OPEN)

        self.assertEqual(result.attack_kind, AttackKind.RANGED)
        self.assertGreater(result.defender_damage, 0)
        self.assertLess(defender.hit_points, defender.max_hit_points)

    def test_cavalry_charge_into_square_is_costly(self) -> None:
        resolver = CombatResolver(rng=random.Random(2))
        cavalry = make_cavalry_squadron("c", "1st Hussars", Side.BLUE)
        infantry = make_infantry_half_battalion("i", "3rd Fusiliers", Side.RED)
        infantry.change_formation(Formation.SQUARE)

        result = resolver.resolve_melee(cavalry, infantry, defender_terrain=TerrainType.OPEN)

        self.assertGreaterEqual(result.attacker_damage, result.defender_damage)

    def test_artillery_counter_battery_is_supported(self) -> None:
        resolver = CombatResolver(rng=random.Random(3))
        attacker = make_artillery_battery("a", "Battery A", Side.BLUE)
        defender = make_artillery_battery("d", "Battery B", Side.RED)
        attacker.change_formation(Formation.UNLIMBERED)

        result = resolver.resolve_ranged(attacker, defender, distance_hexes=4, defender_terrain=TerrainType.OPEN)

        self.assertGreater(result.defender_damage, 0)

    def test_heavy_ranged_damage_can_shake_unit(self) -> None:
        resolver = CombatResolver(rng=random.Random(4))
        attacker = make_artillery_battery("a", "Battery A", Side.BLUE)
        attacker.change_formation(Formation.UNLIMBERED)
        defender = make_infantry_half_battalion("d", "2nd Grenadiers", Side.RED)

        resolver.resolve_ranged(attacker, defender, distance_hexes=1, defender_terrain=TerrainType.OPEN)

        self.assertIn(defender.morale_state, {MoraleState.SHAKEN, MoraleState.ROUTING, MoraleState.BROKEN})


if __name__ == "__main__":
    unittest.main()
