"""Procedural skirmish scenario generator.

Combines the map generator with deterministic unit and objective placement
to produce balanced, ready-to-play GameState instances without requiring
hand-authored JSON scenario files.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .game import GameState
from .map import HexCoord, HexGridMap, TerrainType
from .map_generator import MapGenConfig, generate_map
from .scenario import ScenarioObjective
from .units import (
    Side,
    Unit,
    make_artillery_battery,
    make_cavalry_squadron,
    make_commander,
    make_infantry_half_battalion,
    make_skirmisher_detachment,
    make_supply_wagon,
)


@dataclass(frozen=True)
class SkirmishConfig:
    """Parameters controlling the generated scenario."""

    size: str = "medium"          # "small", "medium", "large"
    blue_force: str = "balanced"  # "infantry", "cavalry", "balanced", "heavy"
    red_force: str = "balanced"
    objective_count: int = 3
    max_turns: int = 20
    seed: int | None = None


# ---------------------------------------------------------------------------
# Size presets
# ---------------------------------------------------------------------------

_MAP_PRESETS: dict[str, MapGenConfig] = {
    "small": MapGenConfig(width=20, height=16, village_count=1, river_count=1, road_count=1),
    "medium": MapGenConfig(width=35, height=28, village_count=2, river_count=1, road_count=2),
    "large": MapGenConfig(width=55, height=45, village_count=3, river_count=2, road_count=3),
}

_UNIT_COUNTS: dict[str, dict[str, int]] = {
    #               inf  cav  art  skm  wgn  cmd
    "small":    {"inf": 3, "cav": 1, "art": 1, "skm": 1, "wgn": 0, "cmd": 1},
    "medium":   {"inf": 4, "cav": 2, "art": 2, "skm": 1, "wgn": 1, "cmd": 1},
    "large":    {"inf": 6, "cav": 2, "art": 2, "skm": 2, "wgn": 1, "cmd": 1},
}

_FORCE_MODIFIERS: dict[str, dict[str, float]] = {
    "infantry": {"inf": 1.5, "cav": 0.5, "art": 0.5, "skm": 1.0},
    "cavalry":  {"inf": 0.5, "cav": 2.0, "art": 0.5, "skm": 1.0},
    "balanced": {"inf": 1.0, "cav": 1.0, "art": 1.0, "skm": 1.0},
    "heavy":    {"inf": 1.0, "cav": 0.5, "art": 2.0, "skm": 0.5},
}


def generate_skirmish(config: SkirmishConfig | None = None, *, rng_seed: int = 1) -> GameState:
    """Generate a complete, balanced skirmish GameState.

    Args:
        config: Optional configuration; defaults to medium balanced skirmish.
        rng_seed: Seed for the game engine's RNG (separate from map gen seed).

    Returns:
        A fully initialised :class:`~core.game.GameState` ready to play.
    """
    if config is None:
        config = SkirmishConfig()

    seed = config.seed if config.seed is not None else rng_seed
    rng = random.Random(seed)

    map_cfg = _MAP_PRESETS.get(config.size, _MAP_PRESETS["medium"])
    map_cfg = MapGenConfig(**{**map_cfg.__dict__, "seed": seed})
    battle_map = generate_map(map_cfg)

    blue_units = _place_units(battle_map, Side.BLUE, config.size, config.blue_force, rng, row_side="top")
    red_units = _place_units(battle_map, Side.RED, config.size, config.red_force, rng, row_side="bottom")

    objectives = _place_objectives(battle_map, config.objective_count, rng)

    all_units = {u.id: u for u in blue_units + red_units}

    return GameState(
        battle_map=battle_map,
        units=all_units,
        objectives=_place_objectives(battle_map, config.objective_count, rng),
        rng_seed=rng_seed,
        current_turn=1,
        reinforcements=[],
    )


# ---------------------------------------------------------------------------
# Unit placement
# ---------------------------------------------------------------------------

_INFANTRY_NAMES = [
    "1st Line Bn", "2nd Line Bn", "3rd Line Bn", "4th Line Bn",
    "5th Line Bn", "6th Line Bn", "Guard Bn", "Fusilier Bn",
]
_CAVALRY_NAMES = ["Hussar Sqn", "Dragoon Sqn", "Uhlan Sqn", "Cuirassier Sqn"]
_ARTILLERY_NAMES = ["Foot Battery A", "Foot Battery B", "Horse Battery A"]
_SKIRMISHER_NAMES = ["1st Jäger Det.", "2nd Jäger Det.", "Rifle Company"]
_WAGON_NAMES = ["Supply Wagon I", "Supply Wagon II"]
_COMMANDER_NAMES = {Side.BLUE: "Blue Commander", Side.RED: "Red Commander"}


def _place_units(
    battle_map: HexGridMap,
    side: Side,
    size: str,
    force_type: str,
    rng: random.Random,
    row_side: str,
) -> list[Unit]:
    counts = _UNIT_COUNTS.get(size, _UNIT_COUNTS["medium"]).copy()
    mods = _FORCE_MODIFIERS.get(force_type, _FORCE_MODIFIERS["balanced"])
    units: list[Unit] = []
    uid_prefix = "b" if side is Side.BLUE else "r"

    # Deployment zone: top 3 rows for BLUE, bottom 3 for RED
    if row_side == "top":
        deploy_rows = list(range(2, min(5, battle_map.height)))
    else:
        deploy_rows = list(range(max(0, battle_map.height - 5), battle_map.height - 2))

    available_hexes = [
        HexCoord(q, r)
        for r in deploy_rows
        for q in range(battle_map.width)
        if battle_map.terrain_at(HexCoord(q, r))
        not in (TerrainType.RIVER,)
    ]
    rng.shuffle(available_hexes)
    hex_pool = list(available_hexes)

    def pop_hex() -> HexCoord | None:
        return hex_pool.pop(0) if hex_pool else None

    inf_names = list(_INFANTRY_NAMES)
    cav_names = list(_CAVALRY_NAMES)
    art_names = list(_ARTILLERY_NAMES)
    skm_names = list(_SKIRMISHER_NAMES)
    wgn_names = list(_WAGON_NAMES)

    n_inf = max(0, round(counts["inf"] * mods.get("inf", 1.0)))
    n_cav = max(0, round(counts["cav"] * mods.get("cav", 1.0)))
    n_art = max(0, round(counts["art"] * mods.get("art", 1.0)))
    n_skm = max(0, round(counts["skm"] * mods.get("skm", 1.0)))
    n_wgn = counts["wgn"]
    n_cmd = counts["cmd"]

    idx = [0]

    def next_id(prefix: str) -> str:
        idx[0] += 1
        return f"{uid_prefix}_{prefix}{idx[0]}"

    for i in range(n_inf):
        u = make_infantry_half_battalion(next_id("inf"), inf_names[i % len(inf_names)], side)
        u.position = pop_hex()
        units.append(u)

    for i in range(n_cav):
        u = make_cavalry_squadron(next_id("cav"), cav_names[i % len(cav_names)], side)
        u.position = pop_hex()
        units.append(u)

    for i in range(n_art):
        u = make_artillery_battery(next_id("art"), art_names[i % len(art_names)], side)
        u.position = pop_hex()
        units.append(u)

    for i in range(n_skm):
        u = make_skirmisher_detachment(next_id("skm"), skm_names[i % len(skm_names)], side)
        u.position = pop_hex()
        units.append(u)

    for i in range(n_wgn):
        u = make_supply_wagon(next_id("wgn"), wgn_names[i % len(wgn_names)], side)
        u.position = pop_hex()
        units.append(u)

    for _ in range(n_cmd):
        u = make_commander(next_id("cmd"), _COMMANDER_NAMES[side], side)
        u.position = pop_hex()
        units.append(u)

    return units


# ---------------------------------------------------------------------------
# Objective placement
# ---------------------------------------------------------------------------

def _place_objectives(
    battle_map: HexGridMap,
    count: int,
    rng: random.Random,
) -> list[ScenarioObjective]:
    # Prefer villages, hills and forts at mid-map
    mid_r_min = battle_map.height // 4
    mid_r_max = 3 * battle_map.height // 4

    preferred = [
        HexCoord(q, r)
        for r in range(mid_r_min, mid_r_max)
        for q in range(battle_map.width)
        if battle_map.terrain_at(HexCoord(q, r))
        in (TerrainType.VILLAGE, TerrainType.HILL, TerrainType.FORTIFICATION)
    ]
    fallback = [
        HexCoord(q, r)
        for r in range(mid_r_min, mid_r_max)
        for q in range(battle_map.width)
        if battle_map.terrain_at(HexCoord(q, r)) not in (TerrainType.RIVER,)
    ]

    candidates = preferred if len(preferred) >= count else fallback
    rng.shuffle(candidates)

    objectives: list[ScenarioObjective] = []
    used: set[HexCoord] = set()
    for coord in candidates:
        if coord in used:
            continue
        if len(objectives) >= count:
            break
        obj_id = f"obj_{coord.q}_{coord.r}"
        terrain = battle_map.terrain_at(coord)
        label = {
            TerrainType.VILLAGE: "Village",
            TerrainType.HILL: "Hill",
            TerrainType.FORTIFICATION: "Redoubt",
        }.get(terrain, "Position")
        objectives.append(ScenarioObjective(
            objective_id=obj_id,
            label=label,
            position=coord,
            points=5 if terrain is TerrainType.FORTIFICATION else 3,
        ))
        used.add(coord)

    return objectives
