"""Draws the battlefield hex grid and terrain."""

from __future__ import annotations

import math

import pygame

from core.fog_of_war import VisibilitySnapshot, VisibilityState
from core.game import GameState
from core.map import HexCoord, TerrainType

from .camera import Camera
from . import themes


TERRAIN_COLOURS = {
    TerrainType.OPEN: themes.OPEN,
    TerrainType.ROAD: themes.ROAD,
    TerrainType.FOREST: themes.FOREST,
    TerrainType.HILL: themes.HILL,
    TerrainType.RIVER: themes.RIVER,
    TerrainType.VILLAGE: themes.VILLAGE,
    TerrainType.MARSH: themes.MARSH,
    TerrainType.FORTIFICATION: themes.FORT,
}


class MapRenderer:
    def draw(
        self,
        surface: pygame.Surface,
        game: GameState,
        camera: Camera,
        visibility: VisibilitySnapshot,
        *,
        hovered_hex: HexCoord | None = None,
        selected_hex: HexCoord | None = None,
        move_targets: set[HexCoord] | None = None,
        attack_targets: set[HexCoord] | None = None,
    ) -> None:
        move_targets = move_targets or set()
        attack_targets = attack_targets or set()
        surface.fill(themes.PARCHMENT)

        for coord in game.battle_map.coords():
            center = camera.axial_to_screen(coord)
            polygon = hex_polygon(center, camera.hex_size)
            terrain = game.battle_map.terrain_at(coord)
            base_colour = TERRAIN_COLOURS[terrain]
            pygame.draw.polygon(surface, base_colour, polygon)
            pygame.draw.polygon(surface, (70, 60, 50), polygon, 1)

            state = visibility.visibility_state(coord)
            if state is VisibilityState.HIDDEN:
                self._overlay(surface, polygon, themes.HIDDEN_OVERLAY)
            elif state is VisibilityState.EXPLORED:
                self._overlay(surface, polygon, themes.EXPLORED_OVERLAY)

            if coord in move_targets:
                self._overlay(surface, polygon, themes.MOVE_HIGHLIGHT)
            if coord in attack_targets:
                self._overlay(surface, polygon, themes.ATTACK_HIGHLIGHT)
            if coord == selected_hex:
                pygame.draw.polygon(surface, themes.SELECTION, polygon, 3)
            elif coord == hovered_hex:
                pygame.draw.polygon(surface, themes.HOVER, polygon, 2)

        for objective in game.objectives:
            center = camera.axial_to_screen(objective.position)
            pygame.draw.circle(surface, themes.SELECTION, center, max(6, int(camera.hex_size * 0.18)), 2)

    @staticmethod
    def _overlay(surface: pygame.Surface, polygon: list[tuple[int, int]], rgba: tuple[int, int, int, int]) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(overlay, rgba, polygon)
        surface.blit(overlay, (0, 0))


def hex_polygon(center: tuple[int, int], size: float) -> list[tuple[int, int]]:
    cx, cy = center
    points = []
    for index in range(6):
        angle = math.radians(60 * index - 30)
        points.append((int(cx + size * math.cos(angle)), int(cy + size * math.sin(angle))))
    return points

