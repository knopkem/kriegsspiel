"""Scrollable, colour-coded combat event log."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from core.game import GameEvent
from core.map import HexCoord
from . import themes


_CATEGORY_COLOURS = {
    "combat":    (220, 90,  90),
    "movement":  (100, 160, 220),
    "morale":    (200, 160, 40),
    "formation": (140, 200, 140),
    "rally":     (120, 200, 180),
    "hold":      (160, 140, 200),
    "command":   (220, 180, 80),
}

_FILTERS = ("all", "combat", "movement", "morale", "orders")

# Categories that map to the "orders" filter
_ORDER_CATEGORIES = {"formation", "rally", "hold", "command"}


@dataclass
class CombatLog:
    scroll_offset: int = 0
    max_visible: int = 6
    _filter: str = field(default="all", init=False, repr=False)
    # Each entry: (rect, coord_or_None) for the last drawn frame
    _entry_rects: list[tuple[pygame.Rect, HexCoord | None]] = field(
        default_factory=list, init=False, repr=False
    )
    _filter_rects: list[tuple[pygame.Rect, str]] = field(default_factory=list, init=False, repr=False)

    def scroll(self, delta: int) -> None:
        self.scroll_offset = max(0, self.scroll_offset + delta)

    def cycle_filter(self) -> None:
        idx = _FILTERS.index(self._filter)
        self._filter = _FILTERS[(idx + 1) % len(_FILTERS)]
        self.scroll_offset = 0

    def _matches_filter(self, event: GameEvent) -> bool:
        if self._filter == "all":
            return True
        if self._filter == "orders":
            return event.category in _ORDER_CATEGORIES
        return event.category == self._filter

    def coord_for_click(self, pos: tuple[int, int]) -> HexCoord | None:
        """Return the coord of the log entry under pos, if any."""
        for rect, coord in self._entry_rects:
            if rect.collidepoint(pos):
                return coord
        return None

    def click_filter(self, pos: tuple[int, int]) -> bool:
        for rect, name in self._filter_rects:
            if rect.collidepoint(pos):
                self._filter = name
                self.scroll_offset = 0
                return True
        return False

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        event_log: list[GameEvent],
        font,
    ) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)

        filter_label = self._filter.upper()
        title = font.render(f"Event Log [{filter_label}]", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 5))

        self._filter_rects = []
        fx = rect.x + 138
        fy = rect.y + 4
        for name in _FILTERS:
            label = name.upper()
            pill_w = max(42, len(label) * 6 + 12)
            pill = pygame.Rect(fx, fy, pill_w, 16)
            active = name == self._filter
            pygame.draw.rect(
                surface,
                (60, 80, 120) if active else (46, 52, 66),
                pill,
                border_radius=4,
            )
            pygame.draw.rect(surface, themes.PANEL_BORDER, pill, 1, border_radius=4)
            txt = font.render(label, True, themes.SELECTION if active else themes.MUTED_TEXT)
            surface.blit(txt, txt.get_rect(center=pill.center))
            self._filter_rects.append((pill, name))
            fx += pill_w + 6

        filtered = [e for e in event_log if self._matches_filter(e)]
        total = len(filtered)
        self.scroll_offset = min(self.scroll_offset, max(0, total - self.max_visible))
        start = max(0, total - self.max_visible - self.scroll_offset)
        visible_events = filtered[start: start + self.max_visible]

        line_h = 18
        y = rect.y + 24
        self._entry_rects = []
        for event in visible_events:
            colour = _CATEGORY_COLOURS.get(event.category, themes.TEXT)
            msg = f"T{event.turn}: {event.message}"
            if len(msg) > 85:
                msg = msg[:82] + "..."
            text = font.render(msg, True, colour)
            surface.blit(text, (rect.x + 6, y))
            entry_rect = pygame.Rect(rect.x, y, rect.width, line_h)
            coord = getattr(event, "coord", None)
            self._entry_rects.append((entry_rect, coord))
            if coord is not None:
                pygame.draw.line(
                    surface, themes.MUTED_TEXT,
                    (rect.x + 6, y + line_h - 2),
                    (rect.x + 6 + min(len(msg) * 6, rect.width - 12), y + line_h - 2),
                    1,
                )
            y += line_h

        if total > self.max_visible:
            hint = font.render(f"^ scroll ({self.scroll_offset})", True, themes.MUTED_TEXT)
            surface.blit(hint, (rect.right - 80, rect.y + 5))

        tab_hint = font.render("Tab:filter", True, themes.MUTED_TEXT)
        surface.blit(tab_hint, (rect.x + 8, rect.bottom - 12))
