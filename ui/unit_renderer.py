"""Draws unit counters and last-known ghost positions."""

from __future__ import annotations

import pygame

from core.fog_of_war import VisibilitySnapshot
from core.game import GameState
from core.units import Side, Unit, UnitType

from .camera import Camera
from . import themes


UNIT_ABBREVIATIONS = {
    UnitType.INFANTRY: "INF",
    UnitType.CAVALRY: "CAV",
    UnitType.ARTILLERY: "ART",
    UnitType.SKIRMISHER: "SKR",
    UnitType.COMMANDER: "HQ",
}


class UnitRenderer:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(
        self,
        surface: pygame.Surface,
        game: GameState,
        camera: Camera,
        player_side: Side,
        visibility: VisibilitySnapshot,
        *,
        selected_unit_id: str | None = None,
    ) -> None:
        for unit in game.units.values():
            if unit.position is None or unit.is_removed:
                continue
            if unit.side is player_side:
                self._draw_counter(surface, camera, unit, selected=(unit.id == selected_unit_id))
            elif unit.id in visibility.visible_enemy_units:
                self._draw_counter(surface, camera, unit, selected=(unit.id == selected_unit_id))

        for ghost in visibility.last_known_enemies.values():
            if ghost.unit_id in visibility.visible_enemy_units:
                continue
            center = camera.axial_to_screen(ghost.position)
            rect = pygame.Rect(0, 0, 28, 18)
            rect.center = center
            pygame.draw.rect(surface, themes.GHOST_UNIT, rect, border_radius=2)
            label = self.font.render("?", True, (20, 20, 20))
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_counter(self, surface: pygame.Surface, camera: Camera, unit: Unit, *, selected: bool) -> None:
        center = camera.axial_to_screen(unit.position)
        width = max(34, int(camera.hex_size * 1.2))
        height = max(20, int(camera.hex_size * 0.75))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        colour = themes.BLUE_UNIT if unit.side is Side.BLUE else themes.RED_UNIT
        pygame.draw.rect(surface, colour, rect, border_radius=3)
        border = themes.SELECTION if selected else (20, 20, 20)
        pygame.draw.rect(surface, border, rect, 2, border_radius=3)

        label = UNIT_ABBREVIATIONS[unit.unit_type]
        text = self.font.render(label, True, themes.TEXT)
        surface.blit(text, text.get_rect(center=rect.center))

