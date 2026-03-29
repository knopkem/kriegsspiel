"""G3: Quick Battle configuration UI."""

from __future__ import annotations

import pygame

from . import themes
from .bitmap_font import BitmapFont

# Option definitions
_MAP_SIZES = [
    ("Small",   "small",  "20x16"),
    ("Medium",  "medium", "35x28"),
    ("Large",   "large",  "55x45"),
]

_FORCE_TYPES = [
    ("Infantry", "infantry"),
    ("Cavalry",  "cavalry"),
    ("Balanced", "balanced"),
    ("Heavy",    "heavy"),
]

_DIFFICULTIES = [
    ("Easy",       "easy"),
    ("Medium",     "medium"),
    ("Hard",       "hard"),
    ("Historical", "historical"),
]

# Approximate unit counts per size/force combination
_UNIT_PREVIEWS: dict[str, dict[str, int]] = {
    "small":  {"infantry": 5, "cavalry": 4, "balanced": 6, "heavy": 5},
    "medium": {"infantry": 8, "cavalry": 7, "balanced": 10, "heavy": 9},
    "large":  {"infantry": 13, "cavalry": 11, "balanced": 15, "heavy": 13},
}


class QuickBattle:
    """Configuration screen for a procedurally generated quick battle.

    :meth:`handle_event` returns:
    - a config ``dict`` when START is pressed
    - the string ``"back"`` when BACK is pressed
    - ``None`` while the player is still choosing
    """

    _W = 1280
    _H = 800
    _COL_W = 440           # width of option column
    _ROW_H = 60
    _ARROW_W = 36
    _OPTION_AREA_W = 280

    def __init__(self, font: BitmapFont, small_font: BitmapFont) -> None:
        self.font = font
        self.small_font = small_font
        self._size_idx = 1          # Medium default
        self._force_idx = 2         # Balanced default
        self._diff_idx = 1          # Medium default
        self._focus_idx = 0
        self._start_rect = pygame.Rect(0, 0, 0, 0)
        self._back_rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_rects: list[tuple[pygame.Rect, str, int]] = []  # (rect, axis, delta)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> dict | str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key == pygame.K_RETURN:
                return self._build_config()
            if event.key == pygame.K_LEFT:
                self._cycle(self._focused_axis(), -1)
            elif event.key == pygame.K_RIGHT:
                self._cycle(self._focused_axis(), 1)
            elif event.key == pygame.K_UP:
                self._focus_idx = (self._focus_idx - 1) % 3
            elif event.key == pygame.K_DOWN:
                self._focus_idx = (self._focus_idx + 1) % 3

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._start_rect.collidepoint(pos):
                return self._build_config()
            if self._back_rect.collidepoint(pos):
                return "back"
            for rect, axis, delta in self._arrow_rects:
                if rect.collidepoint(pos):
                    self._cycle(axis, delta)
                    break

        return None

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        surface.fill(themes.PANEL_BG)

        # Reset interactive rects
        self._arrow_rects = []

        # Title
        title = self.font.render("QUICK BATTLE", True, themes.SELECTION)
        surface.blit(title, title.get_rect(centerx=w // 2, y=20))

        subtitle = self.small_font.render("Configure your forces and engage", True, themes.MUTED_TEXT)
        surface.blit(subtitle, subtitle.get_rect(centerx=w // 2, y=52))

        # Three option rows
        rows = [
            ("MAP SIZE",   _MAP_SIZES,    "size",  self._size_idx),
            ("FORCE TYPE", _FORCE_TYPES,  "force", self._force_idx),
            ("DIFFICULTY", _DIFFICULTIES, "diff",  self._diff_idx),
        ]

        start_y = 130
        row_spacing = 130
        center_x = w // 2

        for row_i, (label, options, axis, cur_idx) in enumerate(rows):
            ry = start_y + row_i * row_spacing

            # Row background
            row_rect = pygame.Rect(center_x - 280, ry - 10, 560, self._ROW_H + 50)
            pygame.draw.rect(surface, (30, 34, 44), row_rect, border_radius=6)
            border = themes.SELECTION if row_i == self._focus_idx else themes.PANEL_BORDER
            pygame.draw.rect(surface, border, row_rect, 1, border_radius=6)

            # Row label
            lbl_surf = self.small_font.render(label, True, themes.MUTED_TEXT)
            surface.blit(lbl_surf, lbl_surf.get_rect(centerx=center_x, y=ry - 4))

            # Left arrow
            left_rect = pygame.Rect(center_x - 200, ry + 22, self._ARROW_W, self._ARROW_W)
            self._draw_arrow_btn(surface, left_rect, "<")
            self._arrow_rects.append((left_rect, axis, -1))

            # Right arrow
            right_rect = pygame.Rect(center_x + 200 - self._ARROW_W, ry + 22, self._ARROW_W, self._ARROW_W)
            self._draw_arrow_btn(surface, right_rect, ">")
            self._arrow_rects.append((right_rect, axis, 1))

            # Current option display
            opt_rect = pygame.Rect(center_x - 150, ry + 16, 300, self._ARROW_W + 8)
            pygame.draw.rect(surface, (50, 60, 85), opt_rect, border_radius=4)
            pygame.draw.rect(surface, themes.SELECTION, opt_rect, 1, border_radius=4)

            opt_name = options[cur_idx][0]
            opt_surf = self.font.render(opt_name, True, themes.TEXT)
            surface.blit(opt_surf, opt_surf.get_rect(center=opt_rect.center))

            # Sub-label (map dimensions etc.)
            if axis == "size":
                sub = _MAP_SIZES[self._size_idx][2]
                sub_surf = self.small_font.render(sub, True, themes.MUTED_TEXT)
                surface.blit(sub_surf, sub_surf.get_rect(centerx=center_x, y=ry + 68))

            # Dots for position indicator
            n_opts = len(options)
            dot_y = ry + 74
            dot_spacing = 12
            total_dot_w = n_opts * dot_spacing
            dot_start_x = center_x - total_dot_w // 2
            for di in range(n_opts):
                dot_color = themes.SELECTION if di == cur_idx else themes.PANEL_BORDER
                pygame.draw.circle(surface, dot_color, (dot_start_x + di * dot_spacing + 4, dot_y + 4), 4)

        # Unit count preview
        size_key = _MAP_SIZES[self._size_idx][1]
        force_key = _FORCE_TYPES[self._force_idx][1]
        est = _UNIT_PREVIEWS.get(size_key, {}).get(force_key, "?")
        preview_y = start_y + len(rows) * row_spacing + 10
        preview_text = self.small_font.render(
            f"Estimated units per side: ~{est}", True, themes.MUTED_TEXT
        )
        surface.blit(preview_text, preview_text.get_rect(centerx=w // 2, y=preview_y))

        # Buttons
        btn_y = preview_y + 36
        start_rect = pygame.Rect(w // 2 - 100, btn_y, 200, 40)
        self._start_rect = start_rect
        pygame.draw.rect(surface, (40, 100, 60), start_rect, border_radius=6)
        pygame.draw.rect(surface, themes.SELECTION, start_rect, 1, border_radius=6)
        start_surf = self.font.render("START", True, themes.SELECTION)
        surface.blit(start_surf, start_surf.get_rect(center=start_rect.center))

        back_rect = pygame.Rect(w // 2 - 240, btn_y, 120, 40)
        self._back_rect = back_rect
        pygame.draw.rect(surface, (50, 60, 80), back_rect, border_radius=6)
        pygame.draw.rect(surface, themes.PANEL_BORDER, back_rect, 1, border_radius=6)
        back_surf = self.small_font.render("< BACK", True, themes.TEXT)
        surface.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # Keyboard hint
        hint = self.small_font.render("ENTER = Start   ESC = Back", True, themes.MUTED_TEXT)
        surface.blit(hint, hint.get_rect(centerx=w // 2, y=btn_y + 50))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _draw_arrow_btn(self, surface: pygame.Surface, rect: pygame.Rect, symbol: str) -> None:
        pygame.draw.rect(surface, (45, 55, 75), rect, border_radius=4)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1, border_radius=4)
        sym_surf = self.font.render(symbol, True, themes.TEXT)
        surface.blit(sym_surf, sym_surf.get_rect(center=rect.center))

    def _cycle(self, axis: str, delta: int) -> None:
        if axis == "size":
            self._size_idx = (self._size_idx + delta) % len(_MAP_SIZES)
        elif axis == "force":
            self._force_idx = (self._force_idx + delta) % len(_FORCE_TYPES)
        elif axis == "diff":
            self._diff_idx = (self._diff_idx + delta) % len(_DIFFICULTIES)

    def _build_config(self) -> dict:
        return {
            "size":       _MAP_SIZES[self._size_idx][1],
            "force":      _FORCE_TYPES[self._force_idx][1],
            "difficulty": _DIFFICULTIES[self._diff_idx][1],
        }

    def _focused_axis(self) -> str:
        return ("size", "force", "diff")[self._focus_idx]
