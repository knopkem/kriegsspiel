"""Minimap widget showing terrain, units, fog, and camera position."""

from __future__ import annotations

import pygame

from core.fog_of_war import VisibilitySnapshot, VisibilityState
from core.game import GameState
from core.map import TerrainType
from core.units import Side

from .camera import Camera
from . import themes


_TERRAIN_MINI_COLOURS = {
    TerrainType.OPEN:          (200, 188, 155),
    TerrainType.ROAD:          (170, 143, 78),
    TerrainType.FOREST:        (45, 90, 42),
    TerrainType.HILL:          (120, 96, 58),
    TerrainType.RIVER:         (55, 105, 150),
    TerrainType.VILLAGE:       (155, 118, 88),
    TerrainType.MARSH:         (88, 112, 72),
    TerrainType.FORTIFICATION: (90, 80, 105),
}


class Minimap:
    def draw(
        self,
        surface: pygame.Surface,
        game: GameState,
        rect: pygame.Rect,
        camera: Camera | None = None,
        visibility: VisibilitySnapshot | None = None,
    ) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)

        w, h = game.battle_map.width, game.battle_map.height
        if w == 0 or h == 0:
            return
        cell_w = rect.width / w
        cell_h = rect.height / h

        for coord in game.battle_map.coords():
            terrain = game.battle_map.terrain_at(coord)
            colour = list(_TERRAIN_MINI_COLOURS.get(terrain, (180, 170, 145)))
            if visibility is not None:
                state = visibility.visibility_state(coord)
                if state is VisibilityState.HIDDEN:
                    colour = [int(c * 0.3) for c in colour]
                elif state is VisibilityState.EXPLORED:
                    colour = [int(c * 0.6) for c in colour]
            px = int(rect.x + coord.q * cell_w)
            py = int(rect.y + coord.r * cell_h)
            pw = max(1, int(cell_w))
            ph = max(1, int(cell_h))
            pygame.draw.rect(surface, colour, (px, py, pw, ph))

        for unit in game.units.values():
            if unit.position is None or unit.is_removed:
                continue
            ux = int(rect.x + unit.position.q * cell_w)
            uy = int(rect.y + unit.position.r * cell_h)
            dot_size = max(2, int(min(cell_w, cell_h) * 1.5))
            colour = themes.BLUE_UNIT if unit.side is Side.BLUE else themes.RED_UNIT
            pygame.draw.rect(surface, colour, (ux, uy, dot_size, dot_size))

        if camera is not None:
            sw, sh = surface.get_size()
            tl = camera.screen_to_axial((0, 0))
            br = camera.screen_to_axial((sw, sh))
            fx = int(rect.x + tl.q * cell_w)
            fy = int(rect.y + tl.r * cell_h)
            fw = int((br.q - tl.q) * cell_w)
            fh = int((br.r - tl.r) * cell_h)
            frustum_rect = pygame.Rect(fx, fy, fw, fh)
            pygame.draw.rect(surface, (255, 255, 255), frustum_rect, 1)

    def click_to_coord(self, game: GameState, rect: pygame.Rect, pos: tuple[int, int]):
        if not rect.collidepoint(pos):
            return None
        rel_x = pos[0] - rect.x
        rel_y = pos[1] - rect.y
        q = int(rel_x / rect.width * game.battle_map.width)
        r = int(rel_y / rect.height * game.battle_map.height)
        return (q, r)

