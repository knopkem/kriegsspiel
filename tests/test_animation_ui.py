"""Tests for animation manager, combat log, and score-history wiring."""

from __future__ import annotations

import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.game import GameEvent, GameState
from core.map import HexCoord
from core.scenario import load_builtin_scenario
from ui import themes
from ui.animation import (
    AnimationManager,
    CascadeRingAnimation,
    DamageNumberAnimation,
    MeleeAnimation,
    RangedFireAnimation,
    UnitMoveAnimation,
)
from ui.bitmap_font import BitmapFont
from ui.combat_log import CombatLog


class AnimationManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.surface = pygame.Surface(themes.WINDOW_SIZE)
        self.font = BitmapFont(scale=1)

    def test_add_sets_animating(self) -> None:
        mgr = AnimationManager()
        mgr.add(MeleeAnimation(duration=1.0, hex_pos=(10, 10)))
        self.assertTrue(mgr.is_animating)

    def test_update_removes_finished_animation(self) -> None:
        mgr = AnimationManager()
        anim = MeleeAnimation(duration=0.01, hex_pos=(10, 10))
        anim.start_time -= 1.0
        mgr.add(anim)
        mgr.update()
        self.assertFalse(mgr.is_animating)

    def test_skip_all_clears_queue(self) -> None:
        mgr = AnimationManager()
        mgr.add(MeleeAnimation(duration=1.0, hex_pos=(10, 10)))
        mgr.skip_all()
        self.assertFalse(mgr.is_animating)

    def test_animated_unit_centers_interpolate_move(self) -> None:
        mgr = AnimationManager()
        anim = UnitMoveAnimation(duration=1.0, unit_id="u1", from_pos=(0, 0), to_pos=(100, 0))
        anim.start_time = time.time() - 0.5
        mgr.add(anim)
        center = mgr.animated_unit_centers()["u1"]
        self.assertGreater(center[0], 40)
        self.assertLess(center[0], 60)

    def test_set_speed_preserves_animation_presence(self) -> None:
        mgr = AnimationManager()
        mgr.add(UnitMoveAnimation(duration=1.0, unit_id="u1", from_pos=(0, 0), to_pos=(10, 0)))
        mgr.set_speed(2.0)
        self.assertEqual(mgr.speed_multiplier, 2.0)
        self.assertTrue(mgr.is_animating)

    def test_draw_ranged_does_not_crash(self) -> None:
        mgr = AnimationManager()
        mgr.add(RangedFireAnimation(duration=1.0, from_pos=(0, 0), to_pos=(40, 40)))
        mgr.draw(self.surface, None, self.font)

    def test_draw_melee_does_not_crash(self) -> None:
        mgr = AnimationManager()
        mgr.add(MeleeAnimation(duration=1.0, hex_pos=(40, 40)))
        mgr.draw(self.surface, None, self.font)

    def test_draw_damage_number_does_not_crash(self) -> None:
        mgr = AnimationManager()
        mgr.add(DamageNumberAnimation(duration=1.0, pos=(20, 20), text="-4 HP"))
        mgr.draw(self.surface, None, self.font)

    def test_draw_cascade_ring_does_not_crash(self) -> None:
        mgr = AnimationManager()
        mgr.add(CascadeRingAnimation(duration=1.0, hex_pos=(20, 20)))
        mgr.draw(self.surface, None, self.font)


class CombatLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.surface = pygame.Surface(themes.WINDOW_SIZE)
        self.font = BitmapFont(scale=1)
        self.rect = pygame.Rect(10, 10, 400, 140)
        self.events = [
            GameEvent(turn=1, category="combat", message="Combat", coord=HexCoord(1, 1)),
            GameEvent(turn=1, category="movement", message="Move", coord=HexCoord(2, 2)),
            GameEvent(turn=1, category="morale", message="Morale", coord=HexCoord(3, 3)),
            GameEvent(turn=1, category="hold", message="Hold", coord=None),
        ]

    def test_cycle_filter_changes_filter(self) -> None:
        log = CombatLog()
        log.cycle_filter()
        self.assertEqual(log._filter, "combat")

    def test_draw_does_not_crash(self) -> None:
        log = CombatLog()
        log.draw(self.surface, self.rect, self.events, self.font)

    def test_click_filter_selects_filter(self) -> None:
        log = CombatLog()
        log.draw(self.surface, self.rect, self.events, self.font)
        combat_rect = next(rect for rect, name in log._filter_rects if name == "combat")
        changed = log.click_filter(combat_rect.center)
        self.assertTrue(changed)
        self.assertEqual(log._filter, "combat")

    def test_coord_for_click_returns_event_coord(self) -> None:
        log = CombatLog()
        log.draw(self.surface, self.rect, self.events, self.font)
        coord = log.coord_for_click(log._entry_rects[0][0].center)
        self.assertEqual(coord, HexCoord(1, 1))

    def test_scroll_never_negative(self) -> None:
        log = CombatLog()
        log.scroll(-10)
        self.assertEqual(log.scroll_offset, 0)


class ScoreHistoryTest(unittest.TestCase):
    def test_score_history_grows_after_turn(self) -> None:
        game = GameState.from_scenario(load_builtin_scenario("tutorial"), rng_seed=1)
        self.assertEqual(game.score_history, [])
        game.advance_turn()
        self.assertEqual(len(game.score_history), 1)


if __name__ == "__main__":
    unittest.main()
