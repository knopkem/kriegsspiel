"""Headless scenario editor model.

:class:`ScenarioEditor` holds a mutable representation of a scenario and
provides methods for painting terrain, placing / removing units and
objectives, and serialising the result to a JSON file.

This module contains **no pygame code** so it can be unit-tested headlessly.
The pygame UI lives in ``ui/scenario_editor_ui.py``.

Typical usage::

    editor = ScenarioEditor.blank(width=20, height=15, scenario_id="my_map")
    editor.paint_terrain(HexCoord(3, 4), TerrainType.FOREST)
    editor.place_unit({"id": "b1", "name": "1/Inf", "side": "blue",
                       "type": "infantry", "position": [3, 4]})
    editor.save("data/scenarios/my_map.json")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .map import HexCoord, TerrainType, TERRAIN_FROM_CHAR


# Reverse mapping: TerrainType → single character for JSON export
CHAR_FROM_TERRAIN: dict[TerrainType, str] = {v: k for k, v in TERRAIN_FROM_CHAR.items()}

# Legal unit types accepted by the scenario loader
UNIT_TYPES: tuple[str, ...] = (
    "infantry", "cavalry", "artillery", "skirmisher", "commander", "supply_wagon"
)


@dataclass
class EditorObjective:
    objective_id: str
    label: str
    q: int
    r: int
    points: int = 3

    def to_dict(self) -> dict:
        return {
            "id": self.objective_id,
            "label": self.label,
            "position": [self.q, self.r],
            "points": self.points,
        }


@dataclass
class ScenarioEditor:
    """Mutable in-memory representation of a scenario under construction."""

    scenario_id: str
    title: str
    description: str
    width: int
    height: int
    # 2-D terrain grid [row][col]
    terrain: list[list[TerrainType]] = field(default_factory=list)
    # Unit specs as raw dicts (same format as JSON)
    units: list[dict] = field(default_factory=list)
    objectives: list[EditorObjective] = field(default_factory=list)
    starting_turn: int = 1
    reinforcements: list[dict] = field(default_factory=list)
    # Undo stack — list of (terrain snapshot, units snapshot, objectives snapshot)
    _undo_stack: list[tuple] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def blank(
        cls,
        *,
        width: int,
        height: int,
        scenario_id: str = "new_scenario",
        title: str = "New Scenario",
        description: str = "",
        default_terrain: TerrainType = TerrainType.OPEN,
    ) -> "ScenarioEditor":
        terrain = [[default_terrain] * width for _ in range(height)]
        return cls(
            scenario_id=scenario_id,
            title=title,
            description=description,
            width=width,
            height=height,
            terrain=terrain,
        )

    @classmethod
    def from_json(cls, path: str) -> "ScenarioEditor":
        """Load an existing scenario JSON into the editor for modification."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        rows: list[str] = raw["map_rows"]
        height = len(rows)
        width = len(rows[0]) if rows else 0
        terrain = [
            [TERRAIN_FROM_CHAR.get(ch, TerrainType.OPEN) for ch in row]
            for row in rows
        ]
        return cls(
            scenario_id=raw["scenario_id"],
            title=raw["title"],
            description=raw.get("description", ""),
            width=width,
            height=height,
            terrain=terrain,
            units=list(raw.get("units", [])),
            objectives=[
                EditorObjective(
                    objective_id=obj["id"],
                    label=obj["label"],
                    q=obj["position"][0],
                    r=obj["position"][1],
                    points=obj.get("points", 3),
                )
                for obj in raw.get("objectives", [])
            ],
            starting_turn=raw.get("starting_turn", 1),
            reinforcements=list(raw.get("reinforcements", [])),
        )

    # ------------------------------------------------------------------
    # Terrain painting
    # ------------------------------------------------------------------

    def in_bounds(self, coord: HexCoord) -> bool:
        return 0 <= coord.q < self.width and 0 <= coord.r < self.height

    def terrain_at(self, coord: HexCoord) -> TerrainType:
        if not self.in_bounds(coord):
            raise ValueError(f"Coordinate out of bounds: {coord}")
        return self.terrain[coord.r][coord.q]

    def paint_terrain(self, coord: HexCoord, terrain: TerrainType) -> None:
        """Set terrain at *coord*. Pushes undo snapshot automatically."""
        if not self.in_bounds(coord):
            return
        self._push_undo()
        self.terrain[coord.r][coord.q] = terrain

    def fill_rect(
        self,
        top_left: HexCoord,
        bottom_right: HexCoord,
        terrain: TerrainType,
    ) -> None:
        """Fill a rectangular region with *terrain*."""
        self._push_undo()
        for r in range(top_left.r, min(bottom_right.r + 1, self.height)):
            for q in range(top_left.q, min(bottom_right.q + 1, self.width)):
                self.terrain[r][q] = terrain

    # ------------------------------------------------------------------
    # Unit management
    # ------------------------------------------------------------------

    def _unit_index_by_id(self, unit_id: str) -> int | None:
        for i, u in enumerate(self.units):
            if u["id"] == unit_id:
                return i
        return None

    def place_unit(self, spec: dict) -> None:
        """Add or replace a unit spec. *spec* must have: id, name, side, type, position."""
        required = {"id", "name", "side", "type", "position"}
        missing = required - spec.keys()
        if missing:
            raise ValueError(f"Unit spec missing fields: {missing}")
        if spec["type"] not in UNIT_TYPES:
            raise ValueError(f"Unknown unit type: {spec['type']!r}")
        self._push_undo()
        idx = self._unit_index_by_id(spec["id"])
        if idx is not None:
            self.units[idx] = spec
        else:
            self.units.append(spec)

    def remove_unit(self, unit_id: str) -> bool:
        """Remove a unit by id. Returns True if found and removed."""
        idx = self._unit_index_by_id(unit_id)
        if idx is None:
            return False
        self._push_undo()
        self.units.pop(idx)
        return True

    def move_unit(self, unit_id: str, new_pos: HexCoord) -> bool:
        """Update a unit's position in-place. Returns True if found."""
        idx = self._unit_index_by_id(unit_id)
        if idx is None:
            return False
        self._push_undo()
        self.units[idx] = {**self.units[idx], "position": [new_pos.q, new_pos.r]}
        return True

    def units_at(self, coord: HexCoord) -> list[dict]:
        return [u for u in self.units if u["position"] == [coord.q, coord.r]]

    # ------------------------------------------------------------------
    # Objective management
    # ------------------------------------------------------------------

    def _obj_index_by_id(self, obj_id: str) -> int | None:
        for i, o in enumerate(self.objectives):
            if o.objective_id == obj_id:
                return i
        return None

    def place_objective(self, obj: EditorObjective) -> None:
        self._push_undo()
        idx = self._obj_index_by_id(obj.objective_id)
        if idx is not None:
            self.objectives[idx] = obj
        else:
            self.objectives.append(obj)

    def remove_objective(self, obj_id: str) -> bool:
        idx = self._obj_index_by_id(obj_id)
        if idx is None:
            return False
        self._push_undo()
        self.objectives.pop(idx)
        return True

    def objectives_at(self, coord: HexCoord) -> list[EditorObjective]:
        return [o for o in self.objectives if o.q == coord.q and o.r == coord.r]

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    _MAX_UNDO = 50

    def _snapshot(self) -> tuple:
        terrain_copy = [row[:] for row in self.terrain]
        return (terrain_copy, [u.copy() for u in self.units], list(self.objectives))

    def _push_undo(self) -> None:
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self._MAX_UNDO:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        terrain, units, objectives = self._undo_stack.pop()
        self.terrain = terrain
        self.units = units
        self.objectives = objectives
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of validation error strings; empty = valid."""
        errors: list[str] = []
        if not self.scenario_id.strip():
            errors.append("scenario_id must not be empty")
        if not self.title.strip():
            errors.append("title must not be empty")
        if self.width < 4 or self.height < 4:
            errors.append("map must be at least 4×4")
        # Unique unit ids
        ids = [u["id"] for u in self.units]
        if len(ids) != len(set(ids)):
            errors.append("duplicate unit IDs detected")
        # Each side must have at least 1 unit
        sides = {u["side"] for u in self.units}
        for side in ("blue", "red"):
            if side not in sides:
                errors.append(f"no {side} units placed")
        # Objectives
        if not self.objectives:
            errors.append("at least one objective required")
        for obj in self.objectives:
            if not self.in_bounds(HexCoord(obj.q, obj.r)):
                errors.append(f"objective {obj.objective_id!r} is out of bounds")
        # Units in bounds
        for u in self.units:
            q, r = u["position"]
            if not self.in_bounds(HexCoord(q, r)):
                errors.append(f"unit {u['id']!r} is out of bounds")
        return errors

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to the canonical scenario JSON structure."""
        map_rows = [
            "".join(CHAR_FROM_TERRAIN[t] for t in row)
            for row in self.terrain
        ]
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "description": self.description,
            "map_rows": map_rows,
            "units": self.units,
            "objectives": [o.to_dict() for o in self.objectives],
            "starting_turn": self.starting_turn,
            "reinforcements": self.reinforcements,
        }

    def save(self, path: str) -> None:
        """Validate and write JSON to *path*. Raises ValueError on invalid state."""
        errors = self.validate()
        if errors:
            raise ValueError("Cannot save invalid scenario:\n" + "\n".join(f"  • {e}" for e in errors))
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
