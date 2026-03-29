"""Headless tests for campaign overview UI."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.campaign import CampaignState, STANDARD_CAMPAIGN
from core.units import Side
from ui import themes
from ui.bitmap_font import BitmapFont
from ui.campaign_ui import CampaignUI


class CampaignUITest(unittest.TestCase):
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

    def test_current_scenario_property(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        self.assertEqual(ui.current_scenario, "tutorial")

    def test_current_difficulty_property(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        self.assertEqual(ui.current_difficulty, "easy")

    def test_escape_returns_back(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(result, "back")

    def test_enter_starts_battle_when_incomplete(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        result = ui.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(result, "start_battle")

    def test_start_button_click_returns_start_battle(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._start_rect.center))
        self.assertEqual(result, "start_battle")

    def test_back_button_click_returns_back(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        ui.draw(self.surface)
        result = ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._back_rect.center))
        self.assertEqual(result, "back")

    def test_complete_campaign_shows_reset_button(self) -> None:
        state = CampaignState(campaign=STANDARD_CAMPAIGN)
        for scenario in STANDARD_CAMPAIGN:
            state.record_result(scenario.scenario_id, winner=Side.BLUE, turns_taken=3, surviving_units=[])
        ui = CampaignUI(self.font, self.small_font, state)
        ui.draw(self.surface)
        self.assertTrue(ui.state.is_complete)
        self.assertGreater(ui._reset_rect.width, 0)

    def test_reset_button_creates_new_campaign(self) -> None:
        state = CampaignState(campaign=STANDARD_CAMPAIGN)
        for scenario in STANDARD_CAMPAIGN:
            state.record_result(scenario.scenario_id, winner=Side.BLUE, turns_taken=3, surviving_units=[])
        ui = CampaignUI(self.font, self.small_font, state)
        ui.draw(self.surface)
        ui.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ui._reset_rect.center))
        self.assertFalse(ui.state.is_complete)
        self.assertEqual(ui.state.current_scenario_index, 0)

    def test_draw_does_not_crash_incomplete(self) -> None:
        ui = CampaignUI(self.font, self.small_font, CampaignState(campaign=STANDARD_CAMPAIGN))
        ui.draw(self.surface)

    def test_draw_does_not_crash_complete(self) -> None:
        state = CampaignState(campaign=STANDARD_CAMPAIGN)
        for scenario in STANDARD_CAMPAIGN:
            state.record_result(scenario.scenario_id, winner=Side.BLUE, turns_taken=3, surviving_units=[])
        ui = CampaignUI(self.font, self.small_font, state)
        ui.draw(self.surface)


if __name__ == "__main__":
    unittest.main()
