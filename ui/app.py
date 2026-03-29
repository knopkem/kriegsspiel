"""Playable pygame prototype front end."""

from __future__ import annotations

import pygame

from ai.opponent import SimpleAICommander
from core.fog_of_war import VisibilitySnapshot
from core.game import GameState
from core.map import HexCoord
from core.orders import OrderStatus
from core.scenario import load_builtin_scenario
from core.tutorial import TutorialDirector
from core.units import Side, UnitType

from . import themes
from .audio import AudioEngine
from .bitmap_font import BitmapFont
from .camera import Camera
from .context_menu import ContextMenu
from .hud import HUD
from .input_handler import cycle_formation
from .map_renderer import MapRenderer
from .toast import ToastManager
from .tooltip import Tooltip
from .unit_renderer import UnitRenderer


class KriegsspielApp:
    def __init__(self, *, scenario_name: str = "skirmish_small", seed: int = 1) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(themes.WINDOW_SIZE)
        pygame.display.set_caption("Kriegsspiel Prototype")
        self.clock = pygame.time.Clock()

        self.font = BitmapFont(scale=2)
        self.small_font = BitmapFont(scale=1)

        self.scenario = load_builtin_scenario(scenario_name)
        self.game = GameState.from_scenario(self.scenario, rng_seed=seed)
        self.player_side = Side.BLUE
        self.ai = SimpleAICommander(Side.RED, seed=seed + 100)
        self.tutorial = TutorialDirector() if scenario_name == "tutorial" else None

        self.camera = Camera(*themes.WINDOW_SIZE, zoom=1.0, offset_x=200, offset_y=80)
        self.map_renderer = MapRenderer()
        self.unit_renderer = UnitRenderer(self.small_font)
        self.hud = HUD(self.font, self.small_font)
        self.tooltip = Tooltip(self.small_font)

        self.selected_unit_id: str | None = None
        self.hover_hex: HexCoord | None = None
        self.dragging = False
        self.last_mouse = (0, 0)
        self.end_turn_button = pygame.Rect(0, 0, 0, 0)

        # B3: movement path preview
        self.pending_move_dest: HexCoord | None = None
        self.move_path: list[HexCoord] = []

        # B5: context menu
        self.context_menu = ContextMenu()
        self._context_target_coord: HexCoord | None = None

        # B11: pause menu
        self.paused: bool = False
        self.quit_requested: bool = False

        # B12: end-game summary
        self.game_over: bool = False
        self.victory_report = None

        # B13: toasts
        self.toasts = ToastManager()

        # B14: help overlay
        self.show_help: bool = False

        # F5: audio engine (gracefully no-ops if mixer unavailable)
        self.audio = AudioEngine()

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_hex = self.camera.screen_to_axial(event.pos)
                    self.context_menu.update_hover(event.pos)
                    if self.dragging:
                        dx = event.pos[0] - self.last_mouse[0]
                        dy = event.pos[1] - self.last_mouse[1]
                        self.camera.pan(dx, dy)
                    self.last_mouse = event.pos
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.last_mouse = event.pos
                    if event.button == 2:
                        self.dragging = True
                    elif event.button == 1:
                        self._handle_left_click(event.pos)
                    elif event.button == 3:
                        self._handle_right_click(event.pos)
                    elif event.button == 4:
                        log_rect = pygame.Rect(
                            180, self.screen.get_height() - 150,
                            self.screen.get_width() - 190, 140,
                        )
                        if log_rect.collidepoint(event.pos):
                            self.hud.combat_log.scroll(1)
                        else:
                            self.camera.zoom_at(1.1, event.pos)
                    elif event.button == 5:
                        log_rect = pygame.Rect(
                            180, self.screen.get_height() - 150,
                            self.screen.get_width() - 190, 140,
                        )
                        if log_rect.collidepoint(event.pos):
                            self.hud.combat_log.scroll(-1)
                        else:
                            self.camera.zoom_at(0.9, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                    self.dragging = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = not self.paused
                    elif self.paused:
                        if event.key == pygame.K_q:
                            self.quit_requested = True
                    else:
                        self._handle_keydown(event.key)

            if self.quit_requested:
                running = False

            self._draw()
            pygame.display.flip()
            self.clock.tick(themes.FPS)

        pygame.quit()

    def _handle_left_click(self, pos: tuple[int, int]) -> None:
        if self.context_menu.visible:
            selected = self.context_menu.click(pos)
            if selected is not None:
                self._execute_context_action(selected, pos)
                return

        minimap_rect = pygame.Rect(10, self.screen.get_height() - 140, 160, 110)
        mini_coord = self.hud.minimap.click_to_coord(self.game, minimap_rect, pos)
        if mini_coord is not None:
            screen_pos = self.camera.axial_to_screen(HexCoord(*mini_coord))
            self.camera.pan(
                (self.screen.get_width() // 2) - screen_pos[0],
                (self.screen.get_height() // 2) - screen_pos[1],
            )
            return

        if self.end_turn_button.collidepoint(pos):
            self._end_turn()
            return

        coord = self.camera.screen_to_axial(pos)
        if not self.game.battle_map.in_bounds(coord):
            self.selected_unit_id = None
            return
        unit = self._top_player_unit_at(coord)
        self.selected_unit_id = unit.id if unit else None
        if unit:
            self.audio.play("unit_select")

    def _handle_right_click(self, pos: tuple[int, int]) -> None:
        selected = self.context_menu.click(pos)
        if selected is not None:
            self._execute_context_action(selected, pos)
            return

        if self.selected_unit_id is None:
            return
        unit = self.game.units[self.selected_unit_id]
        if unit.side is not self.player_side or unit.is_removed:
            return

        coord = self.camera.screen_to_axial(pos)
        if not self.game.battle_map.in_bounds(coord):
            return

        enemy = self._top_enemy_unit_at(coord)
        if enemy is not None:
            self.context_menu.show(pos, ["Attack", "Cancel"])
            self._context_target_coord = coord
        else:
            self.context_menu.show(pos, ["Move Here", "Hold", "Rally", "Formation", "Cancel"])
            self._context_target_coord = coord

    def _execute_context_action(self, action: str, pos: tuple[int, int]) -> None:
        if action == "Cancel" or self.selected_unit_id is None:
            return
        unit = self.game.units[self.selected_unit_id]
        coord = self._context_target_coord
        if action == "Move Here" and coord:
            self.game.order_book.issue_move(unit.id, coord, current_turn=self.game.current_turn)
            self.move_path = (
                self.game.battle_map.find_path(unit.position, coord, terrain_costs=unit.movement_costs()) or []
            )
            self.audio.play("order_given")
        elif action == "Attack" and coord:
            enemy = self._top_enemy_unit_at(coord)
            if enemy:
                self.game.order_book.issue_attack(unit.id, enemy.id, current_turn=self.game.current_turn)
                self.audio.play("order_given")
        elif action == "Hold":
            self.game.order_book.issue_hold(unit.id, current_turn=self.game.current_turn)
        elif action == "Rally":
            self.game.order_book.issue_rally(unit.id, current_turn=self.game.current_turn)
        elif action == "Formation":
            self.game.order_book.issue_change_formation(
                unit.id, cycle_formation(unit), current_turn=self.game.current_turn
            )

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_F1 or key == pygame.K_SLASH:
            self.show_help = not self.show_help
            return

        if self.game_over:
            if key == pygame.K_r:
                self._restart()
            elif key == pygame.K_q:
                self.quit_requested = True
            return

        if key == pygame.K_RETURN:
            self._end_turn()
            return
        if self.selected_unit_id is None:
            return

        unit = self.game.units[self.selected_unit_id]
        if key == pygame.K_f:
            self.game.order_book.issue_change_formation(
                unit.id,
                cycle_formation(unit),
                current_turn=self.game.current_turn,
            )
        elif key == pygame.K_h:
            self.game.order_book.issue_hold(unit.id, current_turn=self.game.current_turn)
        elif key == pygame.K_r:
            self.game.order_book.issue_rally(unit.id, current_turn=self.game.current_turn)
        elif key == pygame.K_c:
            themes.apply_colorblind_mode()
        elif key == pygame.K_LEFT:
            self.camera.pan(25, 0)
        elif key == pygame.K_RIGHT:
            self.camera.pan(-25, 0)
        elif key == pygame.K_UP:
            self.camera.pan(0, 25)
        elif key == pygame.K_DOWN:
            self.camera.pan(0, -25)

    def _end_turn(self) -> None:
        self.ai.issue_orders(self.game)
        self.game.advance_turn()

        routing_this_turn = False
        objective_this_turn = False
        for event in self.game.event_log[-10:]:
            msg_lower = event.message.lower()
            if "rout" in msg_lower or "routing" in msg_lower:
                self.toasts.add(f"! {event.message[:50]}", colour=(200, 80, 80))
                routing_this_turn = True
            elif "objective" in msg_lower or "captures" in msg_lower:
                self.toasts.add(f"* {event.message[:50]}", colour=(50, 200, 80))
                objective_this_turn = True

        if routing_this_turn:
            self.audio.play("routing")
        if objective_this_turn:
            self.audio.play("objective_taken")
        self.audio.play("turn_end")

        report = self.game.victory_report()
        if report.level.value != "draw" or not self._has_combat_units():
            self.game_over = True
            self.victory_report = report
            side = getattr(report, "winner", None)
            if side is not None and side is self.player_side:
                self.audio.play("game_over_win")
            else:
                self.audio.play("game_over_lose")

        self.move_path = []
        self.pending_move_dest = None

    def _has_combat_units(self) -> bool:
        return any(
            not u.is_removed and u.unit_type is not UnitType.COMMANDER
            for u in self.game.units.values()
        )

    def _restart(self) -> None:
        self.game = GameState.from_scenario(self.scenario, rng_seed=self.game.rng_seed)
        self.game_over = False
        self.victory_report = None
        self.selected_unit_id = None
        self.move_path = []

    def _draw_move_path(self) -> None:
        if not self.move_path or len(self.move_path) < 2:
            return
        points = [self.camera.axial_to_screen(h) for h in self.move_path]
        for i in range(len(points) - 1):
            pygame.draw.line(self.screen, (255, 255, 100), points[i], points[i + 1], 2)
            if i > 0:
                pygame.draw.circle(self.screen, (255, 255, 100), points[i], 3)
        pygame.draw.circle(self.screen, (255, 220, 0), points[-1], 5, 2)

    def _draw_pause_overlay(self) -> None:
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(w // 2 - 120, h // 2 - 80, 240, 160)
        pygame.draw.rect(self.screen, themes.PANEL_BG, box, border_radius=6)
        pygame.draw.rect(self.screen, themes.PANEL_BORDER, box, 1, border_radius=6)

        title = self.font.render("PAUSED", True, themes.SELECTION)
        self.screen.blit(title, title.get_rect(centerx=w // 2, y=box.y + 14))

        items = [("Resume", "ESC"), ("Quit", "Q")]
        for i, (label, key) in enumerate(items):
            iy = box.y + 50 + i * 36
            btn = pygame.Rect(box.x + 20, iy, 200, 28)
            pygame.draw.rect(self.screen, (50, 70, 110), btn, border_radius=4)
            text = self.small_font.render(f"{label} ({key})", True, themes.TEXT)
            self.screen.blit(text, text.get_rect(center=btn.center))

    def _draw_game_over(self) -> None:
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(w // 2 - 200, h // 2 - 160, 400, 320)
        pygame.draw.rect(self.screen, themes.PANEL_BG, box, border_radius=8)
        pygame.draw.rect(self.screen, themes.SELECTION, box, 2, border_radius=8)

        report = self.victory_report
        if report is None:
            return

        winner_text = "DRAW" if report.winner is None else f"{report.winner.value.upper()} WINS"
        level_text = report.level.value.upper()

        title = self.font.render(f"{winner_text} - {level_text}", True, themes.SELECTION)
        self.screen.blit(title, title.get_rect(centerx=w // 2, y=box.y + 16))

        y = box.y + 50
        lh = 22
        for line in [
            f"Blue score: {report.blue_score}",
            f"Red score: {report.red_score}",
            f"Margin: {report.margin}",
            "",
            f"Turn: {self.game.current_turn}",
            "",
            "Press R to restart   Q to quit",
        ]:
            text = self.small_font.render(line, True, themes.TEXT)
            self.screen.blit(text, text.get_rect(centerx=w // 2, y=y))
            y += lh

    def _draw_help_overlay(self) -> None:
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(w // 2 - 220, h // 2 - 180, 440, 360)
        pygame.draw.rect(self.screen, themes.PANEL_BG, box, border_radius=6)
        pygame.draw.rect(self.screen, themes.PANEL_BORDER, box, 1, border_radius=6)

        title = self.font.render("Keyboard Reference", True, themes.SELECTION)
        self.screen.blit(title, title.get_rect(centerx=w // 2, y=box.y + 10))

        hotkeys = [
            ("Enter",       "End turn"),
            ("Escape",      "Pause / Resume"),
            ("F1 / ?",      "This help screen"),
            ("C",           "Toggle colour-blind mode"),
            ("F",           "Cycle formation"),
            ("H",           "Hold position"),
            ("R",           "Rally unit"),
            ("Arrow keys",  "Pan camera"),
            ("Scroll wheel", "Zoom in/out"),
            ("Middle drag", "Pan camera"),
            ("Left click",  "Select unit"),
            ("Right click", "Context menu"),
        ]

        y = box.y + 38
        lh = 22
        col_w = 200
        for key, desc in hotkeys:
            key_surf = self.small_font.render(key, True, themes.SELECTION)
            desc_surf = self.small_font.render(desc, True, themes.TEXT)
            self.screen.blit(key_surf, (box.x + 20, y))
            self.screen.blit(desc_surf, (box.x + 20 + col_w, y))
            y += lh

        close_hint = self.small_font.render("Press F1 or ? to close", True, themes.MUTED_TEXT)
        self.screen.blit(close_hint, close_hint.get_rect(centerx=w // 2, y=box.bottom - 22))

    def _draw(self) -> None:
        visibility = self.game.visibility.get(
            self.player_side,
            VisibilitySnapshot(
                side=self.player_side,
                visible_hexes=frozenset(),
                explored_hexes=frozenset(),
                visible_enemy_units=frozenset(),
                last_known_enemies={},
            ),
        )
        selected_unit = self.game.units.get(self.selected_unit_id) if self.selected_unit_id else None
        selected_hex = selected_unit.position if selected_unit and selected_unit.position else None

        move_targets = self._movement_targets(selected_unit)
        attack_targets = self._attack_targets(selected_unit)
        attack_range_hexes = self._attack_range_hexes(selected_unit)

        self.map_renderer.draw(
            self.screen,
            self.game,
            self.camera,
            visibility,
            hovered_hex=self.hover_hex,
            selected_hex=selected_hex,
            move_targets=move_targets,
            attack_targets=attack_targets,
            attack_range_hexes=attack_range_hexes,
        )
        self.unit_renderer.draw(
            self.screen,
            self.game,
            self.camera,
            self.player_side,
            visibility,
            selected_unit_id=self.selected_unit_id,
        )

        # B3: movement path preview
        self._draw_move_path()

        width, height = self.screen.get_size()
        top_bar_height = 28
        panel_top = top_bar_height + 12
        detail_rect = pygame.Rect(10, panel_top, 220, 265)
        order_rect = pygame.Rect(width - 230, panel_top, 220, 220)
        log_rect = pygame.Rect(180, height - 150, width - 190, 140)
        minimap_rect = pygame.Rect(10, height - 140, 160, 110)

        self.hud.unit_detail.draw(self.screen, detail_rect, selected_unit, self.font, self.small_font)
        self.end_turn_button = self.hud.order_panel.draw(self.screen, order_rect, self.game, self.player_side)
        self.hud.combat_log.draw(self.screen, log_rect, self.game.event_log, self.small_font)
        self.hud.minimap.draw(self.screen, self.game, minimap_rect, camera=self.camera, visibility=visibility)

        top_bar = pygame.Rect(0, 0, width, top_bar_height)
        pygame.draw.rect(self.screen, themes.PANEL_BG, top_bar)
        turn_text = self.font.render(
            f"Turn {self.game.current_turn}  Blue {self.game.score_for_side(Side.BLUE)} - Red {self.game.score_for_side(Side.RED)}",
            True,
            themes.TEXT,
        )
        self.screen.blit(turn_text, (250, 5))

        if themes.COLORBLIND_MODE:
            cb_surf = self.small_font.render("CB", True, (230, 159, 0))
            self.screen.blit(cb_surf, (width - 30, 6))

        if self.tutorial is not None:
            step = self.tutorial.update(self.game)
            tutorial_rect = pygame.Rect(250, panel_top, 520, 58)
            pygame.draw.rect(self.screen, themes.PANEL_BG, tutorial_rect, border_radius=4)
            pygame.draw.rect(self.screen, themes.PANEL_BORDER, tutorial_rect, 1, border_radius=4)
            title = self.small_font.render(step.title, True, themes.SELECTION)
            body = self.small_font.render(step.message[:90], True, themes.TEXT)
            self.screen.blit(title, (tutorial_rect.x + 8, tutorial_rect.y + 6))
            self.screen.blit(body, (tutorial_rect.x + 8, tutorial_rect.y + 24))
            # Progress bar
            bar_w = tutorial_rect.width - 16
            bar_rect = pygame.Rect(tutorial_rect.x + 8, tutorial_rect.y + 44, bar_w, 6)
            pygame.draw.rect(self.screen, themes.PANEL_BORDER, bar_rect, border_radius=3)
            fill_w = int(bar_w * self.tutorial.progress_fraction)
            if fill_w > 0:
                fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, 6)
                pygame.draw.rect(self.screen, themes.SELECTION, fill_rect, border_radius=3)

        # B13: toasts
        self.toasts.draw(self.screen, self.small_font)

        tooltip_lines = self._tooltip_lines(visibility)
        self.tooltip.draw(self.screen, pygame.mouse.get_pos(), tooltip_lines)

        # B5: context menu drawn on top of everything else
        self.context_menu.draw(self.screen, self.small_font)

        # B12: game over overlay
        if self.game_over:
            self._draw_game_over()

        # B11: pause overlay
        if self.paused:
            self._draw_pause_overlay()

        # B14: help overlay
        if self.show_help:
            self._draw_help_overlay()

    def _tooltip_lines(self, visibility) -> list[str]:
        if self.hover_hex is None or not self.game.battle_map.in_bounds(self.hover_hex):
            return []
        terrain = self.game.battle_map.terrain_at(self.hover_hex).value
        lines = [f"{self.hover_hex.q}, {self.hover_hex.r}", f"Terrain: {terrain}"]
        for unit in self.game.units_at(self.hover_hex):
            if unit.side is self.player_side or unit.id in visibility.visible_enemy_units:
                lines.append(f"{unit.name} ({unit.hit_points} HP)")
        return lines

    def _movement_targets(self, unit) -> set[HexCoord]:
        if unit is None or unit.position is None:
            return set()
        targets: set[HexCoord] = set()
        budget = unit.turn_movement_budget()
        costs = unit.movement_costs()
        for coord in self.game.battle_map.coords():
            path = self.game.battle_map.find_path(unit.position, coord, terrain_costs=costs)
            if not path:
                continue
            spent = 0.0
            for step in path[1:]:
                spent += self.game.battle_map.movement_cost(step, costs) * 100
            if spent <= budget:
                targets.add(coord)
        return targets

    def _attack_targets(self, unit) -> set[HexCoord]:
        if unit is None or unit.position is None:
            return set()
        attack_range = self.game.combat_resolver.max_range(unit)
        if attack_range <= 0:
            return set()
        targets = set()
        for enemy in self.game.units.values():
            if enemy.side is unit.side or enemy.position is None or enemy.is_removed:
                continue
            if unit.position.distance_to(enemy.position) <= max(1, attack_range):
                targets.add(enemy.position)
        return targets

    def _attack_range_hexes(self, unit) -> set[HexCoord]:
        """B4: All in-bounds hexes within this unit's attack range (ring overlay)."""
        if unit is None or unit.position is None:
            return set()
        attack_range = self.game.combat_resolver.max_range(unit)
        if attack_range <= 0:
            return set()
        ring: set[HexCoord] = set()
        for coord in self.game.battle_map.coords():
            if unit.position.distance_to(coord) <= max(1, attack_range):
                ring.add(coord)
        return ring

    def _top_player_unit_at(self, coord: HexCoord):
        for unit in self.game.units_at(coord):
            if unit.side is self.player_side:
                return unit
        return None

    def _top_enemy_unit_at(self, coord: HexCoord):
        for unit in self.game.units_at(coord):
            if unit.side is not self.player_side:
                return unit
        return None
