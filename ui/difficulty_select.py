"""Difficulty selection screen for Kriegsspiel."""

from __future__ import annotations

import pygame

from . import themes
from .bitmap_font import BitmapFont


DIFFICULTIES = [
    ("EASY",       "easy",       "Reactive AI, no planning"),
    ("MEDIUM",     "medium",     "Threat-aware, coordinated fire"),
    ("HARD",       "hard",       "Strategic planner, terrain expert"),
    ("HISTORICAL", "historical", "Full simulation, unforgiving"),
]

_ITEM_W = 400
_ITEM_H = 48
_ITEM_SPACING = 10


class DifficultySelect:
    def __init__(self, font: BitmapFont, small_font: BitmapFont) -> None:
        self.font = font
        self.small_font = small_font
        self._large_font = BitmapFont(scale=3)
        self._selected = 1  # default to medium

    def handle_event(self, event) -> str | None:
        """Returns difficulty string or None. 'cancel' if Escape pressed."""
        w, h = themes.WINDOW_SIZE
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = (self._selected - 1) % len(DIFFICULTIES)
            elif event.key == pygame.K_DOWN:
                self._selected = (self._selected + 1) % len(DIFFICULTIES)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return DIFFICULTIES[self._selected][1]
            elif event.key == pygame.K_ESCAPE:
                return "cancel"
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._item_rects(w, h)):
                if rect.collidepoint(event.pos):
                    self._selected = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._item_rects(w, h)):
                if rect.collidepoint(event.pos):
                    self._selected = i
                    return DIFFICULTIES[i][1]
        return None

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        surface.fill(themes.PANEL_BG)

        # Diagonal lines overlay
        line_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        line_color = (45, 50, 65, 35)
        step = 18
        for offset in range(-h, w + h, step):
            pygame.draw.line(line_surf, line_color, (offset, 0), (offset + h, h))
        surface.blit(line_surf, (0, 0))

        # Title
        title_surf = self._large_font.render("SELECT DIFFICULTY", True, themes.SELECTION)
        title_rect = title_surf.get_rect(centerx=w // 2, y=h // 4 - title_surf.get_height() // 2)
        surface.blit(title_surf, title_rect)

        # Items
        for i, (label, _key, desc) in enumerate(DIFFICULTIES):
            rect = self._item_rects(w, h)[i]
            if i == self._selected:
                pygame.draw.rect(surface, (60, 80, 120), rect, border_radius=3)
                pygame.draw.rect(surface, themes.SELECTION, rect, 1, border_radius=3)
                name_color = themes.SELECTION
            else:
                pygame.draw.rect(surface, (42, 47, 60), rect, border_radius=3)
                name_color = themes.TEXT

            name_surf = self.font.render(label, True, name_color)
            name_rect = name_surf.get_rect(centerx=rect.centerx, y=rect.y + 6)
            surface.blit(name_surf, name_rect)

            desc_surf = self.small_font.render(desc, True, themes.MUTED_TEXT)
            desc_rect = desc_surf.get_rect(centerx=rect.centerx, y=rect.y + 28)
            surface.blit(desc_surf, desc_rect)

    def _item_rects(self, w: int, h: int) -> list[pygame.Rect]:
        total = len(DIFFICULTIES) * _ITEM_H + (len(DIFFICULTIES) - 1) * _ITEM_SPACING
        start_y = h // 2 - total // 2
        rects = []
        for i in range(len(DIFFICULTIES)):
            x = w // 2 - _ITEM_W // 2
            y = start_y + i * (_ITEM_H + _ITEM_SPACING)
            rects.append(pygame.Rect(x, y, _ITEM_W, _ITEM_H))
        return rects
