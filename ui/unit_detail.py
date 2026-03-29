"""Selected-unit detail panel."""

from __future__ import annotations

import pygame

from . import themes


class UnitDetailPanel:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = small_font

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, unit) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)
        title = self.font.render("Selected Unit", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 8))

        if unit is None:
            text = self.small_font.render("No unit selected", True, themes.MUTED_TEXT)
            surface.blit(text, (rect.x + 8, rect.y + 36))
            return

        lines = [
            unit.name,
            f"Type: {unit.unit_type.value}",
            f"HP: {unit.hit_points}/{unit.max_hit_points}",
            f"Morale: {unit.morale_state.value}",
            f"Fatigue: {unit.fatigue}",
            f"Formation: {unit.formation.value}",
            f"Pos: {unit.position.q}, {unit.position.r}",
        ]
        y = rect.y + 36
        for line in lines:
            text = self.small_font.render(line, True, themes.TEXT)
            surface.blit(text, (rect.x + 8, y))
            y += 18

