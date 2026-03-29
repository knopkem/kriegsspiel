"""Draws NATO-style wargame unit counters with status bars."""

from __future__ import annotations

import math

import pygame

from core.fog_of_war import VisibilitySnapshot
from core.game import GameState
from core.units import FacingDirection, MoraleState, Side, Unit, UnitType

from .bitmap_font import BitmapFont
from .camera import Camera
from . import themes


_FACING_ANGLES: dict[FacingDirection, float] = {
    FacingDirection.SE: math.radians(0),
    FacingDirection.S:  math.radians(60),
    FacingDirection.SW: math.radians(120),
    FacingDirection.NW: math.radians(180),
    FacingDirection.N:  math.radians(240),
    FacingDirection.NE: math.radians(300),
}


def _draw_infantry_symbol(surface, cx, cy, w, h):
    half_w = int(w * 0.3)
    half_h = int(h * 0.3)
    pygame.draw.line(surface, (255, 255, 255), (cx - half_w, cy - half_h), (cx + half_w, cy + half_h), 2)
    pygame.draw.line(surface, (255, 255, 255), (cx + half_w, cy - half_h), (cx - half_w, cy + half_h), 2)


def _draw_cavalry_symbol(surface, cx, cy, w, h):
    half_w = int(w * 0.3)
    half_h = int(h * 0.3)
    pygame.draw.line(surface, (255, 255, 255), (cx - half_w, cy + half_h), (cx + half_w, cy - half_h), 2)


def _draw_artillery_symbol(surface, cx, cy, w, h):
    r = max(3, int(h * 0.2))
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), r)


def _draw_skirmisher_symbol(surface, cx, cy, w, h):
    r = max(2, int(h * 0.08))
    spacing = max(4, int(w * 0.2))
    for i in range(3):
        x = cx - spacing + i * spacing
        pygame.draw.circle(surface, (255, 255, 255), (x, cy), r)


def _draw_commander_symbol(surface, cx, cy, w, h):
    r_out = max(5, int(min(w, h) * 0.3))
    r_in = max(2, r_out // 2)
    points = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        px = cx + int(r * math.cos(angle))
        py = cy + int(r * math.sin(angle))
        points.append((px, py))
    if len(points) >= 3:
        pygame.draw.polygon(surface, (255, 220, 80), points)


_SYMBOL_DRAWERS = {
    UnitType.INFANTRY: _draw_infantry_symbol,
    UnitType.CAVALRY: _draw_cavalry_symbol,
    UnitType.ARTILLERY: _draw_artillery_symbol,
    UnitType.SKIRMISHER: _draw_skirmisher_symbol,
    UnitType.COMMANDER: _draw_commander_symbol,
}

_MORALE_RATIOS = {
    MoraleState.STEADY: 1.0,
    MoraleState.SHAKEN: 0.67,
    MoraleState.ROUTING: 0.33,
    MoraleState.BROKEN: 0.1,
}

_MORALE_COLOURS = {
    MoraleState.STEADY: (50, 100, 200),
    MoraleState.SHAKEN: (200, 140, 40),
    MoraleState.ROUTING: (190, 50, 50),
    MoraleState.BROKEN: (190, 50, 50),
}


class UnitRenderer:
    def __init__(self, font: BitmapFont) -> None:
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
        animated_centers: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        animated_centers = animated_centers or {}
        for unit in game.units.values():
            if unit.position is None or unit.is_removed:
                continue
            if unit.side is player_side:
                self._draw_counter(
                    surface,
                    camera,
                    unit,
                    selected=(unit.id == selected_unit_id),
                    center_override=animated_centers.get(unit.id),
                )
            elif unit.id in visibility.visible_enemy_units:
                self._draw_counter(
                    surface,
                    camera,
                    unit,
                    selected=(unit.id == selected_unit_id),
                    center_override=animated_centers.get(unit.id),
                )

        for ghost in visibility.last_known_enemies.values():
            if ghost.unit_id in visibility.visible_enemy_units:
                continue
            self._draw_ghost(surface, camera, ghost)

    def _draw_counter(
        self,
        surface: pygame.Surface,
        camera: Camera,
        unit: Unit,
        *,
        selected: bool,
        center_override: tuple[int, int] | None = None,
    ) -> None:
        center = center_override if center_override is not None else camera.axial_to_screen(unit.position)
        hex_size = camera.hex_size

        if camera.zoom < 0.8:
            radius = max(4, int(hex_size * 0.3))
            colour = (40, 90, 160) if unit.side is Side.BLUE else (160, 45, 45)
            pygame.draw.circle(surface, colour, center, radius)
            if selected:
                pygame.draw.circle(surface, (255, 220, 50), center, radius + 2, 2)
            return

        width = max(44, int(hex_size * 1.6))
        height = max(30, int(hex_size * 1.1))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center

        side_colour = (40, 90, 160) if unit.side is Side.BLUE else (160, 45, 45)
        bg_colour = tuple(int(c * 0.5) for c in side_colour)

        if selected:
            sel_rect = rect.inflate(6, 6)
            pygame.draw.rect(surface, (255, 220, 50), sel_rect, 3, border_radius=4)

        pygame.draw.rect(surface, bg_colour, rect, border_radius=2)
        pygame.draw.rect(surface, side_colour, rect, 2, border_radius=2)

        symbol_h = int(height * 0.4)
        sym_cx = rect.centerx
        sym_cy = rect.y + symbol_h // 2
        drawer = _SYMBOL_DRAWERS.get(unit.unit_type)
        if drawer:
            drawer(surface, sym_cx, sym_cy, width, symbol_h)

        div_y = rect.y + symbol_h
        pygame.draw.line(surface, side_colour, (rect.x, div_y), (rect.right, div_y), 1)

        bar_x = rect.x + 3
        bar_w = rect.width - 6
        bar_h = 5

        hp_ratio = unit.hit_points / max(1, unit.max_hit_points)
        if hp_ratio > 0.6:
            hp_colour = (60, 180, 60)
        elif hp_ratio > 0.3:
            hp_colour = (220, 200, 40)
        else:
            hp_colour = (200, 50, 50)
        hp_y = div_y + 3
        pygame.draw.rect(surface, (30, 30, 30), (bar_x, hp_y, bar_w, bar_h))
        filled_hp = int(bar_w * max(0.0, min(1.0, hp_ratio)))
        if filled_hp > 0:
            pygame.draw.rect(surface, hp_colour, (bar_x, hp_y, filled_hp, bar_h))

        m_ratio = _MORALE_RATIOS.get(unit.morale_state, 0.5)
        m_colour = _MORALE_COLOURS.get(unit.morale_state, (100, 100, 100))
        mor_y = hp_y + bar_h + 2
        pygame.draw.rect(surface, (30, 30, 30), (bar_x, mor_y, bar_w, bar_h))
        filled_mor = int(bar_w * max(0.0, min(1.0, m_ratio)))
        if filled_mor > 0:
            pygame.draw.rect(surface, m_colour, (bar_x, mor_y, filled_mor, bar_h))

        # K7: facing chevron at zoom >= 1.0
        if camera.zoom >= 1.0:
            theta = _FACING_ANGLES.get(unit.facing, 0.0)
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            arm = 4
            tip_x = sym_cx + int(arm * cos_t)
            tip_y = sym_cy + int(arm * sin_t)
            lx = tip_x + int(arm * math.cos(theta + math.radians(150)))
            ly = tip_y + int(arm * math.sin(theta + math.radians(150)))
            rx = tip_x + int(arm * math.cos(theta - math.radians(150)))
            ry = tip_y + int(arm * math.sin(theta - math.radians(150)))
            pygame.draw.line(surface, (255, 255, 255), (tip_x, tip_y), (lx, ly), 2)
            pygame.draw.line(surface, (255, 255, 255), (tip_x, tip_y), (rx, ry), 2)

        # K8: entrenchment dashes below counter
        if unit.is_entrenched:
            dash_w = 6
            dash_h = 2
            dash_gap = 3
            total_dash_w = 3 * dash_w + 2 * dash_gap
            dash_x = rect.centerx - total_dash_w // 2
            dash_y = rect.bottom + 2
            for i in range(3):
                dx = dash_x + i * (dash_w + dash_gap)
                pygame.draw.rect(surface, (120, 80, 30), (dx, dash_y, dash_w, dash_h))

    def _draw_ghost(self, surface: pygame.Surface, camera: Camera, ghost) -> None:
        center = camera.axial_to_screen(ghost.position)
        hex_size = camera.hex_size

        if camera.zoom < 0.8:
            radius = max(4, int(hex_size * 0.3))
            pygame.draw.circle(surface, (130, 130, 130), center, radius)
            return

        width = max(44, int(hex_size * 1.6))
        height = max(30, int(hex_size * 1.1))
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center

        pygame.draw.rect(surface, (65, 65, 65), rect, border_radius=2)
        pygame.draw.rect(surface, (130, 130, 130), rect, 2, border_radius=2)
        label = self.font.render("?", True, (200, 200, 200))
        surface.blit(label, label.get_rect(center=rect.center))
        turn_text = self.font.render(f"T{ghost.seen_on_turn}", True, (160, 160, 160))
        surface.blit(turn_text, (rect.x + 2, rect.bottom - turn_text.get_height() - 1))
