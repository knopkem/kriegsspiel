"""Combat and event log rendering."""

from __future__ import annotations

import pygame

from . import themes


class CombatLogPanel:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = small_font

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, events) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)
        title = self.font.render("Event Log", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 8))
        y = rect.y + 32
        for event in events[-5:]:
            text = self.small_font.render(event.message[:80], True, themes.TEXT)
            surface.blit(text, (rect.x + 8, y))
            y += 18

