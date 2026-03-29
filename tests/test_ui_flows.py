"""Headless tests for scenario select and quick battle widgets."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ui import themes
from ui.bitmap_font import BitmapFont
from ui.quick_battle import QuickBattle
from ui.scenario_select import ScenarioSelect


class _PygameTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.surface = pygame.Surface(themes.WINDOW_SIZE)
        self.font = BitmapFont(scale=2)
        self.small_font = BitmapFont(scale=1)


class QuickBattleTest(_PygameTestCase):
    def test_enter_returns_default_config(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result["size"], "medium")
        self.assertEqual(result["force"], "balanced")
        self.assertEqual(result["difficulty"], "medium")

    def test_left_right_change_focused_size(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result["size"], "large")

    def test_down_then_right_changes_force(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result["force"], "heavy")

    def test_down_twice_then_left_changes_difficulty(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result["difficulty"], "easy")

    def test_escape_returns_back(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(result, "back")

    def test_start_button_click_returns_config(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._start_rect.center))
        self.assertIsInstance(result, dict)

    def test_back_button_click_returns_back(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._back_rect.center))
        self.assertEqual(result, "back")

    def test_draw_does_not_crash(self) -> None:
        ui = QuickBattle(self.font, self.small_font)
        ui.draw(self.surface)


class ScenarioSelectTest(_PygameTestCase):
    def test_scenarios_are_loaded(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        self.assertGreater(len(ui._scenarios), 0)

    def test_enter_returns_selected_scenario(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsInstance(result, dict)
        self.assertIn("scenario", result)

    def test_escape_returns_back(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(result, "back")

    def test_down_changes_selection(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        first = ui._scenarios[0]["_id"]
        ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertNotEqual(result["scenario"], first)

    def test_mouse_wheel_changes_selection(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        first = ui._scenarios[0]["_id"]
        ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(0, 0)))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertNotEqual(result["scenario"], first)

    def test_back_button_click_returns_back(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._back_rect.center))
        self.assertEqual(result, "back")

    def test_click_selected_row_confirms(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._row_rects[0].center))
        self.assertIsInstance(result, dict)

    def test_draw_does_not_crash(self) -> None:
        ui = ScenarioSelect(self.font, self.small_font)
        ui.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
