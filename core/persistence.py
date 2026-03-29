"""Save and load game state to/from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .game import GameEvent, GameState
from .map import HexCoord, HexGridMap, TerrainType
from .orders import OrderBook
from .replay import ReplayRecorder
from .scenario import ScenarioObjective
from .units import (
    FacingDirection, Formation, MoraleState, Side, Unit, UnitType,
    make_artillery_battery, make_cavalry_squadron, make_commander,
    make_infantry_half_battalion, make_skirmisher_detachment,
)


def save_game(game: GameState, path: str) -> None:
    """Serialise the current game state to a JSON file."""
    data: dict[str, Any] = {
        "current_turn": game.current_turn,
        "rng_seed": game.rng_seed,
        "map": _serialise_map(game.battle_map),
        "units": [_serialise_unit(u) for u in game.units.values()],
        "objectives": [_serialise_objective(o) for o in game.objectives],
        "event_log": [
            {"turn": e.turn, "category": e.category, "message": e.message}
            for e in game.event_log
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2))


def load_game(path: str) -> GameState:
    """Reconstruct a GameState from a saved JSON file."""
    data = json.loads(Path(path).read_text())
    battle_map = _deserialise_map(data["map"])
    units = {u["id"]: _deserialise_unit(u) for u in data["units"]}
    objectives = tuple(_deserialise_objective(o) for o in data["objectives"])
    event_log = [
        GameEvent(e["turn"], e["category"], e["message"])
        for e in data.get("event_log", [])
    ]
    state = GameState(
        battle_map=battle_map,
        units=units,
        current_turn=data["current_turn"],
        rng_seed=data["rng_seed"],
        objectives=objectives,
    )
    state.event_log = event_log
    return state


def _serialise_map(m: HexGridMap) -> dict:
    cells = []
    for coord in m.coords():
        cell = m._cells[coord]
        cells.append({
            "q": coord.q,
            "r": coord.r,
            "terrain": cell.terrain.value,
            "elevation": cell.elevation_meters,
        })
    return {"width": m.width, "height": m.height, "cells": cells}


def _deserialise_map(data: dict) -> HexGridMap:
    m = HexGridMap(width=data["width"], height=data["height"])
    for c in data["cells"]:
        coord = HexCoord(c["q"], c["r"])
        m.set_terrain(coord, TerrainType(c["terrain"]))
        m.set_elevation(coord, c["elevation"])
    return m


def _serialise_unit(u: Unit) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "side": u.side.value,
        "unit_type": u.unit_type.value,
        "formation": u.formation.value,
        "hit_points": u.hit_points,
        "max_hit_points": u.max_hit_points,
        "morale_state": u.morale_state.value,
        "fatigue": u.fatigue,
        "ammo": u.ammo,
        "max_ammo": u.max_ammo,
        "facing": u.facing.value,
        "consecutive_hold_turns": u.consecutive_hold_turns,
        "commander_ability_uses": u.commander_ability_uses,
        "commander_radius": u.commander_radius,
        "position": [u.position.q, u.position.r] if u.position else None,
    }


def _deserialise_unit(data: dict) -> Unit:
    unit_type = UnitType(data["unit_type"])
    side = Side(data["side"])
    factory_map = {
        UnitType.INFANTRY: make_infantry_half_battalion,
        UnitType.CAVALRY: make_cavalry_squadron,
        UnitType.ARTILLERY: make_artillery_battery,
        UnitType.SKIRMISHER: make_skirmisher_detachment,
        UnitType.COMMANDER: make_commander,
    }
    unit = factory_map[unit_type](data["id"], data["name"], side)
    unit.hit_points = data["hit_points"]
    unit.max_hit_points = data["max_hit_points"]
    unit.morale_state = MoraleState(data["morale_state"])
    unit.fatigue = data["fatigue"]
    unit.ammo = data.get("ammo", 0)
    unit.max_ammo = data.get("max_ammo", 0)
    unit.facing = FacingDirection(data.get("facing", "S"))
    unit.consecutive_hold_turns = data.get("consecutive_hold_turns", 0)
    unit.commander_ability_uses = data.get("commander_ability_uses", 0)
    unit.commander_radius = data.get("commander_radius", 5)
    pos = data.get("position")
    unit.position = HexCoord(pos[0], pos[1]) if pos else None
    return unit


def _serialise_objective(o: ScenarioObjective) -> dict:
    return {
        "id": o.objective_id,
        "label": o.label,
        "position": [o.position.q, o.position.r],
        "points": o.points,
    }


def _deserialise_objective(data: dict) -> ScenarioObjective:
    return ScenarioObjective(
        objective_id=data["id"],
        label=data["label"],
        position=HexCoord(data["position"][0], data["position"][1]),
        points=data["points"],
    )
