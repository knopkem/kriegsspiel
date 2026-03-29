"""Main menu for Kriegsspiel."""

from __future__ import annotations

import pygame

from . import themes
from .bitmap_font import BitmapFont


ITEMS = [
    ("QUICK BATTLE", "quick_battle"),
    ("CAMPAIGN", "campaign"),
    ("SELECT SCENARIO", "scenario_select"),
    ("TUTORIAL", "tutorial"),
    ("SCENARIO EDITOR", "editor"),
    ("QUIT", "quit"),
]

_ITEM_W = 320
_ITEM_H = 34
_ITEM_SPACING = 10


class MainMenu:
    def __init__(self, font: BitmapFont, small_font: BitmapFont) -> None:
        self.font = font
        self.small_font = small_font
        self._large_font = BitmapFont(scale=4)
        self._selected = 0

    def handle_event(self, event) -> str | None:
        w, h = themes.WINDOW_SIZE
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected = (self._selected - 1) % len(ITEMS)
            elif event.key == pygame.K_DOWN:
                self._selected = (self._selected + 1) % len(ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return ITEMS[self._selected][1]
            elif event.key == pygame.K_ESCAPE:
                return "quit"
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self._item_rects(w, h)):
                if rect.collidepoint(event.pos):
                    self._selected = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._item_rects(w, h)):
                if rect.collidepoint(event.pos):
                    self._selected = i
                    return ITEMS[i][1]
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
        title_surf = self._large_font.render("KRIEGSSPIEL", True, themes.SELECTION)
        title_rect = title_surf.get_rect(centerx=w // 2, y=h // 4 - title_surf.get_height() // 2)
        surface.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self.small_font.render("THE PRUSSIAN WAR GAME", True, themes.MUTED_TEXT)
        sub_rect = sub_surf.get_rect(centerx=w // 2, y=title_rect.bottom + 10)
        surface.blit(sub_surf, sub_rect)

        # Menu items
        for i, (label, _action) in enumerate(ITEMS):
            rect = self._item_rects(w, h)[i]
            if i == self._selected:
                pygame.draw.rect(surface, (60, 80, 120), rect, border_radius=3)
                pygame.draw.rect(surface, themes.SELECTION, rect, 1, border_radius=3)
                color = themes.SELECTION
            else:
                pygame.draw.rect(surface, (42, 47, 60), rect, border_radius=3)
                color = themes.TEXT
            text_surf = self.font.render(label, True, color)
            surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _item_rects(self, w: int, h: int) -> list[pygame.Rect]:
        start_y = h // 2
        rects = []
        for i in range(len(ITEMS)):
            x = w // 2 - _ITEM_W // 2
            y = start_y + i * (_ITEM_H + _ITEM_SPACING)
            rects.append(pygame.Rect(x, y, _ITEM_W, _ITEM_H))
        return rects
