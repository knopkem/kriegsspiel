import unittest

from core.map import HexCoord, HexGridMap, TerrainType
from core.units import Side, make_infantry_half_battalion


class HexGridMapTestCase(unittest.TestCase):
    def test_hex_distance_uses_axial_coordinates(self) -> None:
        start = HexCoord(0, 0)
        end = HexCoord(3, 2)

        self.assertEqual(start.distance_to(end), 5)

    def test_pathfinding_avoids_impassable_river_hexes(self) -> None:
        battle_map = HexGridMap.from_terrain_rows(
            [
                ".....",
                "..w..",
                "..w..",
                ".....",
                ".....",
            ]
        )

        path = battle_map.find_path(HexCoord(0, 2), HexCoord(4, 2))

        self.assertTrue(path)
        self.assertNotIn(HexCoord(2, 1), path)
        self.assertNotIn(HexCoord(2, 2), path)
        self.assertEqual(path[0], HexCoord(0, 2))
        self.assertEqual(path[-1], HexCoord(4, 2))

    def test_unit_specific_terrain_costs_prefer_roads(self) -> None:
        battle_map = HexGridMap.from_terrain_rows(
            [
                "rrrrr",
                ".mmm.",
                ".....",
            ]
        )
        infantry = make_infantry_half_battalion("3-fus", "3rd Fusiliers", Side.BLUE)

        path = battle_map.find_path(
            HexCoord(0, 1),
            HexCoord(4, 1),
            terrain_costs=infantry.movement_costs(),
        )

        self.assertTrue(any(coord.r == 0 for coord in path))

    def test_line_of_sight_is_blocked_by_forest(self) -> None:
        battle_map = HexGridMap.from_terrain_rows(["..f.."])

        visible = battle_map.has_line_of_sight(HexCoord(0, 0), HexCoord(4, 0))

        self.assertFalse(visible)

    def test_line_of_sight_is_blocked_by_high_ground(self) -> None:
        battle_map = HexGridMap.from_terrain_rows(["....."])
        battle_map.set_elevation(HexCoord(2, 0), 40.0)

        visible = battle_map.has_line_of_sight(HexCoord(0, 0), HexCoord(4, 0))

        self.assertFalse(visible)

    def test_open_ground_line_of_sight_is_clear(self) -> None:
        battle_map = HexGridMap.from_terrain_rows(["....."])

        visible = battle_map.has_line_of_sight(HexCoord(0, 0), HexCoord(4, 0))

        self.assertTrue(visible)

    def test_neighbors_skip_impassable_by_default(self) -> None:
        battle_map = HexGridMap(width=3, height=3)
        battle_map.set_terrain(HexCoord(1, 0), TerrainType.RIVER)

        neighbors = battle_map.neighbors(HexCoord(0, 0))

        self.assertNotIn(HexCoord(1, 0), neighbors)


if __name__ == "__main__":
    unittest.main()
