"""Hover tooltip rendering."""

from __future__ import annotations

import pygame

from . import themes


class Tooltip:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(self, surface: pygame.Surface, pos: tuple[int, int], lines: list[str]) -> None:
        if not lines:
            return
        rendered = [self.font.render(line, True, themes.TEXT) for line in lines]
        width = max(item.get_width() for item in rendered) + 10
        height = sum(item.get_height() for item in rendered) + 8
        rect = pygame.Rect(pos[0] + 16, pos[1] + 16, width, height)
        pygame.draw.rect(surface, themes.PANEL_BG, rect, border_radius=4)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1, border_radius=4)
        y = rect.y + 4
        for item in rendered:
            surface.blit(item, (rect.x + 5, y))
            y += item.get_height()

