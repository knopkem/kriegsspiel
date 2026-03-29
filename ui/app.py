"""Playable pygame prototype front end."""

from __future__ import annotations

import os
import copy
import heapq
import math
import time

os.environ.setdefault("SDL_VIDEO_HIGHDPI_DISABLED", "1")

import pygame

import config
from ai.difficulty import AIDifficulty
from ai.opponent import SimpleAICommander
from core.fog_of_war import VisibilitySnapshot
from core.game import GameState
from core.map import HexCoord
from core.orders import OrderStatus, OrderType
from core.scenario import load_builtin_scenario
from core.tutorial import TutorialDirector
from core.units import MoraleState, Side, UnitType

from . import themes
from .animation import (
    AnimationManager,
    CascadeRingAnimation,
    DamageNumberAnimation,
    MeleeAnimation,
    RangedFireAnimation,
    UnitMoveAnimation,
)
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
    def __init__(self, *, scenario_name: str = "skirmish_small", seed: int = 1,
                 difficulty: str = "medium", game_state=None, campaign_mode: bool = False) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(themes.WINDOW_SIZE)
        pygame.display.set_caption("Kriegsspiel Prototype")
        self.clock = pygame.time.Clock()

        # L2: derive font scales from config.TEXT_SCALE (1=small, 2=medium, 3=large)
        self.font = BitmapFont(scale=config.TEXT_SCALE + 1)
        self.small_font = BitmapFont(scale=config.TEXT_SCALE)

        self._initial_scenario_name = scenario_name
        self._initial_seed = seed
        if game_state is not None:
            self.game = game_state
            self.scenario = None
        else:
            self.scenario = load_builtin_scenario(scenario_name)
            self.game = GameState.from_scenario(self.scenario, rng_seed=seed)
        self._initial_game_state = copy.deepcopy(self.game)
        self.player_side = Side.BLUE
        self.campaign_mode = campaign_mode
        self.ai = SimpleAICommander(Side.RED, difficulty=AIDifficulty(difficulty), seed=seed + 100)
        self.tutorial = TutorialDirector() if scenario_name == "tutorial" else None

        self.camera = Camera(*themes.WINDOW_SIZE, zoom=0.9, offset_x=180, offset_y=70)
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
        self._replay_button = pygame.Rect(0, 0, 0, 0)
        self._continue_button = pygame.Rect(0, 0, 0, 0)

        # B13: toasts
        self.toasts = ToastManager()

        # B14: help overlay
        self.show_help: bool = False

        # L2: flag set when text size changes; fonts are recreated next frame
        self._fonts_dirty: bool = False
        self._text_scale_btn_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        # K3: casualty table scroll offset
        self._casualty_scroll: int = 0

        # F5: audio engine (gracefully no-ops if mixer unavailable)
        self.audio = AudioEngine()

        # Animation framework (H1-H7)
        self.anim_manager = AnimationManager()
        self._anim_button_rects: dict[str, pygame.Rect] = {}

        # K2: log highlight hex + timestamp
        self._log_highlight_hex: HexCoord | None = None
        self._log_highlight_time: float = 0.0

        self._selection_overlay_cache_key: tuple | None = None
        self._cached_move_targets: set[HexCoord] = set()
        self._cached_attack_targets: set[HexCoord] = set()
        self._cached_attack_range_hexes: set[HexCoord] = set()

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
                        if not self.anim_manager.is_animating:
                            self._handle_left_click(event.pos)
                    elif event.button == 3:
                        if not self.anim_manager.is_animating:
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
                        if self.pending_move_dest is not None:
                            self.pending_move_dest = None
                            self.move_path = []
                        else:
                            self.paused = not self.paused
                    elif event.key == pygame.K_SPACE and self.anim_manager.is_animating:
                        self.anim_manager.skip_all()
                    elif self.paused:
                        if event.key == pygame.K_q:
                            self.quit_requested = True
                    else:
                        self._handle_keydown(event.key)

            if self.quit_requested:
                running = False

            # L2: recreate fonts/HUD if text scale changed
            if self._fonts_dirty:
                self._apply_text_scale()

            self._draw()
            pygame.display.flip()
            self.clock.tick(themes.FPS)

        pygame.quit()

    def _handle_left_click(self, pos: tuple[int, int]) -> None:
        # L2: text scale button in pause menu
        if self.paused:
            btn = getattr(self, "_text_scale_btn_rect", None)
            if btn is not None and btn.collidepoint(pos):
                config.TEXT_SCALE = (config.TEXT_SCALE % 3) + 1  # cycle 1→2→3→1
                self._fonts_dirty = True
            return

        for name, rect in self._anim_button_rects.items():
            if rect.collidepoint(pos):
                if name == "skip":
                    self.anim_manager.skip_all()
                else:
                    self.anim_manager.set_speed(float(name))
                return

        if self.context_menu.visible:
            selected = self.context_menu.click(pos)
            if selected is not None:
                self._execute_context_action(selected, pos)
                return

        # K9: replay button
        if self.game_over and self._replay_button.collidepoint(pos):
            self._restart()
            return
        if self.game_over and self._continue_button.collidepoint(pos):
            self.quit_requested = True
            return

        # H8: confirm pending move on left-click of the same hex
        if self.pending_move_dest is not None:
            clicked_coord = self.camera.screen_to_axial(pos)
            if clicked_coord == self.pending_move_dest and self.selected_unit_id:
                unit = self.game.units[self.selected_unit_id]
                self.game.order_book.issue_move(unit.id, self.pending_move_dest, current_turn=self.game.current_turn)
                self.audio.play("order_given")
                self.pending_move_dest = None
                self.move_path = []
                return
            else:
                # Clicking elsewhere cancels preview
                self.pending_move_dest = None
                self.move_path = []
                # fall through to normal selection

        # K2: click on combat log to pan to event location
        log_rect = pygame.Rect(180, self.screen.get_height() - 150, self.screen.get_width() - 190, 140)
        if log_rect.collidepoint(pos):
            if self.hud.combat_log.click_filter(pos):
                return
            coord = self.hud.combat_log.coord_for_click(pos)
            if coord is not None:
                self.camera.center_on(coord)
                self._log_highlight_hex = coord
                self._log_highlight_time = time.time()
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
            self._invalidate_selection_cache()
            self.selected_unit_id = None
            return
        unit = self._top_player_unit_at(coord)
        new_selected_id = unit.id if unit else None
        if new_selected_id != self.selected_unit_id:
            self._invalidate_selection_cache()
        self.selected_unit_id = new_selected_id
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
            self.audio.play("order_given")
            self.pending_move_dest = None
            self.move_path = []
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

        # H7: animation speed controls
        if key == pygame.K_1:
            self.anim_manager.set_speed(1.0)
            return
        if key == pygame.K_2:
            self.anim_manager.set_speed(2.0)
            return
        if key == pygame.K_4:
            self.anim_manager.set_speed(4.0)
            return

        # K1: cycle combat log filter
        if key == pygame.K_TAB:
            self.hud.combat_log.cycle_filter()
            return

        if self.game_over:
            if key == pygame.K_r:
                self._restart()
            elif self.campaign_mode and key in (pygame.K_c, pygame.K_RETURN):
                self.quit_requested = True
            elif key == pygame.K_q:
                self.quit_requested = True
            return

        if key == pygame.K_RETURN:
            # H8: confirm pending move preview
            if self.pending_move_dest is not None:
                unit = self.game.units.get(self.selected_unit_id)
                if unit:
                    self.game.order_book.issue_move(unit.id, self.pending_move_dest, current_turn=self.game.current_turn)
                    self.audio.play("order_given")
                self.pending_move_dest = None
                self.move_path = []
                return
            self._end_turn()
            return

        pan_step = 25
        if key in (pygame.K_LEFT, pygame.K_a):
            self.camera.pan(pan_step, 0)
            return
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.camera.pan(-pan_step, 0)
            return
        if key in (pygame.K_UP, pygame.K_w):
            self.camera.pan(0, pan_step)
            return
        if key in (pygame.K_DOWN, pygame.K_s):
            self.camera.pan(0, -pan_step)
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

    def _end_turn(self) -> None:
        previous_positions = {uid: unit.position for uid, unit in self.game.units.items()}
        previous_hp = {uid: unit.hit_points for uid, unit in self.game.units.items()}
        previous_morale = {uid: unit.morale_state for uid, unit in self.game.units.items()}
        self.ai.issue_orders(self.game)
        turn_events = self.game.advance_turn()

        routing_this_turn = False
        objective_this_turn = False
        for event in turn_events:
            msg_lower = event.message.lower()
            if "rout" in msg_lower or "routing" in msg_lower:
                self.toasts.add(f"! {event.message[:50]}", colour=(200, 80, 80))
                routing_this_turn = True
            elif "objective" in msg_lower or "captures" in msg_lower:
                self.toasts.add(f"* {event.message[:50]}", colour=(50, 200, 80))
                objective_this_turn = True

            # H2-H6: create animations for turn events
            if event.coord is not None:
                screen_pos = self.camera.axial_to_screen(event.coord)
                if event.category == "combat" and "fires on" in event.message:
                    attacker_name = event.message.split(" fires on ", 1)[0]
                    attacker = next((u for u in self.game.units.values() if u.name == attacker_name), None)
                    if attacker is not None and attacker.position is not None:
                        self.anim_manager.add(
                            RangedFireAnimation(
                                duration=0.2,
                                from_pos=self.camera.axial_to_screen(attacker.position),
                                to_pos=screen_pos,
                                is_artillery=attacker.unit_type is UnitType.ARTILLERY,
                            )
                        )
                elif event.category == "combat":
                    self.anim_manager.add(MeleeAnimation(duration=0.6, hex_pos=screen_pos))
                elif event.category == "morale":
                    self.anim_manager.add(CascadeRingAnimation(duration=0.7, hex_pos=screen_pos))

            # K10: minimap pulse for combat events
            if event.category == "combat" and event.coord is not None:
                self.hud.minimap.add_pulse(event.coord)

        for unit_id, before in previous_positions.items():
            after = self.game.units.get(unit_id)
            if after is None or before is None or after.position is None or before == after.position:
                continue
            distance = max(1, before.distance_to(after.position))
            self.anim_manager.add(
                UnitMoveAnimation(
                    duration=0.3 * distance,
                    unit_id=unit_id,
                    from_pos=self.camera.axial_to_screen(before),
                    to_pos=self.camera.axial_to_screen(after.position),
                )
            )

        for unit in self.game.units.values():
            if unit.position is None:
                continue
            old_hp = previous_hp.get(unit.id, unit.hit_points)
            old_morale = previous_morale.get(unit.id, unit.morale_state)
            hp_loss = max(0, old_hp - unit.hit_points)
            pos = self.camera.axial_to_screen(unit.position)
            if hp_loss > 0:
                self.anim_manager.add(
                    DamageNumberAnimation(
                        duration=1.0,
                        pos=(pos[0] + 8, pos[1] - 8),
                        text=f"-{hp_loss} HP",
                        colour=(220, 80, 80),
                    )
                )
            if old_morale != unit.morale_state:
                self.anim_manager.add(
                    DamageNumberAnimation(
                        duration=1.0,
                        pos=(pos[0] - 10, pos[1] - 24),
                        text=unit.morale_state.value.upper(),
                        colour=(90, 160, 240),
                    )
                )

        if routing_this_turn:
            self.audio.play("routing")
        if objective_this_turn:
            self.audio.play("objective_taken")
        self.audio.play("turn_end")

        report = self.game.victory_report()
        blue_alive = any(
            unit.side is Side.BLUE and unit.unit_type is not UnitType.COMMANDER and not unit.is_removed
            for unit in self.game.units.values()
        )
        red_alive = any(
            unit.side is Side.RED and unit.unit_type is not UnitType.COMMANDER and not unit.is_removed
            for unit in self.game.units.values()
        )
        turn_limit_reached = self.game.max_turns is not None and self.game.current_turn > self.game.max_turns
        if turn_limit_reached or not blue_alive or not red_alive:
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
        self.game = copy.deepcopy(self._initial_game_state)
        self.game_over = False
        self.victory_report = None
        self.selected_unit_id = None
        self.move_path = []
        self.pending_move_dest = None
        self.anim_manager.skip_all()
        self._invalidate_selection_cache()

    def _apply_text_scale(self) -> None:
        """L2: Recreate fonts and dependent HUD components after a scale change."""
        self._fonts_dirty = False
        self.font = BitmapFont(scale=config.TEXT_SCALE + 1)
        self.small_font = BitmapFont(scale=config.TEXT_SCALE)
        self.unit_renderer = UnitRenderer(self.small_font)
        self.hud = HUD(self.font, self.small_font)
        self.tooltip = Tooltip(self.small_font)

    def _draw_move_path(self) -> None:
        for order in self.game.order_book.all_orders():
            if order.status is not OrderStatus.QUEUED or order.order_type not in {OrderType.MOVE, OrderType.RETREAT}:
                continue
            unit = self.game.units.get(order.unit_id)
            if unit is None or unit.side is not self.player_side or unit.position is None or order.destination is None:
                continue
            path = self.game.battle_map.find_path(
                unit.position,
                order.destination,
                terrain_costs=unit.movement_costs(),
            ) or [unit.position, order.destination]
            self._draw_path(
                path,
                colour=themes.SELECTION if unit.id == self.selected_unit_id else (120, 180, 255),
                show_costs=(unit.id == self.selected_unit_id),
            )

        if not self.move_path or len(self.move_path) < 2:
            return
        self._draw_path(self.move_path, colour=themes.SELECTION, show_costs=True)

        # Ghost unit at destination (semi-transparent circle)
        if self.pending_move_dest is not None:
            dest_screen = self.camera.axial_to_screen(self.pending_move_dest)
            ghost_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, (255, 220, 90, 128), (15, 15), 12)
            pygame.draw.circle(ghost_surf, (255, 220, 90, 180), (15, 15), 12, 2)
            self.screen.blit(ghost_surf, (dest_screen[0] - 15, dest_screen[1] - 15))

    def _draw_path(self, path: list[HexCoord], *, colour: tuple[int, int, int], show_costs: bool) -> None:
        if len(path) < 2:
            return
        points = [self.camera.axial_to_screen(h) for h in path]
        dash_len = 8
        gap_len = 4
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            seg_len = math.sqrt(dx * dx + dy * dy)
            if seg_len < 1:
                continue
            nx = dx / seg_len
            ny = dy / seg_len
            pos = 0.0
            drawing = True
            while pos < seg_len:
                end_pos = min(pos + (dash_len if drawing else gap_len), seg_len)
                if drawing:
                    start_pt = (int(p1[0] + nx * pos), int(p1[1] + ny * pos))
                    end_pt = (int(p1[0] + nx * end_pos), int(p1[1] + ny * end_pos))
                    pygame.draw.line(self.screen, colour, start_pt, end_pt, 2)
                pos = end_pos
                drawing = not drawing

        selected = self.game.units.get(self.selected_unit_id) if self.selected_unit_id else None
        if show_costs and selected is not None:
            spent = 0.0
            costs = selected.movement_costs()
            for step in path[1:]:
                spent += self.game.battle_map.movement_cost(step, costs)
                sx, sy = self.camera.axial_to_screen(step)
                label = self.small_font.render(f"{spent:.1f}", True, colour)
                self.screen.blit(label, label.get_rect(center=(sx, sy - 14)))

    def _draw_pause_overlay(self) -> None:
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(w // 2 - 140, h // 2 - 110, 280, 220)
        pygame.draw.rect(self.screen, themes.PANEL_BG, box, border_radius=6)
        pygame.draw.rect(self.screen, themes.PANEL_BORDER, box, 1, border_radius=6)

        title = self.font.render("PAUSED", True, themes.SELECTION)
        self.screen.blit(title, title.get_rect(centerx=w // 2, y=box.y + 14))

        items = [("Resume", "ESC"), ("Quit", "Q")]
        for i, (label, key) in enumerate(items):
            iy = box.y + 50 + i * 36
            btn = pygame.Rect(box.x + 20, iy, 240, 28)
            pygame.draw.rect(self.screen, (50, 70, 110), btn, border_radius=4)
            text = self.small_font.render(f"{label} ({key})", True, themes.TEXT)
            self.screen.blit(text, text.get_rect(center=btn.center))

        # L2: Text size setting
        scale_names = {1: "Small", 2: "Medium", 3: "Large"}
        scale_y = box.y + 50 + len(items) * 36 + 8
        scale_lbl = self.small_font.render("Text Size:", True, themes.MUTED_TEXT)
        self.screen.blit(scale_lbl, (box.x + 20, scale_y + 4))
        scale_btn = pygame.Rect(box.x + 130, scale_y, 110, 28)
        pygame.draw.rect(self.screen, (45, 65, 90), scale_btn, border_radius=4)
        pygame.draw.rect(self.screen, themes.PANEL_BORDER, scale_btn, 1, border_radius=4)
        cur_name = scale_names.get(config.TEXT_SCALE, "Medium")
        sz_text = self.small_font.render(cur_name, True, themes.SELECTION)
        self.screen.blit(sz_text, sz_text.get_rect(center=scale_btn.center))

        # Store rect for click detection in _handle_left_click via pause overlay
        self._text_scale_btn_rect = scale_btn

    def _draw_game_over(self) -> None:
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        report = self.victory_report
        if report is None:
            return

        # K3: Expand box to fit casualty table
        box = pygame.Rect(w // 2 - 320, h // 2 - 280, 640, 560)
        pygame.draw.rect(self.screen, themes.PANEL_BG, box, border_radius=8)
        pygame.draw.rect(self.screen, themes.SELECTION, box, 2, border_radius=8)

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
        ]:
            text = self.small_font.render(line, True, themes.TEXT)
            self.screen.blit(text, text.get_rect(centerx=w // 2, y=y))
            y += lh

        # K9: Replay / Continue-or-Quit buttons
        btn_w, btn_h = 160, 34
        replay_rect = pygame.Rect(w // 2 - btn_w - 10, y + 10, btn_w, btn_h)
        continue_rect = pygame.Rect(w // 2 + 10, y + 10, btn_w, btn_h)
        self._replay_button = replay_rect
        self._continue_button = continue_rect

        pygame.draw.rect(self.screen, (50, 100, 80), replay_rect, border_radius=4)
        pygame.draw.rect(self.screen, themes.SELECTION, replay_rect, 1, border_radius=4)
        replay_txt = self.small_font.render("R - REPLAY", True, themes.SELECTION)
        self.screen.blit(replay_txt, replay_txt.get_rect(center=replay_rect.center))

        pygame.draw.rect(self.screen, (80, 50, 50), continue_rect, border_radius=4)
        pygame.draw.rect(self.screen, themes.TEXT, continue_rect, 1, border_radius=4)
        continue_label = "C - CONTINUE" if self.campaign_mode else "Q - QUIT"
        continue_txt = self.small_font.render(continue_label, True, themes.TEXT)
        self.screen.blit(continue_txt, continue_txt.get_rect(center=continue_rect.center))

        # K4: Score graph
        y += btn_h + 18
        self._draw_score_graph(box, y)
        y += 96  # graph height (80) + labels (14) + margin

        # K3: Casualty table
        self._draw_casualty_table(box, y)

    def _draw_score_graph(self, box: pygame.Rect, start_y: int) -> None:
        """K4: Line chart of blue/red scores over turns."""
        history = self.game.score_history
        if len(history) < 2:
            return

        graph_rect = pygame.Rect(box.x + 20, start_y, box.width - 40, 80)
        pygame.draw.rect(self.screen, (20, 24, 32), graph_rect)
        pygame.draw.rect(self.screen, themes.PANEL_BORDER, graph_rect, 1)

        max_score = max((max(b, r) for b, r in history), default=1)
        max_score = max(max_score, 1)
        n = len(history)

        def _x(i: int) -> int:
            return graph_rect.x + int(i / (n - 1) * (graph_rect.width - 1))

        def _y(score: int) -> int:
            frac = score / max_score
            return graph_rect.bottom - 2 - int(frac * (graph_rect.height - 4))

        blue_pts = [(_x(i), _y(b)) for i, (b, _r) in enumerate(history)]
        red_pts  = [(_x(i), _y(r)) for i, (_b, r) in enumerate(history)]

        if len(blue_pts) >= 2:
            pygame.draw.lines(self.screen, themes.BLUE_UNIT, False, blue_pts, 2)
        if len(red_pts) >= 2:
            pygame.draw.lines(self.screen, themes.RED_UNIT, False, red_pts, 2)

        # Axis labels
        t1 = self.small_font.render("T1", True, themes.MUTED_TEXT)
        self.screen.blit(t1, (graph_rect.x, graph_rect.bottom + 2))
        tn = self.small_font.render(f"T{n}", True, themes.MUTED_TEXT)
        self.screen.blit(tn, (graph_rect.right - tn.get_width(), graph_rect.bottom + 2))
        top_lbl = self.small_font.render(str(max_score), True, themes.MUTED_TEXT)
        self.screen.blit(top_lbl, (graph_rect.x, graph_rect.y))

    def _draw_casualty_table(self, box: pygame.Rect, start_y: int) -> None:
        """K3: Render per-unit casualty table inside the game-over box."""
        _STATUS_ORDER = {
            MoraleState.BROKEN:  0,
            MoraleState.ROUTING: 1,
            MoraleState.SHAKEN:  2,
            MoraleState.STEADY:  3,
        }

        def _unit_status(unit) -> str:
            if unit.hit_points <= 0 or unit.is_removed:
                return "Destroyed"
            state = unit.morale_state
            if state is MoraleState.ROUTING:
                return "Routing"
            if state is MoraleState.BROKEN:
                return "Broken"
            if state is MoraleState.SHAKEN:
                return "Shaken"
            return "Active"

        def _sort_key(unit):
            hp_frac = unit.hit_points / max(1, unit.max_hit_points)
            state_order = _STATUS_ORDER.get(unit.morale_state, 3)
            destroyed = 1 if (unit.hit_points <= 0 or unit.is_removed) else 0
            return (-destroyed, state_order, hp_frac)

        all_units = list(self.game.units.values())
        blue_units = sorted([u for u in all_units if u.side is Side.BLUE], key=_sort_key)
        red_units  = sorted([u for u in all_units if u.side is Side.RED],  key=_sort_key)

        w = self.screen.get_width()
        tbl_x = box.x + 10
        tbl_w = box.width - 20
        col_name_w = tbl_w * 35 // 100
        col_shp_w  = tbl_w * 12 // 100
        col_fhp_w  = tbl_w * 12 // 100
        col_stat_w = tbl_w * 25 // 100

        cols = [
            ("UNIT", tbl_x + 4),
            ("START", tbl_x + col_name_w + 4),
            ("FINAL", tbl_x + col_name_w + col_shp_w + 4),
            ("STATUS", tbl_x + col_name_w + col_shp_w + col_fhp_w + 4),
        ]

        ROW_H = 18
        MAX_VISIBLE = 4  # rows per side in the box
        y = start_y

        for side_units, header_color, label in [
            (blue_units, themes.BLUE_UNIT, "BLUE FORCES"),
            (red_units,  themes.RED_UNIT,  "RED FORCES"),
        ]:
            if not side_units:
                continue

            # Section header
            hdr_rect = pygame.Rect(tbl_x, y, tbl_w, ROW_H + 2)
            pygame.draw.rect(self.screen, header_color, hdr_rect, border_radius=3)
            hdr_surf = self.small_font.render(label, True, themes.TEXT)
            self.screen.blit(hdr_surf, hdr_surf.get_rect(centerx=tbl_x + tbl_w // 2, y=y + 2))

            # Column headers
            y += ROW_H + 4
            for col_label, cx in cols:
                ch_surf = self.small_font.render(col_label, True, themes.MUTED_TEXT)
                self.screen.blit(ch_surf, (cx, y))
            y += ROW_H

            # Rows (capped at MAX_VISIBLE with optional overflow note)
            visible = side_units[:MAX_VISIBLE]
            for i, unit in enumerate(visible):
                row_rect = pygame.Rect(tbl_x, y, tbl_w, ROW_H)
                row_bg = (36, 40, 54) if i % 2 == 0 else (28, 32, 44)
                pygame.draw.rect(self.screen, row_bg, row_rect)

                status = _unit_status(unit)
                if status == "Destroyed":
                    name_color = (120, 60, 60)
                elif status == "Routing":
                    name_color = (180, 130, 60)
                else:
                    name_color = themes.TEXT

                name_surf = self.small_font.render(unit.name[:20], True, name_color)
                self.screen.blit(name_surf, (tbl_x + 4, y + 2))

                shp_surf = self.small_font.render(str(unit.max_hit_points), True, themes.MUTED_TEXT)
                self.screen.blit(shp_surf, (tbl_x + col_name_w + 4, y + 2))

                fhp = 0 if (unit.hit_points <= 0 or unit.is_removed) else unit.hit_points
                fhp_color = (120, 60, 60) if fhp == 0 else themes.TEXT
                fhp_surf = self.small_font.render(str(fhp), True, fhp_color)
                self.screen.blit(fhp_surf, (tbl_x + col_name_w + col_shp_w + 4, y + 2))

                stat_surf = self.small_font.render(status, True, name_color)
                self.screen.blit(stat_surf, (tbl_x + col_name_w + col_shp_w + col_fhp_w + 4, y + 2))

                y += ROW_H

            if len(side_units) > MAX_VISIBLE:
                more_surf = self.small_font.render(
                    f"+{len(side_units) - MAX_VISIBLE} more", True, themes.MUTED_TEXT
                )
                self.screen.blit(more_surf, (tbl_x + tbl_w - 60, y))
                y += ROW_H

            y += 6  # gap between sections

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
            ("WASD / Arrows", "Pan camera"),
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
            animated_centers=self.anim_manager.animated_unit_centers(),
        )

        # B3: movement path preview
        self._draw_move_path()

        # H3: draw active animations
        self.anim_manager.draw(self.screen, self.camera, self.small_font)
        self.anim_manager.update()

        # K2: log highlight hex (flashes for 2s after clicking a log entry)
        if self._log_highlight_hex is not None:
            elapsed = time.time() - self._log_highlight_time
            if elapsed < 2.0:
                alpha = int((1.0 - elapsed / 2.0) * 180)
                hl_pos = self.camera.axial_to_screen(self._log_highlight_hex)
                hl_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                pygame.draw.circle(hl_surf, (255, 255, 100, alpha), hl_pos, 20, 3)
                self.screen.blit(hl_surf, (0, 0))
            else:
                self._log_highlight_hex = None

        width, height = self.screen.get_size()
        top_bar_height = 24
        panel_top = top_bar_height + 12
        detail_rect = pygame.Rect(10, panel_top, 200, 232)
        order_rect = pygame.Rect(width - 210, panel_top, 200, 190)
        log_rect = pygame.Rect(168, height - 132, width - 178, 122)
        minimap_rect = pygame.Rect(10, height - 132, 148, 100)

        self.hud.unit_detail.draw(self.screen, detail_rect, selected_unit, self.font, self.small_font)
        self.end_turn_button = self.hud.order_panel.draw(self.screen, order_rect, self.game, self.player_side)
        self.hud.combat_log.draw(self.screen, log_rect, self.game.event_log, self.small_font)
        self.hud.minimap.draw(self.screen, self.game, minimap_rect, camera=self.camera, visibility=visibility)
        self._draw_animation_controls(width, height)

        top_bar = pygame.Rect(0, 0, width, top_bar_height)
        pygame.draw.rect(self.screen, themes.PANEL_BG, top_bar)
        turn_text = self.font.render(
            (
                f"Turn {self.game.current_turn}/{self.game.max_turns}  "
                if self.game.max_turns is not None
                else f"Turn {self.game.current_turn}  "
            )
            + f"Blue {self.game.score_for_side(Side.BLUE)} - Red {self.game.score_for_side(Side.RED)}",
            True,
            themes.TEXT,
        )
        self.screen.blit(turn_text, (250, 5))

        if themes.COLORBLIND_MODE:
            cb_surf = self.small_font.render("CB", True, (230, 159, 0))
            self.screen.blit(cb_surf, (width - 30, 6))

        # H7: speed indicator in top bar
        if self.anim_manager.is_animating:
            spd_label = ">>|"
        else:
            spd = self.anim_manager.speed_multiplier
            spd_label = f"{int(spd)}x" if spd == int(spd) else f"{spd:.1f}x"
        spd_surf = self.small_font.render(spd_label, True, themes.MUTED_TEXT)
        self.screen.blit(spd_surf, (width - 60, 6))

        if self.tutorial is not None:
            step = self.tutorial.update(self.game)
            tutorial_rect = pygame.Rect(250, panel_top, 620, 78)
            pygame.draw.rect(self.screen, themes.PANEL_BG, tutorial_rect, border_radius=4)
            pygame.draw.rect(self.screen, themes.PANEL_BORDER, tutorial_rect, 1, border_radius=4)
            title = self.small_font.render(step.title, True, themes.SELECTION)
            self.screen.blit(title, (tutorial_rect.x + 8, tutorial_rect.y + 6))
            body_lines = self._wrap_bitmap_text(
                step.message,
                self.small_font,
                tutorial_rect.width - 16,
            )[:2]
            for i, line in enumerate(body_lines):
                body = self.small_font.render(line, True, themes.TEXT)
                self.screen.blit(body, (tutorial_rect.x + 8, tutorial_rect.y + 24 + i * 14))
            # Progress bar
            bar_w = tutorial_rect.width - 16
            bar_rect = pygame.Rect(tutorial_rect.x + 8, tutorial_rect.bottom - 14, bar_w, 6)
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

    def _draw_animation_controls(self, width: int, height: int) -> None:
        labels = [("1", "1x"), ("2", "2x"), ("4", "4x"), ("skip", "Skip")]
        self._anim_button_rects = {}
        btn_w = 48
        btn_h = 22
        gap = 6
        total_w = len(labels) * btn_w + (len(labels) - 1) * gap
        x = width - total_w - 12
        y = height - 158
        for key, label in labels:
            rect = pygame.Rect(x, y, btn_w, btn_h)
            self._anim_button_rects[key] = rect
            active = (
                key != "skip"
                and self.anim_manager.speed_multiplier == float(key)
            )
            pygame.draw.rect(
                self.screen,
                (60, 80, 120) if active else (42, 47, 60),
                rect,
                border_radius=4,
            )
            pygame.draw.rect(self.screen, themes.PANEL_BORDER, rect, 1, border_radius=4)
            txt = self.small_font.render(label, True, themes.SELECTION if active else themes.TEXT)
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            x += btn_w + gap

    def _tooltip_lines(self, visibility) -> list[str]:
        if self.hover_hex is None or not self.game.battle_map.in_bounds(self.hover_hex):
            return []
        terrain_type = self.game.battle_map.terrain_at(self.hover_hex)
        terrain = terrain_type.value
        lines = [f"{self.hover_hex.q}, {self.hover_hex.r}", f"Terrain: {terrain}"]
        for unit in self.game.units_at(self.hover_hex):
            if unit.side is self.player_side or unit.id in visibility.visible_enemy_units:
                lines.append(f"{unit.name} ({unit.hit_points} HP)")

        # H9: damage estimate when friendly unit selected and hover over enemy in range
        selected_unit = self.game.units.get(self.selected_unit_id) if self.selected_unit_id else None
        if selected_unit and selected_unit.side is self.player_side:
            hover_units = list(self.game.units_at(self.hover_hex))
            enemy_unit = next((u for u in hover_units if u.side is not self.player_side and not u.is_removed), None)
            if enemy_unit and self.hover_hex in self._attack_targets(selected_unit):
                from core.combat import preview_combat
                dist = selected_unit.position.distance_to(self.hover_hex) if selected_unit.position else 999
                min_dmg, max_dmg, morale_risk = preview_combat(
                    selected_unit, enemy_unit,
                    distance_hexes=dist,
                    defender_terrain=terrain_type,
                )
                lines.append(f"Est. {min_dmg}-{max_dmg} HP dmg | {morale_risk}")
        return lines

    def _movement_targets(self, unit) -> set[HexCoord]:
        if unit is None or unit.position is None:
            return set()
        self._ensure_selection_overlay_cache(unit)
        return self._cached_move_targets

    def _attack_targets(self, unit) -> set[HexCoord]:
        if unit is None or unit.position is None:
            return set()
        self._ensure_selection_overlay_cache(unit)
        return self._cached_attack_targets

    def _attack_range_hexes(self, unit) -> set[HexCoord]:
        """B4: All in-bounds hexes within this unit's attack range (ring overlay)."""
        if unit is None or unit.position is None:
            return set()
        self._ensure_selection_overlay_cache(unit)
        return self._cached_attack_range_hexes

    def _invalidate_selection_cache(self) -> None:
        self._selection_overlay_cache_key = None
        self._cached_move_targets = set()
        self._cached_attack_targets = set()
        self._cached_attack_range_hexes = set()

    def _ensure_selection_overlay_cache(self, unit) -> None:
        if unit is None or unit.position is None:
            self._invalidate_selection_cache()
            return
        cache_key = (
            unit.id,
            self.game.current_turn,
            unit.position.q,
            unit.position.r,
            unit.formation.value,
            unit.fatigue,
            unit.ammo,
            unit.hit_points,
            unit.morale_state.value,
        )
        if cache_key == self._selection_overlay_cache_key:
            return
        self._selection_overlay_cache_key = cache_key
        self._cached_move_targets = self._compute_reachable_hexes(unit)
        self._cached_attack_targets = self._compute_attack_targets(unit)
        self._cached_attack_range_hexes = self._compute_attack_range_hexes(unit)

    def _compute_reachable_hexes(self, unit) -> set[HexCoord]:
        if unit.position is None:
            return set()
        costs = unit.movement_costs()
        budget = unit.turn_movement_budget() / 100.0
        best_cost: dict[HexCoord, float] = {unit.position: 0.0}
        frontier: list[tuple[float, int, HexCoord]] = [(0.0, 0, unit.position)]
        push_count = 1

        while frontier:
            spent, _, coord = heapq.heappop(frontier)
            if spent > best_cost.get(coord, math.inf):
                continue
            for neighbor in self.game.battle_map.neighbors(coord):
                step_cost = self.game.battle_map.movement_cost(neighbor, costs)
                if math.isinf(step_cost):
                    continue
                new_cost = spent + step_cost
                if new_cost > budget:
                    continue
                if new_cost >= best_cost.get(neighbor, math.inf):
                    continue
                best_cost[neighbor] = new_cost
                heapq.heappush(frontier, (new_cost, push_count, neighbor))
                push_count += 1

        best_cost.pop(unit.position, None)
        return set(best_cost)

    def _compute_attack_targets(self, unit) -> set[HexCoord]:
        if unit.position is None:
            return set()
        attack_range = self.game.combat_resolver.max_range(unit)
        if attack_range <= 0:
            return set()
        return {
            enemy.position
            for enemy in self.game.units.values()
            if enemy.side is not unit.side
            and enemy.position is not None
            and not enemy.is_removed
            and unit.position.distance_to(enemy.position) <= max(1, attack_range)
        }

    def _compute_attack_range_hexes(self, unit) -> set[HexCoord]:
        if unit.position is None:
            return set()
        attack_range = self.game.combat_resolver.max_range(unit)
        if attack_range <= 0:
            return set()
        return {
            coord
            for coord in self.game.battle_map.coords()
            if unit.position.distance_to(coord) <= max(1, attack_range)
        }

    def _wrap_bitmap_text(self, text: str, font: BitmapFont, max_width: int) -> list[str]:
        char_width = max(1, (5 * font.scale) + font.scale)
        max_chars = max(1, max_width // char_width)
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word])
            if len(candidate) > max_chars and current:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
        return lines

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
