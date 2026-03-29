"""Scenario loading and battlefield instantiation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from .map import HexCoord, HexGridMap
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


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


@dataclass(frozen=True, slots=True)
class ScenarioObjective:
    objective_id: str
    label: str
    position: HexCoord
    points: int


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    title: str
    description: str
    map_rows: tuple[str, ...]
    units: tuple[dict, ...]
    objectives: tuple[ScenarioObjective, ...]
    starting_turn: int = 1
    reinforcements: tuple[dict, ...] = ()
    max_turns: int | None = None

    def build_map(self) -> HexGridMap:
        return HexGridMap.from_terrain_rows(self.map_rows)

    def build_units(self) -> dict[str, Unit]:
        builders: dict[str, Callable[..., Unit]] = {
            "infantry": make_infantry_half_battalion,
            "cavalry": make_cavalry_squadron,
            "artillery": make_artillery_battery,
            "skirmisher": make_skirmisher_detachment,
            "commander": make_commander,
            "supply_wagon": make_supply_wagon,
        }
        built: dict[str, Unit] = {}
        for unit_spec in self.units:
            builder = builders[unit_spec["type"]]
            side = Side(unit_spec["side"])
            position = HexCoord(*unit_spec["position"])
            kwargs = {}
            if unit_spec["type"] == "commander":
                kwargs["command_radius"] = unit_spec.get("command_radius", 6)
            unit = builder(unit_spec["id"], unit_spec["name"], side, position=position, **kwargs)
            built[unit.id] = unit
        return built


def load_scenario(path: Path) -> Scenario:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return Scenario(
        scenario_id=raw["scenario_id"],
        title=raw["title"],
        description=raw["description"],
        map_rows=tuple(raw["map_rows"]),
        units=tuple(raw["units"]),
        objectives=tuple(
            ScenarioObjective(
                objective_id=item["id"],
                label=item["label"],
                position=HexCoord(*item["position"]),
                points=item["points"],
            )
            for item in raw["objectives"]
        ),
        starting_turn=raw.get("starting_turn", 1),
        reinforcements=tuple(raw.get("reinforcements", [])),
        max_turns=raw.get("max_turns"),
    )


def load_builtin_scenario(name: str) -> Scenario:
    return load_scenario(DATA_DIR / f"{name}.json")
