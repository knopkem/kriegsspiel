import unittest

from core.map import TerrainType
from core.units import (
    FatigueLevel,
    Formation,
    InfantryExchangeState,
    Side,
    make_cavalry_squadron,
    make_infantry_half_battalion,
)


class UnitTestCase(unittest.TestCase):
    def test_infantry_factory_uses_historical_defaults(self) -> None:
        infantry = make_infantry_half_battalion("3-fus", "3rd Fusiliers", Side.BLUE)

        self.assertEqual(infantry.max_strength, 450)
        self.assertEqual(infantry.max_hit_points, 90)
        self.assertEqual(infantry.formation, Formation.COLUMN)
        self.assertEqual(infantry.current_strength, 450)
        self.assertEqual(infantry.frontage_ratio, 1.0)

    def test_infantry_exchange_piece_thresholds_follow_damage_bands(self) -> None:
        infantry = make_infantry_half_battalion("3-fus", "3rd Fusiliers", Side.BLUE)

        infantry.apply_damage(15)
        self.assertEqual(infantry.infantry_exchange_state, InfantryExchangeState.FIVE_SIXTHS)
        self.assertAlmostEqual(infantry.frontage_ratio, 5 / 6)

        infantry.apply_damage(15)
        self.assertEqual(infantry.infantry_exchange_state, InfantryExchangeState.FOUR_SIXTHS)
        self.assertAlmostEqual(infantry.frontage_ratio, 4 / 6)

        infantry.apply_damage(15)
        self.assertEqual(infantry.infantry_exchange_state, InfantryExchangeState.BROKEN)
        self.assertTrue(infantry.is_removed)

    def test_cavalry_movement_allowance_drops_with_fatigue(self) -> None:
        cavalry = make_cavalry_squadron("1-hus", "1st Hussars", Side.RED)
        baseline = cavalry.movement_allowance(TerrainType.ROAD)

        cavalry.add_fatigue(60)
        fatigued = cavalry.movement_allowance(TerrainType.ROAD)

        self.assertEqual(cavalry.fatigue_level, FatigueLevel.WEARY)
        self.assertLess(fatigued, baseline)

    def test_invalid_formation_change_raises(self) -> None:
        cavalry = make_cavalry_squadron("1-hus", "1st Hussars", Side.RED)

        with self.assertRaises(ValueError):
            cavalry.change_formation(Formation.SQUARE)

    def test_non_infantry_units_do_not_use_exchange_pieces(self) -> None:
        cavalry = make_cavalry_squadron("1-hus", "1st Hussars", Side.RED)
        cavalry.apply_damage(10)

        self.assertIsNone(cavalry.infantry_exchange_state)
        self.assertFalse(cavalry.is_removed)


if __name__ == "__main__":
    unittest.main()
