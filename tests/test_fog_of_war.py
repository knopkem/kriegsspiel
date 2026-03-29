import unittest

from core.fog_of_war import FogOfWarEngine, VisibilityState
from core.map import HexCoord, HexGridMap, TerrainType
from core.units import Side, make_cavalry_squadron, make_infantry_half_battalion


class FogOfWarTestCase(unittest.TestCase):
    def test_infantry_reveals_open_ground_within_vision_range(self) -> None:
        battle_map = HexGridMap(width=7, height=3)
        infantry = make_infantry_half_battalion(
            "3-fus",
            "3rd Fusiliers",
            Side.BLUE,
            position=HexCoord(1, 1),
        )

        engine = FogOfWarEngine(battle_map)
        snapshots = engine.update([infantry], current_turn=1)
        snapshot = snapshots[Side.BLUE]

        self.assertEqual(snapshot.visibility_state(HexCoord(4, 1)), VisibilityState.VISIBLE)
        self.assertEqual(snapshot.visibility_state(HexCoord(6, 1)), VisibilityState.HIDDEN)

    def test_forest_blocks_visibility(self) -> None:
        battle_map = HexGridMap(width=7, height=1)
        battle_map.set_terrain(HexCoord(3, 0), TerrainType.FOREST)

        infantry = make_infantry_half_battalion(
            "3-fus",
            "3rd Fusiliers",
            Side.BLUE,
            position=HexCoord(0, 0),
        )

        engine = FogOfWarEngine(battle_map)
        snapshots = engine.update([infantry], current_turn=1)

        self.assertEqual(snapshots[Side.BLUE].visibility_state(HexCoord(4, 0)), VisibilityState.HIDDEN)

    def test_cavalry_sees_farther_than_infantry(self) -> None:
        battle_map = HexGridMap(width=9, height=3)
        infantry = make_infantry_half_battalion(
            "3-fus",
            "3rd Fusiliers",
            Side.BLUE,
            position=HexCoord(1, 1),
        )
        cavalry = make_cavalry_squadron(
            "1-hus",
            "1st Hussars",
            Side.RED,
            position=HexCoord(1, 1),
        )

        engine = FogOfWarEngine(battle_map)
        blue_snapshot = engine.update([infantry], current_turn=1)[Side.BLUE]
        red_snapshot = engine.update([cavalry], current_turn=1)[Side.RED]

        self.assertEqual(blue_snapshot.visibility_state(HexCoord(6, 1)), VisibilityState.HIDDEN)
        self.assertEqual(red_snapshot.visibility_state(HexCoord(6, 1)), VisibilityState.VISIBLE)

    def test_explored_hexes_persist_across_turns(self) -> None:
        battle_map = HexGridMap(width=7, height=3)
        infantry = make_infantry_half_battalion(
            "3-fus",
            "3rd Fusiliers",
            Side.BLUE,
            position=HexCoord(1, 1),
        )
        engine = FogOfWarEngine(battle_map)

        engine.update([infantry], current_turn=1)
        infantry.position = HexCoord(0, 1)
        snapshot = engine.update([infantry], current_turn=2)[Side.BLUE]

        self.assertEqual(snapshot.visibility_state(HexCoord(5, 1)), VisibilityState.EXPLORED)

    def test_last_known_enemy_position_persists_after_contact_is_lost(self) -> None:
        battle_map = HexGridMap(width=6, height=1)
        blue = make_infantry_half_battalion("3-fus", "3rd Fusiliers", Side.BLUE, position=HexCoord(0, 0))
        red = make_infantry_half_battalion("2-gren", "2nd Grenadiers", Side.RED, position=HexCoord(3, 0))
        engine = FogOfWarEngine(battle_map)

        first_snapshot = engine.update([blue, red], current_turn=1)[Side.BLUE]
        self.assertIn("2-gren", first_snapshot.visible_enemy_units)
        self.assertEqual(first_snapshot.last_known_enemies["2-gren"].position, HexCoord(3, 0))

        battle_map.set_terrain(HexCoord(2, 0), TerrainType.FOREST)
        red.position = HexCoord(5, 0)
        second_snapshot = engine.update([blue, red], current_turn=2)[Side.BLUE]

        self.assertNotIn("2-gren", second_snapshot.visible_enemy_units)
        self.assertEqual(second_snapshot.last_known_enemies["2-gren"].position, HexCoord(3, 0))
        self.assertEqual(second_snapshot.last_known_enemies["2-gren"].seen_on_turn, 1)

    def test_snapshot_persists_for_side_with_no_remaining_units(self) -> None:
        battle_map = HexGridMap(width=6, height=1)
        blue = make_infantry_half_battalion("3-fus", "3rd Fusiliers", Side.BLUE, position=HexCoord(0, 0))
        red = make_infantry_half_battalion("2-gren", "2nd Grenadiers", Side.RED, position=HexCoord(3, 0))
        engine = FogOfWarEngine(battle_map)

        engine.update([blue, red], current_turn=1)
        blue.apply_damage(blue.max_hit_points)
        snapshots = engine.update([blue, red], current_turn=2)

        self.assertIn(Side.BLUE, snapshots)
        self.assertEqual(snapshots[Side.BLUE].visible_hexes, frozenset())


if __name__ == "__main__":
    unittest.main()
