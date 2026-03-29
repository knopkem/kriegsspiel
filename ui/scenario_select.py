"""G2: Scenario selection screen."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pygame

from . import themes
from .bitmap_font import BitmapFont

_SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


def _load_scenarios() -> list[dict[str, Any]]:
    """Load all JSON scenario files; sort by difficulty then title."""
    results: list[dict[str, Any]] = []
    for path in sorted(_SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_path"] = str(path)
            data["_id"] = path.stem
            results.append(data)
        except Exception:
            continue
    results.sort(key=lambda d: (d.get("difficulty_stars", 99), d.get("title", "")))
    return results


def _stars(n: Any) -> str:
    """Return a star-rating string."""
    try:
        count = int(n)
    except (TypeError, ValueError):
        return "?"
    return "*" * min(max(count, 0), 5) or "?"


def _map_size_str(data: dict) -> str:
    rows = data.get("map_rows", [])
    h = len(rows)
    w = len(rows[0]) if rows else 0
    if h == 0:
        return "?"
    return f"{w}x{h}"


def _unit_counts(data: dict) -> tuple[int, int]:
    units = data.get("units", [])
    blue = sum(1 for u in units if u.get("side") == "blue")
    red = sum(1 for u in units if u.get("side") == "red")
    return blue, red


def _description(data: dict) -> str:
    briefing = data.get("briefing", "") or data.get("description", "")
    if not briefing:
        return ""
    first_line = briefing.split("\n")[0].strip()
    return first_line[:70]


class ScenarioSelect:
    """Interactive scenario picker.

    Returns a dict via :meth:`handle_event` once the player picks a scenario,
    or the string ``"back"`` if they press Back.
    """

    _ROW_H = 30
    _LIST_X = 40
    _LIST_Y = 100
    _LIST_W = 560
    _DETAIL_X = 640
    _DETAIL_Y = 90
    _VISIBLE_ROWS = 16
    _BACK_H = 32

    def __init__(self, font: BitmapFont, small_font: BitmapFont) -> None:
        self.font = font
        self.small_font = small_font
        self._scenarios = _load_scenarios()
        self._selected = 0
        self._scroll = 0
        # "Back" is index -1 (sentinel)
        self._back_rect = pygame.Rect(0, 0, 0, 0)
        self._row_rects: list[pygame.Rect] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> dict | str | None:
        """Return scenario config dict, ``"back"`` string, or None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key in (pygame.K_UP, pygame.K_k):
                self._move_selection(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_j):
                self._move_selection(1)
            elif event.key == pygame.K_RETURN:
                return self._confirm()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self._back_rect.collidepoint(event.pos):
                    return "back"
                for i, rect in enumerate(self._row_rects):
                    if rect.collidepoint(event.pos):
                        idx = self._scroll + i
                        if idx < len(self._scenarios):
                            if self._selected == idx:
                                return self._confirm()
                            self._selected = idx

            elif event.button == 4:
                self._move_selection(-1)
            elif event.button == 5:
                self._move_selection(1)

        return None

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        surface.fill(themes.PANEL_BG)

        # Title
        title = self.font.render("CHOOSE SCENARIO", True, themes.SELECTION)
        surface.blit(title, title.get_rect(centerx=w // 2, y=18))

        # Back button
        back_rect = pygame.Rect(self._LIST_X, 58, 90, self._BACK_H)
        self._back_rect = back_rect
        pygame.draw.rect(surface, (50, 60, 80), back_rect, border_radius=4)
        pygame.draw.rect(surface, themes.PANEL_BORDER, back_rect, 1, border_radius=4)
        back_text = self.small_font.render("< BACK", True, themes.TEXT)
        surface.blit(back_text, back_text.get_rect(center=back_rect.center))

        # Column headers
        hx = self._LIST_X
        hy = self._LIST_Y - 20
        for label, cx in [("SCENARIO", hx + 4), ("MAP", hx + 310), ("DIFF", hx + 390), ("FORCES", hx + 450)]:
            col_label = self.small_font.render(label, True, themes.MUTED_TEXT)
            surface.blit(col_label, (cx, hy))

        # Divider
        pygame.draw.line(surface, themes.PANEL_BORDER,
                         (self._LIST_X, self._LIST_Y - 4),
                         (self._LIST_X + self._LIST_W, self._LIST_Y - 4))

        # Scenario rows
        self._row_rects = []
        visible_end = min(self._scroll + self._VISIBLE_ROWS, len(self._scenarios))
        for i, si in enumerate(range(self._scroll, visible_end)):
            data = self._scenarios[si]
            ry = self._LIST_Y + i * self._ROW_H
            row_rect = pygame.Rect(self._LIST_X, ry, self._LIST_W, self._ROW_H - 2)
            self._row_rects.append(row_rect)

            selected = si == self._selected
            if selected:
                pygame.draw.rect(surface, (60, 70, 100), row_rect, border_radius=3)
                pygame.draw.rect(surface, themes.SELECTION, row_rect, 1, border_radius=3)
            elif i % 2 == 0:
                pygame.draw.rect(surface, (36, 40, 50), row_rect, border_radius=2)

            name_color = themes.SELECTION if selected else themes.TEXT
            title_str = data.get("title", data["_id"])[:32]
            name_surf = self.small_font.render(title_str, True, name_color)
            surface.blit(name_surf, (row_rect.x + 4, row_rect.y + 7))

            map_str = _map_size_str(data)
            map_surf = self.small_font.render(map_str, True, themes.MUTED_TEXT)
            surface.blit(map_surf, (self._LIST_X + 310, row_rect.y + 7))

            stars_str = _stars(data.get("difficulty_stars"))
            stars_surf = self.small_font.render(stars_str, True, themes.SELECTION)
            surface.blit(stars_surf, (self._LIST_X + 390, row_rect.y + 7))

            blue, red = _unit_counts(data)
            forces_str = f"B{blue}/R{red}" if blue or red else "?"
            forces_surf = self.small_font.render(forces_str, True, themes.MUTED_TEXT)
            surface.blit(forces_surf, (self._LIST_X + 450, row_rect.y + 7))

        # Scroll indicator
        total = len(self._scenarios)
        if total > self._VISIBLE_ROWS:
            bar_h = max(20, int(h * self._VISIBLE_ROWS / total))
            bar_y = self._LIST_Y + int(
                (self._scroll / max(1, total - self._VISIBLE_ROWS))
                * (self._VISIBLE_ROWS * self._ROW_H - bar_h)
            )
            sb_x = self._LIST_X + self._LIST_W + 4
            pygame.draw.rect(surface, themes.PANEL_BORDER,
                             pygame.Rect(sb_x, self._LIST_Y, 6, self._VISIBLE_ROWS * self._ROW_H))
            pygame.draw.rect(surface, themes.MUTED_TEXT,
                             pygame.Rect(sb_x, bar_y, 6, bar_h), border_radius=3)

        # Detail panel
        self._draw_detail(surface)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _move_selection(self, delta: int) -> None:
        n = len(self._scenarios)
        if n == 0:
            return
        self._selected = max(0, min(n - 1, self._selected + delta))
        # Keep selected in view
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + self._VISIBLE_ROWS:
            self._scroll = self._selected - self._VISIBLE_ROWS + 1

    def _confirm(self) -> dict | None:
        if not self._scenarios:
            return None
        data = self._scenarios[self._selected]
        return {
            "scenario": data["_id"],
            "mode": "scenario",
            "difficulty": _stars(data.get("difficulty_stars")),
        }

    def _draw_detail(self, surface: pygame.Surface) -> None:
        if not self._scenarios:
            return
        data = self._scenarios[self._selected]

        dx = self._DETAIL_X
        dy = self._DETAIL_Y
        dw = surface.get_width() - dx - 20
        dh = surface.get_height() - dy - 20

        detail_rect = pygame.Rect(dx, dy, dw, dh)
        pygame.draw.rect(surface, (28, 32, 42), detail_rect, border_radius=6)
        pygame.draw.rect(surface, themes.SELECTION, detail_rect, 1, border_radius=6)

        y = dy + 14
        lh = 22

        # Title
        t = self.font.render(data.get("title", data["_id"])[:24], True, themes.SELECTION)
        surface.blit(t, t.get_rect(centerx=dx + dw // 2, y=y))
        y += lh + 8

        # Difficulty stars
        stars_str = _stars(data.get("difficulty_stars"))
        stars_surf = self.small_font.render(f"Difficulty: {stars_str}", True, themes.TEXT)
        surface.blit(stars_surf, (dx + 12, y))
        y += lh

        # Map size
        ms = _map_size_str(data)
        ms_surf = self.small_font.render(f"Map: {ms}", True, themes.TEXT)
        surface.blit(ms_surf, (dx + 12, y))
        y += lh

        # Unit counts
        blue, red = _unit_counts(data)
        if blue or red:
            uc_surf = self.small_font.render(f"Blue units: {blue}   Red units: {red}", True, themes.TEXT)
            surface.blit(uc_surf, (dx + 12, y))
            y += lh

        # Objectives
        objs = data.get("objectives", [])
        if objs:
            obj_surf = self.small_font.render(f"Objectives: {len(objs)}", True, themes.TEXT)
            surface.blit(obj_surf, (dx + 12, y))
            y += lh

        y += 8
        pygame.draw.line(surface, themes.PANEL_BORDER, (dx + 12, y), (dx + dw - 12, y))
        y += 10

        # Description / briefing
        desc = _description(data)
        if desc:
            words = desc.split()
            line_buf: list[str] = []
            max_chars = max(1, dw // 7)
            for word in words:
                candidate = " ".join(line_buf + [word])
                if len(candidate) > max_chars and line_buf:
                    line_surf = self.small_font.render(" ".join(line_buf), True, themes.MUTED_TEXT)
                    surface.blit(line_surf, (dx + 12, y))
                    y += 18
                    line_buf = [word]
                else:
                    line_buf.append(word)
            if line_buf:
                line_surf = self.small_font.render(" ".join(line_buf), True, themes.MUTED_TEXT)
                surface.blit(line_surf, (dx + 12, y))
                y += 18

        y += 10
        # Enter to select hint
        hint = self.small_font.render("ENTER to start", True, themes.SELECTION)
        surface.blit(hint, hint.get_rect(centerx=dx + dw // 2, y=min(y, dy + dh - 30)))
