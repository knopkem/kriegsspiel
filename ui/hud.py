"""HUD composition helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from .combat_log import CombatLogPanel
from .minimap import Minimap
from .order_panel import OrderPanel
from .unit_detail import UnitDetailPanel


@dataclass(slots=True)
class HUD:
    font: pygame.font.Font
    small_font: pygame.font.Font
    order_panel: OrderPanel = field(init=False)
    unit_detail: UnitDetailPanel = field(init=False)
    combat_log: CombatLogPanel = field(init=False)
    minimap: Minimap = field(init=False)

    def __post_init__(self) -> None:
        self.order_panel = OrderPanel(self.font, self.small_font)
        self.unit_detail = UnitDetailPanel(self.font, self.small_font)
        self.combat_log = CombatLogPanel(self.font, self.small_font)
        self.minimap = Minimap()
