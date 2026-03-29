"""Self-dismissing notification toast system."""

from __future__ import annotations

from dataclasses import dataclass, field
import time

import pygame

from . import themes


@dataclass
class Toast:
    message: str
    created_at: float = field(default_factory=time.time)
    duration: float = 3.0
    colour: tuple = field(default_factory=lambda: themes.SELECTION)

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.duration

    def alpha(self) -> int:
        remaining = self.duration - (time.time() - self.created_at)
        if remaining < 0.5:
            return int(255 * remaining / 0.5)
        return 255


@dataclass
class ToastManager:
    toasts: list[Toast] = field(default_factory=list)

    def add(self, message: str, colour: tuple = themes.SELECTION, duration: float = 3.0) -> None:
        self.toasts.append(Toast(message, colour=colour, duration=duration))
        if len(self.toasts) > 4:
            self.toasts = self.toasts[-4:]

    def update(self) -> None:
        self.toasts = [t for t in self.toasts if not t.is_expired()]

    def draw(self, surface: pygame.Surface, font) -> None:
        self.update()
        w = surface.get_width()
        y = 40
        for toast in reversed(self.toasts):
            text = font.render(toast.message, True, (20, 20, 20))
            tw, th = text.get_width() + 20, text.get_height() + 10
            tx = w // 2 - tw // 2
            toast_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
            alpha = toast.alpha()
            r, g, b = toast.colour[:3]
            pygame.draw.rect(toast_surf, (r, g, b, min(200, alpha)), (0, 0, tw, th), border_radius=4)
            toast_surf.blit(text, (10, 5))
            surface.blit(toast_surf, (tx, y))
            y += th + 4
