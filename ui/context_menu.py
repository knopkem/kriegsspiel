"""Simple dropdown context menu for order entry."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from . import themes


@dataclass
class ContextMenu:
    """A small popup menu that shows order choices."""
    items: list[str] = field(default_factory=list)
    position: tuple[int, int] = (0, 0)
    visible: bool = False
    _hovered_index: int = -1

    ITEM_HEIGHT: int = 22
    MIN_WIDTH: int = 140
    PADDING: int = 6

    def show(self, position: tuple[int, int], items: list[str]) -> None:
        self.position = position
        self.items = items
        self.visible = True
        self._hovered_index = -1

    def hide(self) -> None:
        self.visible = False
        self.items = []

    def rect(self) -> pygame.Rect:
        w = self.MIN_WIDTH
        h = len(self.items) * self.ITEM_HEIGHT + self.PADDING * 2
        return pygame.Rect(self.position[0], self.position[1], w, h)

    def update_hover(self, mouse_pos: tuple[int, int]) -> None:
        if not self.visible:
            return
        r = self.rect()
        if not r.collidepoint(mouse_pos):
            self._hovered_index = -1
            return
        rel_y = mouse_pos[1] - r.y - self.PADDING
        self._hovered_index = rel_y // self.ITEM_HEIGHT

    def click(self, mouse_pos: tuple[int, int]) -> str | None:
        """Returns the selected item label, or None if click was outside."""
        if not self.visible:
            return None
        r = self.rect()
        if not r.collidepoint(mouse_pos):
            self.hide()
            return None
        rel_y = mouse_pos[1] - r.y - self.PADDING
        idx = rel_y // self.ITEM_HEIGHT
        if 0 <= idx < len(self.items):
            selected = self.items[idx]
            self.hide()
            return selected
        self.hide()
        return None

    def draw(self, surface: pygame.Surface, font) -> None:
        if not self.visible:
            return
        r = self.rect()
        shadow = r.move(2, 2)
        shadow_surf = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 80))
        surface.blit(shadow_surf, shadow.topleft)
        pygame.draw.rect(surface, themes.PANEL_BG, r, border_radius=3)
        pygame.draw.rect(surface, themes.PANEL_BORDER, r, 1, border_radius=3)
        for i, item in enumerate(self.items):
            item_rect = pygame.Rect(
                r.x + 1,
                r.y + self.PADDING + i * self.ITEM_HEIGHT,
                r.width - 2,
                self.ITEM_HEIGHT,
            )
            if i == self._hovered_index:
                pygame.draw.rect(surface, (60, 80, 120), item_rect, border_radius=2)
            text = font.render(item, True, themes.TEXT)
            surface.blit(text, (item_rect.x + 4, item_rect.y + 3))
