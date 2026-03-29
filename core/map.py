"""Hex-grid battlefield model with terrain, line of sight, and pathfinding."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import heapq
import math
from typing import Callable, Iterable, Mapping, Sequence


class TerrainType(StrEnum):
    OPEN = "open"
    ROAD = "road"
    FOREST = "forest"
    HILL = "hill"
    RIVER = "river"
    VILLAGE = "village"
    MARSH = "marsh"
    FORTIFICATION = "fortification"


DEFAULT_TERRAIN_COSTS: dict[TerrainType, float] = {
    TerrainType.OPEN: 1.0,
    TerrainType.ROAD: 0.8,
    TerrainType.FOREST: 1.7,
    TerrainType.HILL: 1.4,
    TerrainType.RIVER: math.inf,
    TerrainType.VILLAGE: 1.3,
    TerrainType.MARSH: 2.2,
    TerrainType.FORTIFICATION: 1.5,
}

TERRAIN_LOS_OBSTRUCTION: dict[TerrainType, float] = {
    TerrainType.OPEN: 0.0,
    TerrainType.ROAD: 0.0,
    TerrainType.FOREST: 18.0,
    TerrainType.HILL: 0.0,
    TerrainType.RIVER: 0.0,
    TerrainType.VILLAGE: 10.0,
    TerrainType.MARSH: 3.0,
    TerrainType.FORTIFICATION: 12.0,
}

TERRAIN_FROM_CHAR: dict[str, TerrainType] = {
    ".": TerrainType.OPEN,
    "r": TerrainType.ROAD,
    "f": TerrainType.FOREST,
    "h": TerrainType.HILL,
    "w": TerrainType.RIVER,
    "v": TerrainType.VILLAGE,
    "m": TerrainType.MARSH,
    "#": TerrainType.FORTIFICATION,
}

HEX_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)

TerrainCostResolver = Mapping[TerrainType, float] | Callable[["HexCoord", "HexCell"], float]


@dataclass(frozen=True, order=True)
class HexCoord:
    """Axial hex coordinate."""

    q: int
    r: int

    def neighbors(self) -> tuple["HexCoord", ...]:
        return tuple(HexCoord(self.q + dq, self.r + dr) for dq, dr in HEX_DIRECTIONS)

    def to_cube(self) -> tuple[int, int, int]:
        x = self.q
        z = self.r
        y = -x - z
        return x, y, z

    def distance_to(self, other: "HexCoord") -> int:
        ax, ay, az = self.to_cube()
        bx, by, bz = other.to_cube()
        return max(abs(ax - bx), abs(ay - by), abs(az - bz))

    def line_to(self, other: "HexCoord") -> list["HexCoord"]:
        distance = self.distance_to(other)
        if distance == 0:
            return [self]

        ax, ay, az = self.to_cube()
        bx, by, bz = other.to_cube()
        line: list[HexCoord] = []
        for step in range(distance + 1):
            t = step / distance
            cube = _cube_round(
                _lerp(ax, bx, t),
                _lerp(ay, by, t),
                _lerp(az, bz, t),
            )
            line.append(HexCoord(cube[0], cube[2]))
        return line


@dataclass(slots=True)
class HexCell:
    terrain: TerrainType = TerrainType.OPEN
    elevation_meters: float = 0.0


@dataclass(slots=True)
class HexGridMap:
    """A rectangular axial hex battlefield."""

    width: int
    height: int
    hex_size_meters: float = 75.0
    _cells: dict[HexCoord, HexCell] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Map dimensions must be positive integers.")

        for q in range(self.width):
            for r in range(self.height):
                self._cells.setdefault(HexCoord(q, r), HexCell())

    @classmethod
    def from_terrain_rows(
        cls,
        rows: Sequence[str],
        *,
        hex_size_meters: float = 75.0,
    ) -> "HexGridMap":
        if not rows:
            raise ValueError("rows must not be empty")

        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("all terrain rows must have equal width")

        battle_map = cls(width=width, height=len(rows), hex_size_meters=hex_size_meters)
        for r, row in enumerate(rows):
            for q, char in enumerate(row):
                try:
                    terrain = TERRAIN_FROM_CHAR[char]
                except KeyError as exc:
                    raise ValueError(f"Unsupported terrain character: {char!r}") from exc
                battle_map.set_terrain(HexCoord(q, r), terrain)
        return battle_map

    def coords(self) -> Iterable[HexCoord]:
        return self._cells.keys()

    def in_bounds(self, coord: HexCoord) -> bool:
        return 0 <= coord.q < self.width and 0 <= coord.r < self.height

    def cell_at(self, coord: HexCoord) -> HexCell:
        if not self.in_bounds(coord):
            raise ValueError(f"Coordinate out of bounds: {coord}")
        return self._cells[coord]

    def set_terrain(
        self,
        coord: HexCoord,
        terrain: TerrainType,
        *,
        elevation_meters: float | None = None,
    ) -> None:
        cell = self.cell_at(coord)
        cell.terrain = terrain
        if elevation_meters is not None:
            cell.elevation_meters = elevation_meters

    def set_elevation(self, coord: HexCoord, elevation_meters: float) -> None:
        self.cell_at(coord).elevation_meters = elevation_meters

    def terrain_at(self, coord: HexCoord) -> TerrainType:
        return self.cell_at(coord).terrain

    def elevation_at(self, coord: HexCoord) -> float:
        return self.cell_at(coord).elevation_meters

    def neighbors(self, coord: HexCoord, *, include_impassable: bool = False) -> list[HexCoord]:
        results: list[HexCoord] = []
        for neighbor in coord.neighbors():
            if not self.in_bounds(neighbor):
                continue
            if not include_impassable and math.isinf(self.movement_cost(neighbor)):
                continue
            results.append(neighbor)
        return results

    def movement_cost(
        self,
        coord: HexCoord,
        resolver: TerrainCostResolver | None = None,
    ) -> float:
        cell = self.cell_at(coord)
        if resolver is None:
            return DEFAULT_TERRAIN_COSTS[cell.terrain]
        if isinstance(resolver, Mapping):
            return resolver.get(cell.terrain, math.inf)
        return resolver(coord, cell)

    def find_path(
        self,
        start: HexCoord,
        goal: HexCoord,
        *,
        terrain_costs: TerrainCostResolver | None = None,
    ) -> list[HexCoord]:
        if not self.in_bounds(start) or not self.in_bounds(goal):
            raise ValueError("Start and goal must both be within map bounds.")
        if start == goal:
            return [start]

        frontier: list[tuple[float, int, HexCoord]] = [(0.0, 0, start)]
        came_from: dict[HexCoord, HexCoord | None] = {start: None}
        cost_so_far: dict[HexCoord, float] = {start: 0.0}
        minimum_cost = _minimum_traversable_cost(terrain_costs)
        sequence = 1

        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal:
                break

            for neighbor in self.neighbors(current, include_impassable=True):
                step_cost = self.movement_cost(neighbor, terrain_costs)
                if math.isinf(step_cost):
                    continue

                new_cost = cost_so_far[current] + step_cost
                if new_cost >= cost_so_far.get(neighbor, math.inf):
                    continue

                cost_so_far[neighbor] = new_cost
                priority = new_cost + (neighbor.distance_to(goal) * minimum_cost)
                came_from[neighbor] = current
                heapq.heappush(frontier, (priority, sequence, neighbor))
                sequence += 1

        if goal not in came_from:
            return []

        path: list[HexCoord] = []
        current: HexCoord | None = goal
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path

    def has_line_of_sight(
        self,
        origin: HexCoord,
        target: HexCoord,
        *,
        observer_height: float = 1.7,
        target_height: float = 1.7,
    ) -> bool:
        if not self.in_bounds(origin) or not self.in_bounds(target):
            raise ValueError("Origin and target must both be within map bounds.")
        if origin == target:
            return True

        line = origin.line_to(target)
        total_steps = len(line) - 1
        origin_height = self.elevation_at(origin) + observer_height
        target_height_absolute = self.elevation_at(target) + target_height

        for index, coord in enumerate(line[1:-1], start=1):
            cell = self.cell_at(coord)
            fraction = index / total_steps
            expected_height = _lerp(origin_height, target_height_absolute, fraction)
            obstruction = cell.elevation_meters + TERRAIN_LOS_OBSTRUCTION[cell.terrain]
            if obstruction >= expected_height:
                return False

        return True


def _lerp(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def _cube_round(x: float, y: float, z: float) -> tuple[int, int, int]:
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
    return int(rx), int(ry), int(rz)


def _minimum_traversable_cost(resolver: TerrainCostResolver | None) -> float:
    if resolver is None:
        candidates = DEFAULT_TERRAIN_COSTS.values()
    elif isinstance(resolver, Mapping):
        candidates = resolver.values()
    else:
        return 1.0

    traversable = [cost for cost in candidates if cost > 0 and not math.isinf(cost)]
    return min(traversable, default=1.0)
