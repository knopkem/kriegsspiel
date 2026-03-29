"""Replay capture for turn-by-turn inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .map import HexCoord
from .units import MoraleState, Side, Unit


@dataclass(frozen=True, slots=True)
class UnitSnapshot:
    unit_id: str
    name: str
    side: Side
    position: HexCoord | None
    hit_points: int
    morale_state: MoraleState
    fatigue: int
    removed: bool


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    turn: int
    units: Mapping[str, UnitSnapshot]
    scores: Mapping[str, int]
    events: tuple[str, ...]


@dataclass(slots=True)
class ReplayRecorder:
    frames: list[ReplayFrame] = field(default_factory=list)

    def capture(self, *, turn: int, units: Iterable[Unit], scores: Mapping[str, int], events: Iterable[str]) -> None:
        snapshot = {
            unit.id: UnitSnapshot(
                unit_id=unit.id,
                name=unit.name,
                side=unit.side,
                position=unit.position,
                hit_points=unit.hit_points,
                morale_state=unit.morale_state,
                fatigue=unit.fatigue,
                removed=unit.is_removed,
            )
            for unit in units
        }
        self.frames.append(
            ReplayFrame(
                turn=turn,
                units=snapshot,
                scores=dict(scores),
                events=tuple(events),
            )
        )
