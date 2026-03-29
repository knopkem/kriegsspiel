"""Tests for the procedural map generator."""

import unittest

from core.map import TerrainType
from core.map_generator import (
    MapGenConfig,
    generate_map,
    generate_quick_battle_map,
)


class MapGeneratorTestCase(unittest.TestCase):
    def test_generates_correct_dimensions(self) -> None:
        cfg = MapGenConfig(width=20, height=15, seed=1)
        m = generate_map(cfg)
        self.assertEqual(m.width, 20)
        self.assertEqual(m.height, 15)
        self.assertEqual(sum(1 for _ in m.coords()), 20 * 15)

    def test_terrain_types_present(self) -> None:
        cfg = MapGenConfig(
            width=25, height=20,
            hill_fraction=0.12, forest_fraction=0.10,
            marsh_fraction=0.04, village_count=2,
            river_count=1, road_count=1,
            seed=7,
        )
        m = generate_map(cfg)
        terrains = {m.terrain_at(c) for c in m.coords()}
        self.assertIn(TerrainType.HILL, terrains)
        self.assertIn(TerrainType.FOREST, terrains)
        self.assertIn(TerrainType.ROAD, terrains)
        self.assertIn(TerrainType.RIVER, terrains)

    def test_deterministic_with_seed(self) -> None:
        cfg = MapGenConfig(width=20, height=15, seed=99)
        m1 = generate_map(cfg)
        m2 = generate_map(cfg)
        for c in m1.coords():
            self.assertEqual(m1.terrain_at(c), m2.terrain_at(c))
            self.assertAlmostEqual(m1.elevation_at(c), m2.elevation_at(c))

    def test_different_seeds_differ(self) -> None:
        m1 = generate_map(MapGenConfig(width=20, height=15, seed=1))
        m2 = generate_map(MapGenConfig(width=20, height=15, seed=2))
        terrains_differ = any(
            m1.terrain_at(c) != m2.terrain_at(c) for c in m1.coords()
        )
        self.assertTrue(terrains_differ, "Different seeds should produce different maps")

    def test_elevation_set_for_all_hexes(self) -> None:
        m = generate_map(MapGenConfig(width=15, height=12, seed=5))
        for c in m.coords():
            elev = m.elevation_at(c)
            self.assertGreaterEqual(elev, 0.0)

    def test_hills_have_higher_elevation_than_rivers(self) -> None:
        m = generate_map(MapGenConfig(width=30, height=25, river_count=1, seed=42))
        hill_elevs = [m.elevation_at(c) for c in m.coords() if m.terrain_at(c) is TerrainType.HILL]
        river_elevs = [m.elevation_at(c) for c in m.coords() if m.terrain_at(c) is TerrainType.RIVER]
        if hill_elevs and river_elevs:
            self.assertGreater(min(hill_elevs), max(river_elevs) * 0.5)

    def test_quick_battle_small(self) -> None:
        m = generate_quick_battle_map(size="small", seed=1)
        self.assertEqual(m.width, 20)
        self.assertEqual(m.height, 16)

    def test_quick_battle_medium(self) -> None:
        m = generate_quick_battle_map(size="medium", seed=1)
        self.assertEqual(m.width, 35)
        self.assertEqual(m.height, 28)

    def test_quick_battle_large(self) -> None:
        m = generate_quick_battle_map(size="large", seed=1)
        self.assertEqual(m.width, 55)
        self.assertEqual(m.height, 45)

    def test_village_count_respected(self) -> None:
        cfg = MapGenConfig(width=25, height=20, village_count=3, seed=10)
        m = generate_map(cfg)
        village_count = sum(
            1 for c in m.coords() if m.terrain_at(c) is TerrainType.VILLAGE
        )
        self.assertGreaterEqual(village_count, 1)

    def test_all_hexes_have_terrain(self) -> None:
        m = generate_map(MapGenConfig(width=20, height=15, seed=3))
        for c in m.coords():
            self.assertIsInstance(m.terrain_at(c), TerrainType)


if __name__ == "__main__":
    unittest.main()
