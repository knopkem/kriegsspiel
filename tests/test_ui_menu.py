"""Headless tests for main menu and difficulty picker widgets."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ui import themes
from ui.bitmap_font import BitmapFont
from ui.difficulty_select import DifficultySelect
from ui.main_menu import MainMenu


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


class MainMenuTest(_PygameTestCase):
    def test_enter_activates_default_quick_battle(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "quick_battle")

    def test_up_wraps_to_last_item(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "quit")

    def test_down_selects_campaign(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "campaign")

    def test_escape_requests_quit(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(result, "quit")

    def test_mouse_motion_changes_selection(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        rect = menu._item_rects(*themes.WINDOW_SIZE)[2]
        menu.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center))
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "scenario_select")

    def test_mouse_click_returns_clicked_action(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        rect = menu._item_rects(*themes.WINDOW_SIZE)[3]
        result = menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(result, "tutorial")

    def test_space_activates_selected_item(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        result = menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(result, "campaign")

    def test_draw_does_not_crash(self) -> None:
        menu = MainMenu(self.font, self.small_font)
        menu.draw(self.surface)


class DifficultySelectTest(_PygameTestCase):
    def test_enter_returns_medium_by_default(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "medium")

    def test_up_selects_easy(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "easy")

    def test_down_selects_hard_after_two_steps(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "historical")

    def test_escape_returns_cancel(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(result, "cancel")

    def test_mouse_click_selects_easy(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        rect = picker._item_rects(*themes.WINDOW_SIZE)[0]
        result = picker.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(result, "easy")

    def test_mouse_motion_highlights_item(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        rect = picker._item_rects(*themes.WINDOW_SIZE)[3]
        picker.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center))
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "historical")

    def test_space_activates_selection(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        result = picker.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(result, "hard")

    def test_draw_does_not_crash(self) -> None:
        picker = DifficultySelect(self.font, self.small_font)
        picker.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
