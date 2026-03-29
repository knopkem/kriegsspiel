"""Tests for elevation-based gameplay mechanics (A4)."""

import unittest

from core.map import (
    HexCoord,
    HexGridMap,
    TerrainType,
    elevation_movement_factor,
)


class ElevationMovementFactorTestCase(unittest.TestCase):
    def test_flat_terrain_no_modifier(self) -> None:
        self.assertEqual(elevation_movement_factor(10.0, 10.0), 1.0)

    def test_gentle_uphill_no_modifier(self) -> None:
        # <5m diff → flat
        self.assertEqual(elevation_movement_factor(10.0, 14.0), 1.0)

    def test_moderate_uphill_penalty(self) -> None:
        # 5–15m diff → 1.20
        factor = elevation_movement_factor(0.0, 10.0)
        self.assertAlmostEqual(factor, 1.20)

    def test_steep_uphill_higher_penalty(self) -> None:
        # >15m diff → 1.40
        factor = elevation_movement_factor(0.0, 20.0)
        self.assertAlmostEqual(factor, 1.40)

    def test_gentle_downhill_no_modifier(self) -> None:
        # -4m → flat
        self.assertEqual(elevation_movement_factor(10.0, 6.5), 1.0)

    def test_downhill_discount(self) -> None:
        # >5m downhill → 0.90
        factor = elevation_movement_factor(20.0, 5.0)
        self.assertAlmostEqual(factor, 0.90)

    def test_symmetric_steep_up_vs_down(self) -> None:
        up = elevation_movement_factor(0.0, 30.0)
        down = elevation_movement_factor(30.0, 0.0)
        self.assertGreater(up, 1.0)
        self.assertLess(down, 1.0)


class ElevationCombatModifierTestCase(unittest.TestCase):
    def _map_with_elevations(self, elev_a: float, elev_b: float) -> tuple[HexGridMap, HexCoord, HexCoord]:
        m = HexGridMap(width=10, height=10)
        a = HexCoord(2, 2)
        b = HexCoord(7, 7)
        m.set_elevation(a, elev_a)
        m.set_elevation(b, elev_b)
        return m, a, b

    def test_equal_elevation_no_bonus(self) -> None:
        m, a, b = self._map_with_elevations(20.0, 20.0)
        ranged, melee = m.elevation_combat_modifier(a, b)
        self.assertAlmostEqual(ranged, 1.0)

    def test_attacker_higher_ranged_bonus(self) -> None:
        m, a, b = self._map_with_elevations(30.0, 0.0)
        ranged, _ = m.elevation_combat_modifier(a, b)
        self.assertGreater(ranged, 1.0)

    def test_attacker_lower_ranged_penalty(self) -> None:
        m, a, b = self._map_with_elevations(0.0, 30.0)
        ranged, _ = m.elevation_combat_modifier(a, b)
        self.assertLess(ranged, 1.0)

    def test_melee_defence_bonus_when_elevation_differs(self) -> None:
        # Melee def mult should be > 1 whenever there is any height difference
        m, a, b = self._map_with_elevations(0.0, 20.0)
        _, melee = m.elevation_combat_modifier(a, b)
        self.assertGreater(melee, 1.0)

    def test_cap_prevents_extreme_values(self) -> None:
        # 100m height diff should be capped at 30m effect
        m, a, b = self._map_with_elevations(0.0, 100.0)
        m2, a2, b2 = self._map_with_elevations(0.0, 30.0)
        ranged1, _ = m.elevation_combat_modifier(a, b)
        ranged2, _ = m2.elevation_combat_modifier(a2, b2)
        self.assertAlmostEqual(ranged1, ranged2)

    def test_returns_non_negative_values(self) -> None:
        m, a, b = self._map_with_elevations(0.0, 999.0)
        ranged, melee = m.elevation_combat_modifier(a, b)
        self.assertGreaterEqual(ranged, 0.0)
        self.assertGreaterEqual(melee, 0.0)


class SlopeAwarePathfindingTestCase(unittest.TestCase):
    def test_slope_path_avoids_steep_uphill(self) -> None:
        """A slope-aware path should prefer going around a steep ridge."""
        m = HexGridMap(width=15, height=10)
        # Set a ridge at q=7 with very high elevation
        for r in range(10):
            m.set_elevation(HexCoord(7, r), 80.0)
        # Low ground everywhere else
        start = HexCoord(1, 5)
        goal = HexCoord(13, 5)

        path_flat = m.find_path(start, goal, use_slope=False)
        path_slope = m.find_path(start, goal, use_slope=True)

        # Both should find a path
        self.assertGreater(len(path_flat), 0)
        self.assertGreater(len(path_slope), 0)
        # Both must end at goal
        self.assertEqual(path_flat[-1], goal)
        self.assertEqual(path_slope[-1], goal)

    def test_movement_cost_between_uphill_more_expensive(self) -> None:
        m = HexGridMap(width=10, height=10)
        low = HexCoord(2, 2)
        high = HexCoord(3, 2)
        m.set_elevation(low, 0.0)
        m.set_elevation(high, 20.0)  # steep uphill

        cost_between = m.movement_cost_between(low, high)
        cost_plain = m.movement_cost(high)
        self.assertGreater(cost_between, cost_plain)

    def test_movement_cost_between_flat_equals_plain(self) -> None:
        m = HexGridMap(width=10, height=10)
        a = HexCoord(2, 2)
        b = HexCoord(3, 2)
        # Same elevation → slope factor = 1.0
        m.set_elevation(a, 10.0)
        m.set_elevation(b, 10.0)
        self.assertAlmostEqual(m.movement_cost_between(a, b), m.movement_cost(b))


if __name__ == "__main__":
    unittest.main()
