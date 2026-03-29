"""Left-side unit detail panel with visual stat bars."""

from __future__ import annotations

import pygame

from core.units import FatigueLevel, FacingDirection, Formation, MoraleState, Unit, UnitType
from . import themes


def _bar(surface, x, y, w, h, ratio, filled_colour, empty_colour=(40, 40, 40)):
    pygame.draw.rect(surface, empty_colour, (x, y, w, h))
    filled_w = int(w * max(0.0, min(1.0, ratio)))
    if filled_w > 0:
        pygame.draw.rect(surface, filled_colour, (x, y, filled_w, h))


class UnitDetail:
    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        unit: Unit | None,
        font,
        small_font,
    ) -> None:
        pygame.draw.rect(surface, themes.PANEL_BG, rect)
        pygame.draw.rect(surface, themes.PANEL_BORDER, rect, 1)
        title = font.render("Selected Unit", True, themes.TEXT)
        surface.blit(title, (rect.x + 8, rect.y + 6))

        if unit is None:
            msg = small_font.render("No unit selected", True, themes.MUTED_TEXT)
            surface.blit(msg, (rect.x + 8, rect.y + 32))
            return

        x, y = rect.x + 8, rect.y + 28
        lh = 16          # line height
        bar_h = 6        # stat bar height
        bar_gap = 10     # space consumed by bar + gap below
        bar_w = rect.width - 20

        def text(label, colour=themes.TEXT):
            nonlocal y
            surface.blit(small_font.render(label, True, colour), (x, y))
            y += lh

        def bar_row(label, ratio, filled_col):
            nonlocal y
            surface.blit(small_font.render(label, True, themes.TEXT), (x, y))
            y += lh - 2
            _bar(surface, x, y, bar_w, bar_h, ratio, filled_col)
            y += bar_gap

        def separator():
            nonlocal y
            y += 4

        # --- Identity ---
        text(unit.name, themes.SELECTION)
        text(f"Type: {unit.unit_type.value.capitalize()}")
        text(f"Formation: {unit.formation.value}")

        separator()

        # --- HP ---
        hp_ratio = unit.hit_points / max(1, unit.max_hit_points)
        hp_col = (60, 180, 60) if hp_ratio > 0.6 else (220, 200, 40) if hp_ratio > 0.3 else (200, 50, 50)
        bar_row(f"HP: {unit.hit_points}/{unit.max_hit_points}", hp_ratio, hp_col)

        # --- Strength ---
        text(f"Str: {unit.current_strength}/{unit.max_strength}")

        separator()

        # --- Morale ---
        morale_ratios = {
            MoraleState.STEADY: 1.0, MoraleState.SHAKEN: 0.67,
            MoraleState.ROUTING: 0.33, MoraleState.BROKEN: 0.05,
        }
        morale_cols = {
            MoraleState.STEADY: (50, 120, 220), MoraleState.SHAKEN: (210, 150, 30),
            MoraleState.ROUTING: (200, 60, 60), MoraleState.BROKEN: (100, 20, 20),
        }
        m_ratio = morale_ratios.get(unit.morale_state, 0.5)
        m_col = morale_cols.get(unit.morale_state, themes.TEXT)
        bar_row(f"Morale: {unit.morale_state.value}", m_ratio, m_col)

        # --- Fatigue ---
        fat_ratio = unit.fatigue / 100.0
        fat_col = (60, 180, 60) if fat_ratio < 0.3 else (220, 200, 40) if fat_ratio < 0.6 else (200, 50, 50)
        bar_row(f"Fatigue: {unit.fatigue}/100", fat_ratio, fat_col)

        separator()

        # --- Ammo (only if unit uses ammo) ---
        if unit.max_ammo > 0:
            ammo_ratio = unit.ammo / max(1, unit.max_ammo)
            ammo_col = (80, 160, 220) if ammo_ratio > 0.4 else (220, 200, 40) if ammo_ratio > 0.1 else (200, 60, 60)
            bar_row(f"Ammo: {unit.ammo}/{unit.max_ammo}", ammo_ratio, ammo_col)

        # --- Facing & position ---
        text(f"Facing: {unit.facing.value}")
        pos_text = f"Pos: {unit.position.q},{unit.position.r}" if unit.position else "Pos: -"
        text(pos_text, themes.MUTED_TEXT)

        # --- Status badges ---
        badges: list[str] = []
        if unit.is_entrenched:
            badges.append("Entrenched")
        if getattr(unit, "last_stand_active", False):
            badges.append("Last Stand!")
        if unit.unit_type is UnitType.COMMANDER and unit.commander_ability_uses > 0:
            badges.append(f"Ability x{unit.commander_ability_uses}")
        if badges:
            separator()
            text(" | ".join(badges), themes.SELECTION)


