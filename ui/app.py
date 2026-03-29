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
from core.units import Side

from . import themes
from .bitmap_font import BitmapFont
from .camera import Camera
from .hud import HUD
from .input_handler import cycle_formation
from .map_renderer import MapRenderer
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

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_hex = self.camera.screen_to_axial(event.pos)
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
                        self.camera.zoom_at(1.1, event.pos)
                    elif event.button == 5:
                        self.camera.zoom_at(0.9, event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                    self.dragging = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)

            self._draw()
            pygame.display.flip()
            self.clock.tick(themes.FPS)

        pygame.quit()

    def _handle_left_click(self, pos: tuple[int, int]) -> None:
        minimap_rect = pygame.Rect(10, self.screen.get_height() - 140, 160, 110)
        mini_coord = self.hud.minimap.click_to_coord(self.game, minimap_rect, pos)
        if mini_coord is not None:
            screen_pos = self.camera.axial_to_screen(HexCoord(*mini_coord))
            self.camera.pan((self.screen.get_width() // 2) - screen_pos[0], (self.screen.get_height() // 2) - screen_pos[1])
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

    def _handle_right_click(self, pos: tuple[int, int]) -> None:
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
            self.game.order_book.issue_attack(unit.id, enemy.id, current_turn=self.game.current_turn)
        else:
            self.game.order_book.issue_move(unit.id, coord, current_turn=self.game.current_turn)

    def _handle_keydown(self, key: int) -> None:
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

        self.map_renderer.draw(
            self.screen,
            self.game,
            self.camera,
            visibility,
            hovered_hex=self.hover_hex,
            selected_hex=selected_hex,
            move_targets=move_targets,
            attack_targets=attack_targets,
        )
        self.unit_renderer.draw(
            self.screen,
            self.game,
            self.camera,
            self.player_side,
            visibility,
            selected_unit_id=self.selected_unit_id,
        )

        width, height = self.screen.get_size()
        top_bar_height = 28
        panel_top = top_bar_height + 12
        detail_rect = pygame.Rect(10, panel_top, 220, 170)
        order_rect = pygame.Rect(width - 230, panel_top, 220, 220)
        log_rect = pygame.Rect(180, height - 150, width - 190, 140)
        minimap_rect = pygame.Rect(10, height - 140, 160, 110)

        self.hud.unit_detail.draw(self.screen, detail_rect, selected_unit)
        self.end_turn_button = self.hud.order_panel.draw(self.screen, order_rect, self.game, self.player_side)
        self.hud.combat_log.draw(self.screen, log_rect, self.game.event_log)
        self.hud.minimap.draw(self.screen, self.game, minimap_rect)

        top_bar = pygame.Rect(0, 0, width, top_bar_height)
        pygame.draw.rect(self.screen, themes.PANEL_BG, top_bar)
        turn_text = self.font.render(
            f"Turn {self.game.current_turn}  Blue {self.game.score_for_side(Side.BLUE)} - Red {self.game.score_for_side(Side.RED)}",
            True,
            themes.TEXT,
        )
        self.screen.blit(turn_text, (250, 5))

        if self.tutorial is not None:
            step = self.tutorial.update(self.game)
            tutorial_rect = pygame.Rect(250, panel_top, 520, 50)
            pygame.draw.rect(self.screen, themes.PANEL_BG, tutorial_rect, border_radius=4)
            pygame.draw.rect(self.screen, themes.PANEL_BORDER, tutorial_rect, 1, border_radius=4)
            title = self.small_font.render(step.title, True, themes.SELECTION)
            body = self.small_font.render(step.message[:90], True, themes.TEXT)
            self.screen.blit(title, (tutorial_rect.x + 8, tutorial_rect.y + 6))
            self.screen.blit(body, (tutorial_rect.x + 8, tutorial_rect.y + 24))

        tooltip_lines = self._tooltip_lines(visibility)
        self.tooltip.draw(self.screen, pygame.mouse.get_pos(), tooltip_lines)

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
