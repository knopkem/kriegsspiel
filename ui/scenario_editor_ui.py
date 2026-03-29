"""Pygame scenario editor UI.

Launches a standalone map editor window.  Uses the headless
:class:`~core.scenario_editor.ScenarioEditor` as its data model.

Controls
--------
Left-click hex         Paint with selected terrain brush
Right-click hex        Context menu: place / remove unit or objective
Scroll wheel           Zoom in / out
Middle-drag / arrows   Pan camera
U                      Undo last action
S                      Save (validates first; shows error toast if invalid)
L                      Load existing scenario JSON
N                      New blank map (prompts for size via CLI)
Tab                    Cycle terrain brush
Escape / Q             Quit editor (warns if unsaved changes)
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Callable

import pygame

# project imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.map import HexCoord, TerrainType, TERRAIN_FROM_CHAR
from core.scenario_editor import EditorObjective, ScenarioEditor, CHAR_FROM_TERRAIN
from ui import themes
from ui.camera import Camera
from ui.bitmap_font import BitmapFont

# ---------------------------------------------------------------------------
# Terrain brush palette
# ---------------------------------------------------------------------------

TERRAIN_ORDER: list[TerrainType] = [
    TerrainType.OPEN,
    TerrainType.ROAD,
    TerrainType.FOREST,
    TerrainType.HILL,
    TerrainType.RIVER,
    TerrainType.VILLAGE,
    TerrainType.MARSH,
    TerrainType.FORTIFICATION,
]

TERRAIN_LABEL: dict[TerrainType, str] = {
    TerrainType.OPEN: "Open",
    TerrainType.ROAD: "Road",
    TerrainType.FOREST: "Forest",
    TerrainType.HILL: "Hill",
    TerrainType.RIVER: "River",
    TerrainType.VILLAGE: "Village",
    TerrainType.MARSH: "Marsh",
    TerrainType.FORTIFICATION: "Fort",
}

TERRAIN_COLOUR: dict[TerrainType, tuple[int, int, int]] = {
    TerrainType.OPEN: themes.OPEN,
    TerrainType.ROAD: themes.ROAD,
    TerrainType.FOREST: themes.FOREST,
    TerrainType.HILL: themes.HILL,
    TerrainType.RIVER: themes.RIVER,
    TerrainType.VILLAGE: themes.VILLAGE,
    TerrainType.MARSH: themes.MARSH,
    TerrainType.FORTIFICATION: (180, 180, 180),
}

# ---------------------------------------------------------------------------
# Unit template palette
# ---------------------------------------------------------------------------

UNIT_TEMPLATES: list[dict] = [
    {"type": "infantry",  "name": "Infantry Bn",   "side": "blue"},
    {"type": "cavalry",   "name": "Cavalry Sqn",   "side": "blue"},
    {"type": "artillery", "name": "Artillery Bty",  "side": "blue"},
    {"type": "skirmisher","name": "Skirmisher Det", "side": "blue"},
    {"type": "commander", "name": "Commander",      "side": "blue"},
    {"type": "infantry",  "name": "Infantry Bn",   "side": "red"},
    {"type": "cavalry",   "name": "Cavalry Sqn",   "side": "red"},
    {"type": "artillery", "name": "Artillery Bty",  "side": "red"},
]

_SIDE_COLOUR = {"blue": themes.BLUE_UNIT, "red": themes.RED_UNIT}


# ---------------------------------------------------------------------------
# Main editor class
# ---------------------------------------------------------------------------

class ScenarioEditorApp:
    """Pygame scenario editor application."""

    PANEL_W = 220      # right-side palette panel width
    TOPBAR_H = 32
    STATUS_H = 24
    DEFAULT_W, DEFAULT_H = 1280, 800

    def __init__(
        self,
        editor: ScenarioEditor | None = None,
        save_path: str | None = None,
    ) -> None:
        if not pygame.get_init():
            pygame.init()

        self.screen = pygame.display.set_mode(
            (self.DEFAULT_W, self.DEFAULT_H), pygame.RESIZABLE
        )
        pygame.display.set_caption("Kriegsspiel — Scenario Editor")
        self.clock = pygame.time.Clock()

        self.editor = editor or ScenarioEditor.blank(
            width=20, height=15, scenario_id="new_scenario", title="New Scenario"
        )
        self.save_path: str = save_path or "data/scenarios/new_scenario.json"
        self.camera = Camera(
            width=self.DEFAULT_W,
            height=self.DEFAULT_H,
            zoom=1.0,
            offset_x=float(self.PANEL_W // 2),
            offset_y=float(self.TOPBAR_H + 10),
        )
        self.font = BitmapFont(scale=2)
        self.small_font = BitmapFont(scale=1)

        self.brush_index: int = 0          # current terrain brush
        self.unit_template_index: int = 0  # selected unit template
        self.mode: str = "terrain"         # "terrain" | "unit" | "objective"
        self.is_painting: bool = False
        self.status_msg: str = "Ready — L to load, S to save, Tab to cycle brush"
        self.unsaved: bool = False
        self._next_unit_id: int = 1
        self._next_obj_id: int = 1
        self._pan_keys: dict[int, tuple[int, int]] = {
            pygame.K_LEFT:  (-10, 0),
            pygame.K_RIGHT: (10, 0),
            pygame.K_UP:    (0, -10),
            pygame.K_DOWN:  (0, 10),
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if not self._handle_key(event):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.is_painting = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.is_painting and self.mode == "terrain":
                        coord = self.camera.screen_to_axial(event.pos)
                        if self.editor.in_bounds(coord):
                            t = TERRAIN_ORDER[self.brush_index]
                            if self.editor.terrain_at(coord) != t:
                                self.editor.paint_terrain(coord, t)
                                self.unsaved = True
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    self.camera.zoom_at(1.15 if event.y > 0 else 1 / 1.15, (mx, my))

            # Continuous key pan
            keys = pygame.key.get_pressed()
            for key, delta in self._pan_keys.items():
                if keys[key]:
                    self.camera.offset_x -= delta[0]
                    self.camera.offset_y -= delta[1]

            self._draw()
            pygame.display.flip()

        pygame.quit()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_key(self, event: pygame.event.Event) -> bool:
        """Returns False to signal quit."""
        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            return False
        elif event.key == pygame.K_TAB:
            self.brush_index = (self.brush_index + 1) % len(TERRAIN_ORDER)
            self.mode = "terrain"
            brush = TERRAIN_LABEL[TERRAIN_ORDER[self.brush_index]]
            self.status_msg = f"Brush: {brush}"
        elif event.key == pygame.K_u:
            if self.editor.undo():
                self.unsaved = True
                self.status_msg = "Undo"
            else:
                self.status_msg = "Nothing to undo"
        elif event.key == pygame.K_s:
            self._do_save()
        elif event.key == pygame.K_t:
            self.mode = "terrain"
            self.status_msg = "Mode: Terrain"
        elif event.key == pygame.K_p:
            self.mode = "unit"
            self.status_msg = "Mode: Place Unit (click hex)"
        elif event.key == pygame.K_o:
            self.mode = "objective"
            self.status_msg = "Mode: Place Objective (click hex)"
        elif event.key == pygame.K_r:
            self.mode = "remove"
            self.status_msg = "Mode: Remove (click unit/objective hex)"
        elif event.key == pygame.K_1:
            self.unit_template_index = min(0, len(UNIT_TEMPLATES) - 1)
        elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
            self.unit_template_index = (self.unit_template_index - 1) % len(UNIT_TEMPLATES)
            self.status_msg = f"Unit: {UNIT_TEMPLATES[self.unit_template_index]['name']} ({UNIT_TEMPLATES[self.unit_template_index]['side']})"
        elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
            self.unit_template_index = (self.unit_template_index + 1) % len(UNIT_TEMPLATES)
            self.status_msg = f"Unit: {UNIT_TEMPLATES[self.unit_template_index]['name']} ({UNIT_TEMPLATES[self.unit_template_index]['side']})"
        return True

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        pos = event.pos
        # Ignore clicks in the palette panel
        w, h = self.screen.get_size()
        if pos[0] > w - self.PANEL_W:
            self._handle_palette_click(pos)
            return

        coord = self.camera.screen_to_axial(pos)
        if not self.editor.in_bounds(coord):
            return

        if event.button == 1:
            if self.mode == "terrain":
                self.is_painting = True
                self.editor.paint_terrain(coord, TERRAIN_ORDER[self.brush_index])
                self.unsaved = True
            elif self.mode == "unit":
                tmpl = UNIT_TEMPLATES[self.unit_template_index]
                uid = f"{tmpl['side'][0]}{tmpl['type'][0]}{self._next_unit_id}"
                self._next_unit_id += 1
                self.editor.place_unit({
                    "id": uid,
                    "name": tmpl["name"],
                    "side": tmpl["side"],
                    "type": tmpl["type"],
                    "position": [coord.q, coord.r],
                })
                self.unsaved = True
                self.status_msg = f"Placed {uid} at ({coord.q},{coord.r})"
            elif self.mode == "objective":
                oid = f"obj{self._next_obj_id}"
                self._next_obj_id += 1
                self.editor.place_objective(
                    EditorObjective(oid, f"Objective {self._next_obj_id-1}", coord.q, coord.r, points=3)
                )
                self.unsaved = True
                self.status_msg = f"Placed {oid} at ({coord.q},{coord.r})"
            elif self.mode == "remove":
                # Remove first unit, or objective at this hex
                units = self.editor.units_at(coord)
                if units:
                    self.editor.remove_unit(units[0]["id"])
                    self.unsaved = True
                    self.status_msg = f"Removed unit {units[0]['id']}"
                else:
                    objs = self.editor.objectives_at(coord)
                    if objs:
                        self.editor.remove_objective(objs[0].objective_id)
                        self.unsaved = True
                        self.status_msg = f"Removed {objs[0].objective_id}"

    def _handle_palette_click(self, pos: tuple[int, int]) -> None:
        """Handle clicks in the right palette panel."""
        w, _ = self.screen.get_size()
        panel_x = w - self.PANEL_W
        rel_x = pos[0] - panel_x
        rel_y = pos[1] - self.TOPBAR_H
        # Terrain tiles are 28px tall each
        row_h = 28
        for i, t in enumerate(TERRAIN_ORDER):
            tile_rect = pygame.Rect(4, i * row_h + 4, self.PANEL_W - 8, row_h - 2)
            if tile_rect.collidepoint(rel_x, rel_y):
                self.brush_index = i
                self.mode = "terrain"
                self.status_msg = f"Brush: {TERRAIN_LABEL[t]}"
                return
        # Unit templates below terrain tiles
        unit_start_y = len(TERRAIN_ORDER) * row_h + 20
        for i, tmpl in enumerate(UNIT_TEMPLATES):
            tile_rect = pygame.Rect(4, unit_start_y + i * row_h + 4, self.PANEL_W - 8, row_h - 2)
            if tile_rect.collidepoint(rel_x, rel_y):
                self.unit_template_index = i
                self.mode = "unit"
                self.status_msg = f"Mode: Place {tmpl['name']} ({tmpl['side']})"
                return

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _do_save(self) -> None:
        errors = self.editor.validate()
        if errors:
            self.status_msg = "Cannot save: " + errors[0]
            return
        try:
            self.editor.save(self.save_path)
            self.unsaved = False
            self.status_msg = f"Saved → {self.save_path}"
        except Exception as exc:
            self.status_msg = f"Save error: {exc}"

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        w, h = self.screen.get_size()
        self.screen.fill(themes.PANEL_BG)

        # Draw hex grid
        self._draw_map(w, h)
        self._draw_topbar(w)
        self._draw_palette(w, h)
        self._draw_status(w, h)

    def _draw_map(self, w: int, h: int) -> None:
        panel_x = w - self.PANEL_W
        for r in range(self.editor.height):
            for q in range(self.editor.width):
                coord = HexCoord(q, r)
                cx, cy = self.camera.axial_to_screen(coord)
                if cx < -60 or cx > panel_x + 60 or cy < self.TOPBAR_H - 60 or cy > h + 60:
                    continue
                terrain = self.editor.terrain[r][q]
                colour = TERRAIN_COLOUR[terrain]
                self._draw_hex(cx, cy, colour)

                # Units
                for u in self.editor.units_at(coord):
                    side_col = _SIDE_COLOUR.get(u["side"], themes.BLUE_UNIT)
                    self._draw_unit_pip(cx, cy, side_col)
                    break

                # Objectives
                for _ in self.editor.objectives_at(coord):
                    self._draw_objective_pip(cx, cy)
                    break

    def _hex_pts(self, cx: int, cy: int) -> list[tuple[float, float]]:
        s = self.camera.hex_size
        return [
            (cx + s * math.cos(math.radians(60 * i - 30)),
             cy + s * math.sin(math.radians(60 * i - 30)))
            for i in range(6)
        ]

    def _draw_hex(self, cx: int, cy: int, colour: tuple[int, int, int]) -> None:
        pts = self._hex_pts(cx, cy)
        pygame.draw.polygon(self.screen, colour, pts)
        pygame.draw.polygon(self.screen, (60, 55, 50), pts, 1)

    def _draw_unit_pip(self, cx: int, cy: int, colour: tuple[int, int, int]) -> None:
        r = max(3, int(self.camera.hex_size * 0.3))
        pygame.draw.circle(self.screen, colour, (cx, cy), r)
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), r, 1)

    def _draw_objective_pip(self, cx: int, cy: int) -> None:
        s = max(4, int(self.camera.hex_size * 0.25))
        pts = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
        pygame.draw.polygon(self.screen, (255, 220, 50), pts)
        pygame.draw.polygon(self.screen, (180, 140, 0), pts, 1)

    def _draw_topbar(self, w: int) -> None:
        pygame.draw.rect(self.screen, themes.PANEL_BG, pygame.Rect(0, 0, w, self.TOPBAR_H))
        mode_str = f"Mode: {self.mode.upper()}  |  Brush: {TERRAIN_LABEL[TERRAIN_ORDER[self.brush_index]]}  |  Units: {len(self.editor.units)}  |  Objs: {len(self.editor.objectives)}"
        txt = self.font.render(mode_str, True, themes.TEXT)
        self.screen.blit(txt, (8, 8))
        unsaved_txt = self.font.render("● unsaved" if self.unsaved else "✓ saved", True,
                                       (255, 100, 60) if self.unsaved else (100, 200, 100))
        self.screen.blit(unsaved_txt, (w - self.PANEL_W - 100, 8))

    def _draw_palette(self, w: int, h: int) -> None:
        panel_x = w - self.PANEL_W
        pygame.draw.rect(self.screen, themes.PANEL_BG, pygame.Rect(panel_x, self.TOPBAR_H, self.PANEL_W, h - self.TOPBAR_H))
        pygame.draw.line(self.screen, themes.PANEL_BORDER, (panel_x, self.TOPBAR_H), (panel_x, h), 1)

        y = self.TOPBAR_H + 8
        header = self.small_font.render("TERRAIN (Tab/click)", True, (160, 155, 150))
        self.screen.blit(header, (panel_x + 4, y))
        y += 14

        row_h = 28
        for i, t in enumerate(TERRAIN_ORDER):
            tile_rect = pygame.Rect(panel_x + 4, y + i * row_h + 2, self.PANEL_W - 8, row_h - 4)
            colour = TERRAIN_COLOUR[t]
            border = themes.SELECTION if i == self.brush_index and self.mode == "terrain" else (70, 65, 60)
            pygame.draw.rect(self.screen, colour, tile_rect, border_radius=3)
            pygame.draw.rect(self.screen, border, tile_rect, 2 if i == self.brush_index else 1, border_radius=3)
            lbl = self.small_font.render(TERRAIN_LABEL[t], True, (30, 20, 10))
            self.screen.blit(lbl, (tile_rect.x + 6, tile_rect.y + 7))

        y += len(TERRAIN_ORDER) * row_h + 14
        header2 = self.small_font.render("UNITS ([]/click)", True, (160, 155, 150))
        self.screen.blit(header2, (panel_x + 4, y))
        y += 14

        for i, tmpl in enumerate(UNIT_TEMPLATES):
            tile_rect = pygame.Rect(panel_x + 4, y + i * row_h + 2, self.PANEL_W - 8, row_h - 4)
            col = _SIDE_COLOUR.get(tmpl["side"], themes.BLUE_UNIT)
            border = themes.SELECTION if i == self.unit_template_index and self.mode == "unit" else (70, 65, 60)
            pygame.draw.rect(self.screen, col, tile_rect, border_radius=3)
            pygame.draw.rect(self.screen, border, tile_rect, 2 if (i == self.unit_template_index and self.mode == "unit") else 1, border_radius=3)
            lbl_text = f"{tmpl['type'][:4]} ({tmpl['side'][0].upper()})"
            lbl = self.small_font.render(lbl_text, True, (240, 240, 240))
            self.screen.blit(lbl, (tile_rect.x + 6, tile_rect.y + 7))

        # Hotkey reference at bottom of panel
        hint_y = h - self.STATUS_H - 100
        hints = ["T=Terrain  P=Place unit", "O=Objective  R=Remove", "U=Undo  S=Save  Q=Quit"]
        for hint in hints:
            surf = self.small_font.render(hint, True, (160, 155, 150))
            self.screen.blit(surf, (panel_x + 6, hint_y))
            hint_y += 14

    def _draw_status(self, w: int, h: int) -> None:
        bar_rect = pygame.Rect(0, h - self.STATUS_H, w - self.PANEL_W, self.STATUS_H)
        pygame.draw.rect(self.screen, themes.PANEL_BG, bar_rect)
        msg_surf = self.small_font.render(self.status_msg[:120], True, themes.TEXT)
        self.screen.blit(msg_surf, (8, h - self.STATUS_H + 5))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def launch_editor(
    load_path: str | None = None,
    save_path: str | None = None,
    width: int = 20,
    height: int = 15,
) -> None:
    """Launch the scenario editor, optionally loading an existing file."""
    if load_path:
        editor = ScenarioEditor.from_json(load_path)
        sp = save_path or load_path
    else:
        editor = ScenarioEditor.blank(
            width=width,
            height=height,
            scenario_id="new_scenario",
            title="New Scenario",
        )
        sp = save_path or "data/scenarios/new_scenario.json"

    app = ScenarioEditorApp(editor=editor, save_path=sp)
    app.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Kriegsspiel Scenario Editor")
    parser.add_argument("--load", help="Load existing scenario JSON")
    parser.add_argument("--save", help="Output path for saving")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=15)
    args = parser.parse_args()

    launch_editor(
        load_path=args.load,
        save_path=args.save,
        width=args.width,
        height=args.height,
    )
