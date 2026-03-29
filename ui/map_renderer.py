"""Draws the battlefield hex grid and terrain.

Performance architecture
------------------------
Rendering is split into three layers, each cached in *world space* (no camera
offset so the surface can be blitted at ``(offset_x, offset_y)`` every frame):

1. **Terrain surface** — hex fills, outlines, texture details, roads/rivers.
   Cached per ``(zoom_rounded, detail_mode)``.  Rebuilt only when zoom changes.

2. **Fog surface** — HIDDEN/EXPLORED overlays, soft fog-edge tint, cloud blobs.
   Cached per ``(current_turn, zoom_rounded)``.  Rebuilt only at turn end.

3. **Highlight surface** — move/attack/range overlays.  Built fresh each frame
   but batched into a **single** SRCALPHA surface and blitted once.  Falls back
   to direct viewport-sized rendering when there are no highlights.

Viewport culling skips hexes whose world position falls outside the visible
screen area, so panning over a 50×40 map processes only the ~500 visible hexes.

World surface memory is capped at 64 MB; above that the renderer falls back to
direct per-frame drawing without a cache.
"""

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

# Maximum world surface area (pixels) before caching is skipped.
_MAX_WORLD_PIXELS = 16_000_000   # 64 MB at 32-bit colour


def _world_pos(coord: HexCoord, hex_size: float) -> tuple[float, float]:
    """Axial → world coordinates (no camera offset)."""
    x = hex_size * math.sqrt(3) * (coord.q + coord.r / 2)
    y = hex_size * 1.5 * coord.r
    return x, y


def _world_surface_size(game: GameState, hex_size: float) -> tuple[int, int] | None:
    """Compute world surface dimensions; return None if they exceed the cap."""
    w, h = game.battle_map.width, game.battle_map.height
    # Corner hexes that give maximum extent
    max_wx = hex_size * math.sqrt(3) * ((w - 1) + (h - 1) / 2) + hex_size * 2
    max_wy = hex_size * 1.5 * (h - 1) + hex_size * 2
    ww, wh = int(max_wx) + 4, int(max_wy) + 4
    if ww * wh > _MAX_WORLD_PIXELS:
        return None
    return ww, wh


class MapRenderer:

    def __init__(self) -> None:
        self._terrain_surf: pygame.Surface | None = None
        self._terrain_key: tuple = ()

        self._fog_surf: pygame.Surface | None = None
        self._fog_key: tuple = ()

    # ------------------------------------------------------------------
    # Public draw entry-point
    # ------------------------------------------------------------------

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
        attack_range_hexes: set[HexCoord] | None = None,
    ) -> None:
        move_targets = move_targets or set()
        attack_targets = attack_targets or set()
        attack_range_hexes = attack_range_hexes or set()

        sw, sh = surface.get_size()
        detail = camera.zoom >= 0.8
        hex_size = camera.hex_size
        zoom_key = round(hex_size, 1)

        surface.fill(themes.PARCHMENT)

        # --- Layer 1: terrain (cached world surface) ---
        t_key = (zoom_key, detail)
        if t_key != self._terrain_key:
            self._terrain_surf = _build_terrain_surface(game, hex_size, detail)
            self._terrain_key = t_key

        if self._terrain_surf is not None:
            surface.blit(self._terrain_surf, (int(camera.offset_x), int(camera.offset_y)))
        else:
            # Fallback: direct per-hex draw with viewport culling
            _draw_terrain_direct(surface, game, camera, sw, sh, detail)

        # --- Layer 2: fog / explored (cached world surface) ---
        f_key = (game.current_turn, zoom_key)
        if f_key != self._fog_key:
            self._fog_surf = _build_fog_surface(game, visibility, hex_size)
            self._fog_key = f_key

        if self._fog_surf is not None:
            surface.blit(self._fog_surf, (int(camera.offset_x), int(camera.offset_y)))
        else:
            # Fallback: direct fog draw
            _draw_fog_direct(surface, game, camera, visibility, sw, sh)

        # --- Layer 3: dynamic highlights (batched, per-frame) ---
        _draw_highlight_layer(
            surface, camera, sw, sh,
            move_targets, attack_targets, attack_range_hexes - attack_targets,
        )

        # --- Selection and hover borders (2 polygon draws max) ---
        if selected_hex is not None:
            _draw_hex_border(surface, selected_hex, camera, themes.SELECTION, 3)
        if hovered_hex is not None and hovered_hex != selected_hex:
            _draw_hex_border(surface, hovered_hex, camera, themes.HOVER, 2)

        # --- Objectives ---
        for objective in game.objectives:
            cx, cy = camera.axial_to_screen(objective.position)
            if -20 < cx < sw + 20 and -20 < cy < sh + 20:
                pygame.draw.circle(
                    surface, themes.SELECTION, (cx, cy),
                    max(6, int(hex_size * 0.18)), 2,
                )


# ------------------------------------------------------------------
# Surface builders
# ------------------------------------------------------------------

def _build_terrain_surface(
    game: GameState,
    hex_size: float,
    detail: bool,
) -> pygame.Surface | None:
    """Render terrain + roads + rivers to a world-space surface.

    Returns None if the surface would exceed the memory cap.
    """
    dims = _world_surface_size(game, hex_size)
    if dims is None:
        return None

    surf = pygame.Surface(dims)
    surf.fill(themes.PARCHMENT)

    for coord in game.battle_map.coords():
        wx, wy = _world_pos(coord, hex_size)
        center = (int(wx), int(wy))
        polygon = hex_polygon(center, hex_size)
        terrain = game.battle_map.terrain_at(coord)
        base_colour = TERRAIN_COLOURS[terrain]

        elev = game.battle_map.elevation_at(coord)
        shade = max(0.78, 1.0 - elev * 0.0025)
        shaded = (
            int(min(255, base_colour[0] * shade)),
            int(min(255, base_colour[1] * shade)),
            int(min(255, base_colour[2] * shade)),
        )

        pygame.draw.polygon(surf, shaded, polygon)
        pygame.draw.polygon(surf, (70, 60, 50), polygon, 1)

        if detail:
            _draw_terrain_detail(surf, coord, terrain, center, hex_size)

    # A5: road / river connectivity lines
    road_w = max(2, int(hex_size * 0.12))
    river_w = max(3, int(hex_size * 0.15))
    for coord in game.battle_map.coords():
        terrain = game.battle_map.terrain_at(coord)
        if terrain not in (TerrainType.ROAD, TerrainType.RIVER):
            continue
        cx, cy = _world_pos(coord, hex_size)
        for nb in coord.neighbors():
            if not game.battle_map.in_bounds(nb):
                continue
            if game.battle_map.terrain_at(nb) is not terrain:
                continue
            nx, ny = _world_pos(nb, hex_size)
            colour = (165, 138, 72) if terrain is TerrainType.ROAD else (55, 105, 165)
            width = road_w if terrain is TerrainType.ROAD else river_w
            pygame.draw.line(surf, colour, (int(cx), int(cy)), (int(nx), int(ny)), width)

    return surf


def _build_fog_surface(
    game: GameState,
    visibility: VisibilitySnapshot,
    hex_size: float,
) -> pygame.Surface | None:
    """Render fog/explored overlays and cloud blobs to a world-space SRCALPHA surface."""
    dims = _world_surface_size(game, hex_size)
    if dims is None:
        return None

    surf = pygame.Surface(dims, pygame.SRCALPHA)

    hidden_set: set[HexCoord] = set()
    for coord in game.battle_map.coords():
        if visibility.visibility_state(coord) is VisibilityState.HIDDEN:
            hidden_set.add(coord)

    for coord in game.battle_map.coords():
        state = visibility.visibility_state(coord)
        if state is VisibilityState.HIDDEN:
            wx, wy = _world_pos(coord, hex_size)
            polygon = hex_polygon((int(wx), int(wy)), hex_size)
            pygame.draw.polygon(surf, themes.HIDDEN_OVERLAY, polygon)
            _draw_fog_clouds_onto(surf, coord, (int(wx), int(wy)), hex_size)
        elif state is VisibilityState.EXPLORED:
            wx, wy = _world_pos(coord, hex_size)
            polygon = hex_polygon((int(wx), int(wy)), hex_size)
            pygame.draw.polygon(surf, themes.EXPLORED_OVERLAY, polygon)
            # B10: soft fog edge
            if any(nb in hidden_set for nb in coord.neighbors()):
                pygame.draw.polygon(surf, themes.FOG_EDGE_OVERLAY, polygon)

    return surf


# ------------------------------------------------------------------
# Fallback direct renderers (used when world surface exceeds memory cap)
# ------------------------------------------------------------------

def _draw_terrain_direct(
    surface: pygame.Surface,
    game: GameState,
    camera: Camera,
    sw: int,
    sh: int,
    detail: bool,
) -> None:
    margin = camera.hex_size * 2
    road_w = max(2, int(camera.hex_size * 0.12))
    river_w = max(3, int(camera.hex_size * 0.15))

    for coord in game.battle_map.coords():
        cx, cy = camera.axial_to_screen(coord)
        if cx < -margin or cx > sw + margin or cy < -margin or cy > sh + margin:
            continue
        polygon = hex_polygon((cx, cy), camera.hex_size)
        terrain = game.battle_map.terrain_at(coord)
        base_colour = TERRAIN_COLOURS[terrain]
        elev = game.battle_map.elevation_at(coord)
        shade = max(0.78, 1.0 - elev * 0.0025)
        shaded = (
            int(min(255, base_colour[0] * shade)),
            int(min(255, base_colour[1] * shade)),
            int(min(255, base_colour[2] * shade)),
        )
        pygame.draw.polygon(surface, shaded, polygon)
        pygame.draw.polygon(surface, (70, 60, 50), polygon, 1)
        if detail:
            _draw_terrain_detail(surface, coord, terrain, (cx, cy), camera.hex_size)

    for coord in game.battle_map.coords():
        terrain = game.battle_map.terrain_at(coord)
        if terrain not in (TerrainType.ROAD, TerrainType.RIVER):
            continue
        cx, cy = camera.axial_to_screen(coord)
        if cx < -margin or cx > sw + margin or cy < -margin or cy > sh + margin:
            continue
        for nb in coord.neighbors():
            if not game.battle_map.in_bounds(nb):
                continue
            if game.battle_map.terrain_at(nb) is not terrain:
                continue
            nx, ny = camera.axial_to_screen(nb)
            colour = (165, 138, 72) if terrain is TerrainType.ROAD else (55, 105, 165)
            width = road_w if terrain is TerrainType.ROAD else river_w
            pygame.draw.line(surface, colour, (cx, cy), (nx, ny), width)


def _draw_fog_direct(
    surface: pygame.Surface,
    game: GameState,
    camera: Camera,
    visibility: VisibilitySnapshot,
    sw: int,
    sh: int,
) -> None:
    margin = camera.hex_size * 2
    fog_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    hidden_set: set[HexCoord] = set()
    for coord in game.battle_map.coords():
        if visibility.visibility_state(coord) is VisibilityState.HIDDEN:
            hidden_set.add(coord)

    for coord in game.battle_map.coords():
        cx, cy = camera.axial_to_screen(coord)
        if cx < -margin or cx > sw + margin or cy < -margin or cy > sh + margin:
            continue
        state = visibility.visibility_state(coord)
        polygon = hex_polygon((cx, cy), camera.hex_size)
        if state is VisibilityState.HIDDEN:
            pygame.draw.polygon(fog_surf, themes.HIDDEN_OVERLAY, polygon)
            _draw_fog_clouds_onto(fog_surf, coord, (cx, cy), camera.hex_size)
        elif state is VisibilityState.EXPLORED:
            pygame.draw.polygon(fog_surf, themes.EXPLORED_OVERLAY, polygon)
            if any(nb in hidden_set for nb in coord.neighbors()):
                pygame.draw.polygon(fog_surf, themes.FOG_EDGE_OVERLAY, polygon)
    surface.blit(fog_surf, (0, 0))


# ------------------------------------------------------------------
# Dynamic highlight layer (per-frame, batched into one blit)
# ------------------------------------------------------------------

def _draw_highlight_layer(
    surface: pygame.Surface,
    camera: Camera,
    sw: int,
    sh: int,
    move_targets: set[HexCoord],
    attack_targets: set[HexCoord],
    attack_range_hexes: set[HexCoord],
) -> None:
    all_highlights = move_targets | attack_targets | attack_range_hexes
    if not all_highlights:
        return

    hl_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    margin = camera.hex_size * 2
    for coord in all_highlights:
        cx, cy = camera.axial_to_screen(coord)
        if cx < -margin or cx > sw + margin or cy < -margin or cy > sh + margin:
            continue
        polygon = hex_polygon((cx, cy), camera.hex_size)
        if coord in attack_targets:
            pygame.draw.polygon(hl_surf, themes.ATTACK_HIGHLIGHT, polygon)
        elif coord in move_targets:
            pygame.draw.polygon(hl_surf, themes.MOVE_HIGHLIGHT, polygon)
        else:
            pygame.draw.polygon(hl_surf, themes.ATTACK_RANGE_OVERLAY, polygon)
    surface.blit(hl_surf, (0, 0))


def _draw_hex_border(
    surface: pygame.Surface,
    coord: HexCoord,
    camera: Camera,
    colour: tuple,
    width: int,
) -> None:
    cx, cy = camera.axial_to_screen(coord)
    polygon = hex_polygon((cx, cy), camera.hex_size)
    pygame.draw.polygon(surface, colour, polygon, width)


# ------------------------------------------------------------------
# Per-hex drawing helpers
# ------------------------------------------------------------------

def _draw_fog_clouds_onto(
    surf: pygame.Surface,
    coord: HexCoord,
    center: tuple[int, int],
    hex_size: float,
) -> None:
    """Draw cloud blobs for one hidden hex onto *surf* (B10)."""
    cx, cy = center
    h = (coord.q * 73856093) ^ (coord.r * 19349663)
    r_blob = max(3, int(hex_size * 0.18))
    for i in range(3):
        angle = math.radians(((h >> (i * 8)) & 0xFF) * 360 / 255)
        dist = hex_size * 0.28 * (((h >> (i * 4 + 4)) & 0xF) / 15.0)
        bx = int(cx + dist * math.cos(angle))
        by = int(cy + dist * math.sin(angle))
        alpha = 60 + ((h >> (i * 3)) & 0x3F)
        pygame.draw.circle(surf, (18, 22, 30, alpha), (bx, by), r_blob)


def _draw_terrain_detail(
    surface: pygame.Surface,
    coord: HexCoord,
    terrain: TerrainType,
    center: tuple[int, int],
    hex_size: float,
) -> None:
    cx, cy = center
    s = hex_size

    if terrain is TerrainType.FOREST:
        offsets = ((-s * 0.2, -s * 0.1), (s * 0.15, -s * 0.15), (0.0, s * 0.15))
        r = max(2, int(s * 0.1))
        for dx, dy in offsets:
            pygame.draw.circle(surface, (35, 80, 35), (int(cx + dx), int(cy + dy)), r)

    elif terrain is TerrainType.HILL:
        arc_w = max(4, int(s * 0.5))
        arc_h = max(2, int(s * 0.25))
        for dy_off in (-int(s * 0.1), int(s * 0.1)):
            rect = pygame.Rect(cx - arc_w // 2, cy + dy_off - arc_h // 2, arc_w, arc_h)
            pygame.draw.arc(surface, (100, 78, 42), rect, 0, math.pi, max(1, int(s * 0.04)))

    elif terrain is TerrainType.MARSH:
        line_half = max(2, int(s * 0.25 / 2))
        for dy_off in (-int(s * 0.15), 0, int(s * 0.15)):
            pygame.draw.line(
                surface, (65, 95, 115),
                (cx - line_half, cy + dy_off),
                (cx + line_half, cy + dy_off),
                max(1, int(s * 0.04)),
            )

    elif terrain is TerrainType.VILLAGE:
        hw = max(4, int(s * 0.18))
        rect = pygame.Rect(cx - hw // 2, cy - hw // 2, hw, hw)
        pygame.draw.rect(surface, (130, 95, 65), rect)

    elif terrain is TerrainType.FORTIFICATION:
        d = max(5, int(s * 0.2))
        pts = [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)]
        pygame.draw.polygon(surface, (80, 65, 100), pts, max(1, int(s * 0.05)))


def hex_polygon(center: tuple[int, int], size: float) -> list[tuple[int, int]]:
    cx, cy = center
    return [
        (int(cx + size * math.cos(math.radians(60 * i - 30))),
         int(cy + size * math.sin(math.radians(60 * i - 30))))
        for i in range(6)
    ]

