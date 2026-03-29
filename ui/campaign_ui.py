"""G4: Campaign progression UI."""

from __future__ import annotations

from pathlib import Path

import pygame

from core.campaign import STANDARD_CAMPAIGN, CampaignState
from core.units import Side
from . import themes
from .bitmap_font import BitmapFont

_SAVE_PATH = Path.home() / ".kriegsspiel" / "campaign.json"

_DIFFICULTY_MAP = {
    "tutorial":       "easy",
    "skirmish_small": "easy",
    "assault_on_hill": "medium",
    "full_battle":    "hard",
    "mockern_1813":   "hard",
    "ligny_1815":     "hard",
}


def _load_or_new() -> CampaignState:
    if _SAVE_PATH.exists():
        try:
            return CampaignState.load(str(_SAVE_PATH), STANDARD_CAMPAIGN)
        except Exception:
            pass
    return CampaignState(campaign=STANDARD_CAMPAIGN)


class CampaignUI:
    """Campaign overview screen showing battle sequence.

    :meth:`handle_event` returns:
    - ``"start_battle"`` when the player starts the next battle
    - ``"back"`` to return to the main menu
    - ``None`` otherwise
    """

    _BOX_W = 160
    _BOX_H = 110
    _BOX_GAP = 24
    _BOX_Y = 240

    def __init__(
        self,
        font: BitmapFont,
        small_font: BitmapFont,
        campaign_state: CampaignState | None = None,
    ) -> None:
        self.font = font
        self.small_font = small_font
        self.state = campaign_state if campaign_state is not None else _load_or_new()
        self._start_rect = pygame.Rect(0, 0, 0, 0)
        self._back_rect = pygame.Rect(0, 0, 0, 0)
        self._reset_rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_scenario(self) -> str:
        s = self.state.current_scenario
        return s.scenario_id if s else ""

    @property
    def current_difficulty(self) -> str:
        return _DIFFICULTY_MAP.get(self.current_scenario, "medium")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            if event.key == pygame.K_RETURN and not self.state.is_complete:
                return "start_battle"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self._back_rect.collidepoint(pos):
                return "back"
            if self._start_rect.collidepoint(pos) and not self.state.is_complete:
                return "start_battle"
            if self._reset_rect.collidepoint(pos):
                self.state = CampaignState(campaign=STANDARD_CAMPAIGN)

        return None

    def draw(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        surface.fill(themes.PANEL_BG)

        # Title
        title = self.font.render("CAMPAIGN", True, themes.SELECTION)
        surface.blit(title, title.get_rect(centerx=w // 2, y=18))

        sub = self.small_font.render(
            "Carry your forces through linked battles", True, themes.MUTED_TEXT
        )
        surface.blit(sub, sub.get_rect(centerx=w // 2, y=50))

        # Status line
        cur = self.state.current_scenario
        if self.state.is_complete:
            winner = self.state.campaign_winner
            if winner is Side.BLUE:
                status_str = "Campaign complete - BLUE WINS"
            elif winner is Side.RED:
                status_str = "Campaign complete - RED WINS"
            else:
                status_str = "Campaign complete - DRAW"
            status_color = themes.SELECTION
        else:
            idx = self.state.current_scenario_index
            status_str = f"Battle {idx + 1} of {len(self.state.campaign)}: {cur.title if cur else '?'}"
            status_color = themes.TEXT

        status_surf = self.small_font.render(status_str, True, status_color)
        surface.blit(status_surf, status_surf.get_rect(centerx=w // 2, y=76))

        # Score line
        score_str = f"Record: {self.state.blue_wins}W - {self.state.red_wins}L"
        score_surf = self.small_font.render(score_str, True, themes.MUTED_TEXT)
        surface.blit(score_surf, score_surf.get_rect(centerx=w // 2, y=100))

        # Battle boxes
        n = len(self.state.campaign)
        total_w = n * self._BOX_W + (n - 1) * self._BOX_GAP
        start_x = max(20, (w - total_w) // 2)

        for i, scenario in enumerate(self.state.campaign):
            bx = start_x + i * (self._BOX_W + self._BOX_GAP)
            by = self._BOX_Y
            box_rect = pygame.Rect(bx, by, self._BOX_W, self._BOX_H)

            result = self.state.scenario_result(scenario.scenario_id)
            is_current = i == self.state.current_scenario_index
            is_future = i > self.state.current_scenario_index

            # Box fill
            if is_future:
                bg_color = (25, 28, 36)
                border_color = (50, 55, 65)
                text_color = (80, 85, 95)
            elif is_current:
                bg_color = (40, 55, 80)
                border_color = themes.SELECTION
                text_color = themes.TEXT
            else:
                bg_color = (30, 40, 55)
                border_color = themes.PANEL_BORDER
                text_color = themes.MUTED_TEXT

            pygame.draw.rect(surface, bg_color, box_rect, border_radius=6)
            border_w = 2 if is_current else 1
            pygame.draw.rect(surface, border_color, box_rect, border_w, border_radius=6)

            # Battle number
            num_surf = self.small_font.render(f"#{i + 1}", True, border_color)
            surface.blit(num_surf, (bx + 8, by + 8))

            # Title (two lines max)
            title_words = scenario.title.split()
            lines: list[str] = []
            line: list[str] = []
            for word in title_words:
                candidate = " ".join(line + [word])
                if len(candidate) > 14 and line:
                    lines.append(" ".join(line))
                    line = [word]
                else:
                    line.append(word)
            if line:
                lines.append(" ".join(line))

            ty = by + 28
            for ln in lines[:2]:
                ln_surf = self.small_font.render(ln, True, text_color)
                surface.blit(ln_surf, ln_surf.get_rect(centerx=bx + self._BOX_W // 2, y=ty))
                ty += 16

            # Result badge
            if result is not None:
                if result.winner is Side.BLUE:
                    badge_text = "W"
                    badge_color = (40, 180, 80)
                elif result.winner is Side.RED:
                    badge_text = "L"
                    badge_color = (180, 60, 60)
                else:
                    badge_text = "D"
                    badge_color = (130, 130, 70)
                badge_rect = pygame.Rect(bx + self._BOX_W - 30, by + self._BOX_H - 30, 24, 24)
                pygame.draw.rect(surface, badge_color, badge_rect, border_radius=4)
                badge_surf = self.small_font.render(badge_text, True, themes.TEXT)
                surface.blit(badge_surf, badge_surf.get_rect(center=badge_rect.center))

            # Lock icon for future battles
            if is_future:
                lock_surf = self.small_font.render("LOCKED", True, (60, 65, 75))
                surface.blit(lock_surf, lock_surf.get_rect(centerx=bx + self._BOX_W // 2, y=by + self._BOX_H - 22))

            # Arrow connector
            if i < n - 1:
                arrow_x = bx + self._BOX_W + self._BOX_GAP // 2
                arrow_y = by + self._BOX_H // 2
                arrow_color = themes.PANEL_BORDER if is_future else themes.MUTED_TEXT
                pygame.draw.line(surface, arrow_color, (bx + self._BOX_W + 2, arrow_y), (arrow_x + 8, arrow_y), 2)
                # Arrow head
                pygame.draw.polygon(surface, arrow_color, [
                    (arrow_x + 8, arrow_y - 5),
                    (arrow_x + 8, arrow_y + 5),
                    (arrow_x + 14, arrow_y),
                ])

        # Description of current scenario
        if cur and not self.state.is_complete:
            desc_y = self._BOX_Y + self._BOX_H + 30
            desc_surf = self.small_font.render(cur.description[:80], True, themes.MUTED_TEXT)
            surface.blit(desc_surf, desc_surf.get_rect(centerx=w // 2, y=desc_y))

        # Buttons
        btn_y = self._BOX_Y + self._BOX_H + 70

        back_rect = pygame.Rect(w // 2 - 260, btn_y, 120, 40)
        self._back_rect = back_rect
        pygame.draw.rect(surface, (50, 60, 80), back_rect, border_radius=6)
        pygame.draw.rect(surface, themes.PANEL_BORDER, back_rect, 1, border_radius=6)
        back_surf = self.small_font.render("< BACK", True, themes.TEXT)
        surface.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        if not self.state.is_complete:
            start_rect = pygame.Rect(w // 2 - 110, btn_y, 220, 40)
            self._start_rect = start_rect
            pygame.draw.rect(surface, (40, 100, 60), start_rect, border_radius=6)
            pygame.draw.rect(surface, themes.SELECTION, start_rect, 1, border_radius=6)
            start_surf = self.font.render("START BATTLE", True, themes.SELECTION)
            surface.blit(start_surf, start_surf.get_rect(center=start_rect.center))
        else:
            # New campaign button
            reset_rect = pygame.Rect(w // 2 - 110, btn_y, 220, 40)
            self._reset_rect = reset_rect
            pygame.draw.rect(surface, (60, 40, 80), reset_rect, border_radius=6)
            pygame.draw.rect(surface, themes.SELECTION, reset_rect, 1, border_radius=6)
            reset_surf = self.small_font.render("NEW CAMPAIGN", True, themes.SELECTION)
            surface.blit(reset_surf, reset_surf.get_rect(center=reset_rect.center))

        # Hint
        hint = self.small_font.render("ENTER = Start   ESC = Back", True, themes.MUTED_TEXT)
        surface.blit(hint, hint.get_rect(centerx=w // 2, y=btn_y + 50))
