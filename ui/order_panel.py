"""Queued-order panel rendering."""

from __future__ import annotations

import pygame

from core.orders import OrderStatus
from core.units import Side

from . import themes


class OrderPanel:
    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = small_font

    def draw(self, surface: pygame.Surface, rect: pygame.Rect, game, player_side: Side) -> pygame.Rect:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)
        title = self.font.render("Orders", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 8))

        queued = [
            order
            for order in game.order_book.all_orders()
            if order.status is OrderStatus.QUEUED and game.units[order.unit_id].side is player_side
        ]
        y = rect.y + 34
        for order in queued[:10]:
            text = self.small_font.render(
                f"{order.unit_id}: {order.order_type.value}",
                True,
                themes.TEXT,
            )
            surface.blit(text, (rect.x + 8, y))
            y += 18

        button = pygame.Rect(rect.x + 8, rect.bottom - 38, rect.width - 16, 28)
        pygame.draw.rect(surface, themes.BLUE_UNIT, button, border_radius=4)
        label = self.font.render("End Turn", True, themes.TEXT)
        surface.blit(label, label.get_rect(center=button.center))
        return button

