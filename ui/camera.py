"""Camera transforms for pointy-top hex maps."""

from __future__ import annotations

from dataclasses import dataclass
import math

from core.map import HexCoord


@dataclass(slots=True)
class Camera:
    width: int
    height: int
    zoom: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    base_hex_size: float = 28.0

    @property
    def hex_size(self) -> float:
        return self.base_hex_size * self.zoom

    def pan(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy

    def center_on(self, coord: "HexCoord") -> None:
        """Pan so that coord is centred on screen."""
        wx, wy = self.axial_to_world(coord)
        self.offset_x = self.width / 2 - wx
        self.offset_y = self.height / 2 - wy

    def zoom_at(self, factor: float, anchor: tuple[int, int]) -> None:
        old_size = self.hex_size
        self.zoom = max(0.5, min(2.5, self.zoom * factor))
        new_size = self.hex_size
        scale = new_size / max(old_size, 1e-6)
        ax, ay = anchor
        self.offset_x = ax - (ax - self.offset_x) * scale
        self.offset_y = ay - (ay - self.offset_y) * scale

    def axial_to_world(self, coord: HexCoord) -> tuple[float, float]:
        size = self.hex_size
        x = size * math.sqrt(3) * (coord.q + coord.r / 2)
        y = size * 1.5 * coord.r
        return x, y

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return int(x + self.offset_x), int(y + self.offset_y)

    def axial_to_screen(self, coord: HexCoord) -> tuple[int, int]:
        return self.world_to_screen(*self.axial_to_world(coord))

    def screen_to_world(self, x: float, y: float) -> tuple[float, float]:
        return x - self.offset_x, y - self.offset_y

    def screen_to_axial(self, pos: tuple[int, int]) -> HexCoord:
        px, py = self.screen_to_world(*pos)
        size = self.hex_size
        q = ((math.sqrt(3) / 3) * px - (1 / 3) * py) / size
        r = ((2 / 3) * py) / size
        return _hex_round(q, r)


def _hex_round(q: float, r: float) -> HexCoord:
    x = q
    z = r
    y = -x - z

    rx = round(x)
    ry = round(y)
    rz = round(z)

    x_diff = abs(rx - x)
    y_diff = abs(ry - y)
    z_diff = abs(rz - z)

    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry

    return HexCoord(int(rx), int(rz))

