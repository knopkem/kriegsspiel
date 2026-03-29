"""HUD composition helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from .combat_log import CombatLog
from .minimap import Minimap
from .order_panel import OrderPanel
from .unit_detail import UnitDetail


@dataclass(slots=True)
class HUD:
    font: pygame.font.Font
    small_font: pygame.font.Font
    order_panel: OrderPanel = field(init=False)
    unit_detail: UnitDetail = field(init=False)
    combat_log: CombatLog = field(init=False)
    minimap: Minimap = field(init=False)

    def __post_init__(self) -> None:
        self.order_panel = OrderPanel(self.font, self.small_font)
        self.unit_detail = UnitDetail()
        self.combat_log = CombatLog()
        self.minimap = Minimap()
