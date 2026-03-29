"""Simple minimap widget."""

from __future__ import annotations

import pygame

from core.game import GameState
from core.units import Side

from . import themes


class Minimap:
    def draw(self, surface: pygame.Surface, game: GameState, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)
        cell_w = rect.width / game.battle_map.width
        cell_h = rect.height / game.battle_map.height

        for unit in game.units.values():
            if unit.position is None or unit.is_removed:
                continue
            colour = themes.BLUE_UNIT if unit.side is Side.BLUE else themes.RED_UNIT
            marker = pygame.Rect(
                rect.x + int(unit.position.q * cell_w),
                rect.y + int(unit.position.r * cell_h),
                max(2, int(cell_w)),
                max(2, int(cell_h)),
            )
            pygame.draw.rect(surface, colour, marker)

    def click_to_coord(self, game: GameState, rect: pygame.Rect, pos: tuple[int, int]):
        if not rect.collidepoint(pos):
            return None
        x_ratio = (pos[0] - rect.x) / rect.width
        y_ratio = (pos[1] - rect.y) / rect.height
        return (
            min(game.battle_map.width - 1, max(0, int(x_ratio * game.battle_map.width))),
            min(game.battle_map.height - 1, max(0, int(y_ratio * game.battle_map.height))),
        )

