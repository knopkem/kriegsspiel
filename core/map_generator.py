"""Procedural battlefield map generator.

Generates random but tactically interesting Kriegsspiel battlefields with
configurable terrain density and guaranteed playability.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from .map import HexCoord, HexGridMap, TerrainType


@dataclass(frozen=True)
class MapGenConfig:
    """Configuration for procedural map generation."""

    width: int = 30
    height: int = 25
    # Terrain density fractions (must sum to ≤ 1.0; remainder is OPEN)
    hill_fraction: float = 0.12
    forest_fraction: float = 0.10
    marsh_fraction: float = 0.04
    village_count: int = 2
    fort_count: int = 0
    river_count: int = 1
    road_count: int = 2
    # Hill cluster radius (1 = isolated hexes, 3 = broad ridges)
    hill_cluster_radius: int = 2
    # Forest cluster radius
    forest_cluster_radius: int = 2
    # Seed (None = random)
    seed: int | None = None


def generate_map(config: MapGenConfig | None = None) -> HexGridMap:
    """Generate a random HexGridMap from the given config."""
    if config is None:
        config = MapGenConfig()

    rng = random.Random(config.seed)
    m = HexGridMap(width=config.width, height=config.height)

    _place_hill_clusters(m, config, rng)
    _place_forest_clusters(m, config, rng)
    _place_marsh(m, config, rng)
    _place_rivers(m, config, rng)
    _place_roads(m, config, rng)
    _place_villages(m, config, rng)
    _place_forts(m, config, rng)
    _assign_elevations(m, rng)

    return m


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _open_hexes(m: HexGridMap) -> list[HexCoord]:
    return [c for c in m.coords() if m.terrain_at(c) is TerrainType.OPEN]


def _place_hill_clusters(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    """Paint hill clusters onto the map."""
    total = cfg.width * cfg.height
    target = int(total * cfg.hill_fraction)
    painted = 0
    attempts = 0
    while painted < target and attempts < 200:
        attempts += 1
        cq = rng.randint(cfg.hill_cluster_radius, cfg.width - cfg.hill_cluster_radius - 1)
        cr = rng.randint(cfg.hill_cluster_radius, cfg.height - cfg.hill_cluster_radius - 1)
        centre = HexCoord(cq, cr)
        for coord in _hex_ring_up_to(m, centre, cfg.hill_cluster_radius):
            if m.terrain_at(coord) is TerrainType.OPEN:
                m.set_terrain(coord, TerrainType.HILL)
                painted += 1


def _place_forest_clusters(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    """Paint forest clusters avoiding hills."""
    total = cfg.width * cfg.height
    target = int(total * cfg.forest_fraction)
    painted = 0
    attempts = 0
    while painted < target and attempts < 200:
        attempts += 1
        cq = rng.randint(cfg.forest_cluster_radius, cfg.width - cfg.forest_cluster_radius - 1)
        cr = rng.randint(cfg.forest_cluster_radius, cfg.height - cfg.forest_cluster_radius - 1)
        centre = HexCoord(cq, cr)
        for coord in _hex_ring_up_to(m, centre, cfg.forest_cluster_radius):
            if m.terrain_at(coord) is TerrainType.OPEN:
                m.set_terrain(coord, TerrainType.FOREST)
                painted += 1


def _place_marsh(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    total = cfg.width * cfg.height
    target = int(total * cfg.marsh_fraction)
    open_hexes = _open_hexes(m)
    rng.shuffle(open_hexes)
    for coord in open_hexes[:target]:
        m.set_terrain(coord, TerrainType.MARSH)


def _place_rivers(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    """Trace river paths from top to bottom of the map."""
    for _ in range(cfg.river_count):
        # Start at a random top-row hex
        start_q = rng.randint(2, cfg.width - 3)
        current = HexCoord(start_q, 0)
        for row in range(cfg.height):
            if not m.in_bounds(current):
                break
            if m.terrain_at(current) not in (TerrainType.HILL, TerrainType.FORTIFICATION):
                m.set_terrain(current, TerrainType.RIVER)
            # Meander slightly left/right as we go down
            drift = rng.choice([-1, 0, 0, 1])
            next_q = max(0, min(cfg.width - 1, current.q + drift))
            current = HexCoord(next_q, row + 1)


def _place_roads(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    """Trace roads from left edge to right edge of the map."""
    used_rows: set[int] = set()
    for _ in range(cfg.road_count):
        for _attempt in range(20):
            row = rng.randint(1, cfg.height - 2)
            if row not in used_rows:
                used_rows.add(row)
                break
        for col in range(cfg.width):
            coord = HexCoord(col, row)
            if not m.in_bounds(coord):
                continue
            terrain = m.terrain_at(coord)
            # Roads go over open/hill but not river or forest
            if terrain in (TerrainType.OPEN, TerrainType.HILL, TerrainType.VILLAGE):
                m.set_terrain(coord, TerrainType.ROAD)
            elif terrain is TerrainType.FOREST:
                # Road cuts through forest
                m.set_terrain(coord, TerrainType.ROAD)


def _place_villages(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    open_hexes = _open_hexes(m)
    rng.shuffle(open_hexes)
    # Prefer road-adjacent hexes
    road_adjacent = [
        c for c in open_hexes
        if any(m.in_bounds(n) and m.terrain_at(n) is TerrainType.ROAD for n in c.neighbors())
    ]
    candidates = road_adjacent if len(road_adjacent) >= cfg.village_count else open_hexes
    for coord in candidates[:cfg.village_count]:
        m.set_terrain(coord, TerrainType.VILLAGE)


def _place_forts(m: HexGridMap, cfg: MapGenConfig, rng: random.Random) -> None:
    # Prefer hill hexes for forts
    hill_hexes = [c for c in m.coords() if m.terrain_at(c) is TerrainType.HILL]
    rng.shuffle(hill_hexes)
    for coord in hill_hexes[:cfg.fort_count]:
        m.set_terrain(coord, TerrainType.FORTIFICATION)


def _assign_elevations(m: HexGridMap, rng: random.Random) -> None:
    """Assign elevation values: hills high, rivers low, graduated elsewhere."""
    for coord in m.coords():
        terrain = m.terrain_at(coord)
        if terrain is TerrainType.HILL:
            elev = rng.uniform(40, 80)
        elif terrain is TerrainType.FORTIFICATION:
            elev = rng.uniform(50, 90)
        elif terrain is TerrainType.RIVER:
            elev = rng.uniform(0, 10)
        elif terrain is TerrainType.MARSH:
            elev = rng.uniform(0, 15)
        elif terrain is TerrainType.FOREST:
            elev = rng.uniform(5, 30)
        else:
            elev = rng.uniform(5, 25)
        m.set_elevation(coord, elev)


def _hex_ring_up_to(
    m: HexGridMap,
    centre: HexCoord,
    radius: int,
) -> list[HexCoord]:
    """Return all in-bounds hexes within `radius` of centre."""
    result: list[HexCoord] = []
    for dq in range(-radius, radius + 1):
        for dr in range(-radius, radius + 1):
            coord = HexCoord(centre.q + dq, centre.r + dr)
            if m.in_bounds(coord) and centre.distance_to(coord) <= radius:
                result.append(coord)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Scenario helpers
# ──────────────────────────────────────────────────────────────────────────────


def generate_quick_battle_map(
    *,
    size: str = "medium",
    seed: int | None = None,
) -> HexGridMap:
    """High-level helper for Quick Battle mode.

    Args:
        size: "small" (20×16), "medium" (35×28), or "large" (55×45).
        seed: Optional RNG seed for reproducibility.
    """
    presets: dict[str, MapGenConfig] = {
        "small": MapGenConfig(
            width=20, height=16,
            hill_fraction=0.10, forest_fraction=0.08,
            village_count=1, river_count=1, road_count=1,
            seed=seed,
        ),
        "medium": MapGenConfig(
            width=35, height=28,
            hill_fraction=0.12, forest_fraction=0.10,
            village_count=2, river_count=1, road_count=2,
            seed=seed,
        ),
        "large": MapGenConfig(
            width=55, height=45,
            hill_fraction=0.14, forest_fraction=0.11,
            marsh_fraction=0.04, village_count=3,
            river_count=2, road_count=3,
            seed=seed,
        ),
    }
    cfg = presets.get(size, presets["medium"])
    return generate_map(cfg)
