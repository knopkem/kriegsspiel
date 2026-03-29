"""Animation framework for visual combat and movement effects."""

from __future__ import annotations
import time
import math
from dataclasses import dataclass, field

import pygame


@dataclass
class Animation:
    """Base animation with timing."""
    duration: float          # seconds
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def progress(self) -> float:
        """0.0 → 1.0"""
        return min(1.0, self.elapsed / max(0.001, self.duration))

    @property
    def is_done(self) -> bool:
        return self.elapsed >= self.duration


@dataclass
class RangedFireAnimation(Animation):
    from_pos: tuple = (0, 0)   # screen coords
    to_pos: tuple = (0, 0)
    is_artillery: bool = False


@dataclass
class MeleeAnimation(Animation):
    hex_pos: tuple = (0, 0)    # screen coords of combat hex


@dataclass
class DamageNumberAnimation(Animation):
    pos: tuple = (0, 0)        # screen coords (start)
    text: str = ""
    colour: tuple = (220, 60, 60)


@dataclass
class CascadeRingAnimation(Animation):
    hex_pos: tuple = (0, 0)
    max_radius: float = 60.0


@dataclass
class UnitMoveAnimation(Animation):
    unit_id: str = ""
    from_pos: tuple = (0, 0)
    to_pos: tuple = (0, 0)


class AnimationManager:
    def __init__(self, speed_multiplier: float = 1.0):
        self._animations: list[Animation] = []
        self.speed_multiplier = speed_multiplier

    def add(self, anim: Animation) -> None:
        self._animations.append(anim)

    def update(self) -> None:
        """Remove completed animations."""
        self._animations = [a for a in self._animations if not a.is_done]

    @property
    def is_animating(self) -> bool:
        return bool(self._animations)

    def skip_all(self) -> None:
        """Immediately complete all animations."""
        self._animations.clear()

    def set_speed(self, multiplier: float) -> None:
        self.speed_multiplier = multiplier
        now = time.time()
        for anim in self._animations:
            remaining = anim.duration - anim.elapsed
            anim.start_time = now - anim.duration + (remaining / max(0.001, multiplier))

    def draw(self, surface: pygame.Surface, camera, font) -> None:
        """Draw all active animations."""
        for anim in self._animations:
            if isinstance(anim, UnitMoveAnimation):
                continue
            if isinstance(anim, RangedFireAnimation):
                self._draw_ranged(surface, anim)
            elif isinstance(anim, MeleeAnimation):
                self._draw_melee(surface, anim)
            elif isinstance(anim, DamageNumberAnimation):
                self._draw_damage_number(surface, anim, font)
            elif isinstance(anim, CascadeRingAnimation):
                self._draw_cascade_ring(surface, anim)

    def animated_unit_centers(self) -> dict[str, tuple[int, int]]:
        centers: dict[str, tuple[int, int]] = {}
        for anim in self._animations:
            if not isinstance(anim, UnitMoveAnimation):
                continue
            progress = anim.progress
            sx, sy = anim.from_pos
            tx, ty = anim.to_pos
            centers[anim.unit_id] = (
                int(sx + (tx - sx) * progress),
                int(sy + (ty - sy) * progress),
            )
        return centers

    def _draw_ranged(self, surface: pygame.Surface, anim: RangedFireAnimation) -> None:
        alpha = 1.0 - anim.progress
        if alpha <= 0:
            return
        colour = (255, 200, 50) if not anim.is_artillery else (255, 120, 30)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        a = int(alpha * 200)
        pygame.draw.line(overlay, (*colour, a), anim.from_pos, anim.to_pos, 2)
        burst_r = int(4 + anim.progress * 8)
        pygame.draw.circle(overlay, (*colour, max(0, a - 50)), anim.to_pos, burst_r, 2)
        surface.blit(overlay, (0, 0))

    def _draw_melee(self, surface: pygame.Surface, anim: MeleeAnimation) -> None:
        alpha = 1.0 - anim.progress * 0.7
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        a = int(alpha * 220)
        cx, cy = anim.hex_pos
        size = 12
        pygame.draw.line(overlay, (255, 255, 100, a), (cx - size, cy - size), (cx + size, cy + size), 3)
        pygame.draw.line(overlay, (255, 255, 100, a), (cx + size, cy - size), (cx - size, cy + size), 3)
        surface.blit(overlay, (0, 0))

    def _draw_damage_number(self, surface: pygame.Surface, anim: DamageNumberAnimation, font) -> None:
        rise = anim.progress * 30
        alpha = 1.0 - max(0.0, (anim.progress - 0.5) * 2)
        if alpha <= 0:
            return
        x, y = anim.pos
        draw_y = int(y - rise)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        a = int(alpha * 255)
        text_surf = font.render(anim.text, True, anim.colour)
        text_surf.set_alpha(a)
        overlay.blit(text_surf, (x, draw_y))
        surface.blit(overlay, (0, 0))

    def _draw_cascade_ring(self, surface: pygame.Surface, anim: CascadeRingAnimation) -> None:
        r = int(anim.progress * anim.max_radius)
        alpha = int((1.0 - anim.progress) * 150)
        if r < 2 or alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (220, 60, 60, alpha), anim.hex_pos, r, 3)
        surface.blit(overlay, (0, 0))
