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
        line_gap = 3
        pad_x, pad_y = 6, 5
        rendered = [self.font.render(line, True, themes.TEXT) for line in lines]
        line_h = rendered[0].get_height() if rendered else 7
        width = max(item.get_width() for item in rendered) + pad_x * 2
        height = len(rendered) * line_h + (len(rendered) - 1) * line_gap + pad_y * 2
        rect = pygame.Rect(pos[0] + 16, pos[1] + 16, width, height)
        pygame.draw.rect(surface, themes.PANEL_BG, rect, border_radius=4)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1, border_radius=4)
        y = rect.y + pad_y
        for item in rendered:
            surface.blit(item, (rect.x + pad_x, y))
            y += line_h + line_gap

