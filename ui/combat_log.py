"""Scrollable, colour-coded combat event log."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from core.game import GameEvent
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


@dataclass
class CombatLog:
    scroll_offset: int = 0
    max_visible: int = 6

    def scroll(self, delta: int) -> None:
        self.scroll_offset = max(0, self.scroll_offset + delta)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        event_log: list[GameEvent],
        font,
    ) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)

        title = font.render("Event Log", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 5))

        total = len(event_log)
        self.scroll_offset = min(self.scroll_offset, max(0, total - self.max_visible))
        start = max(0, total - self.max_visible - self.scroll_offset)
        visible_events = event_log[start: start + self.max_visible]

        line_h = 18
        y = rect.y + 24
        for event in visible_events:
            colour = _CATEGORY_COLOURS.get(event.category, themes.TEXT)
            msg = f"T{event.turn}: {event.message}"
            if len(msg) > 85:
                msg = msg[:82] + "..."
            text = font.render(msg, True, colour)
            surface.blit(text, (rect.x + 6, y))
            y += line_h

        if total > self.max_visible:
            hint = font.render(f"^ scroll ({self.scroll_offset})", True, themes.MUTED_TEXT)
            surface.blit(hint, (rect.right - 80, rect.y + 5))

