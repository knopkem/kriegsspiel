"""Adaptive difficulty controller backed by persistent match stats."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .difficulty import AIDifficulty

DEFAULT_STATS_PATH = Path.home() / ".kriegsspiel" / "stats.json"

_LEVELS: tuple[AIDifficulty, ...] = (
    AIDifficulty.EASY,
    AIDifficulty.MEDIUM,
    AIDifficulty.HARD,
    AIDifficulty.HISTORICAL,
)


@dataclass
class AdaptiveController:
    """Tracks match results and recommends adaptive difficulty adjustments.

    Results are persisted to ``~/.kriegsspiel/stats.json`` by default.
    """

    results: list[dict[str, Any]] = field(default_factory=list)
    difficulty: AIDifficulty = AIDifficulty.MEDIUM
    stats_path: Path = field(default_factory=lambda: DEFAULT_STATS_PATH)

    def record_result(self, winner: str, scenario: str, turns: int) -> None:
        """Append a completed match result."""
        self.results.append({"winner": winner, "scenario": scenario, "turns": turns})

    def get_recommended_difficulty(self) -> str:
        """Return a recommended difficulty string based on the last 3 results.

        - All 3 won by player (blue) → step up one level.
        - All 3 lost by player      → step down one level.
        - Mixed                      → keep current.
        """
        if len(self.results) < 3:
            return str(self.difficulty)
        last3 = self.results[-3:]
        player_wins = [r["winner"] == "blue" for r in last3]
        idx = _LEVELS.index(AIDifficulty(str(self.difficulty)))
        if all(player_wins):
            return str(_LEVELS[min(idx + 1, len(_LEVELS) - 1)])
        if not any(player_wins):
            return str(_LEVELS[max(idx - 1, 0)])
        return str(self.difficulty)

    def get_difficulty(self) -> str:
        """Return current difficulty as a string."""
        return str(self.difficulty)

    def save(self) -> None:
        """Persist stats to ``stats_path`` (creates parent directories as needed)."""
        path = Path(self.stats_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "results": self.results,
            "difficulty": str(self.difficulty),
        }
        path.write_text(json.dumps(data))

    @classmethod
    def load(cls, path: Path | str | None = None) -> AdaptiveController:
        """Load an AdaptiveController from *path* (defaults to DEFAULT_STATS_PATH).

        Returns a fresh controller if the file does not exist yet.
        """
        p = Path(path) if path is not None else DEFAULT_STATS_PATH
        if not p.exists():
            return cls(stats_path=p)
        data = json.loads(p.read_text())
        return cls(
            results=data.get("results", []),
            difficulty=AIDifficulty(data.get("difficulty", str(AIDifficulty.MEDIUM))),
            stats_path=p,
        )
