"""Difficulty profiles for the simple AI opponent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class AIDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    HISTORICAL = "historical"


@dataclass(frozen=True, slots=True)
class AIDifficultyProfile:
    aggression: float = 1.0
    retreat_threshold: float = 0.28
    random_move_bias: float = 0.1
    objective_bias: float = 1.0
    use_flanking: bool = True
    use_focus_fire: bool = True
    use_terrain_scoring: bool = True
    use_belief_map: bool = True
    lookahead_depth: int = 0


DIFFICULTY_PROFILES: dict[AIDifficulty, AIDifficultyProfile] = {
    AIDifficulty.EASY: AIDifficultyProfile(
        aggression=0.8, retreat_threshold=0.3, random_move_bias=0.3, objective_bias=0.9,
        use_flanking=False, use_focus_fire=False, use_terrain_scoring=False, use_belief_map=False,
    ),
    AIDifficulty.MEDIUM: AIDifficultyProfile(
        aggression=1.0, retreat_threshold=0.28, random_move_bias=0.1, objective_bias=1.0,
        use_flanking=True, use_focus_fire=False, use_terrain_scoring=True, use_belief_map=False,
    ),
    AIDifficulty.HARD: AIDifficultyProfile(
        aggression=1.1, retreat_threshold=0.22, random_move_bias=0.05, objective_bias=1.15,
        use_flanking=True, use_focus_fire=True, use_terrain_scoring=True, use_belief_map=True,
    ),
    AIDifficulty.HISTORICAL: AIDifficultyProfile(
        aggression=1.0, retreat_threshold=0.28, random_move_bias=0.15, objective_bias=1.1,
        use_flanking=True, use_focus_fire=True, use_terrain_scoring=True, use_belief_map=True,
    ),
}


def get_difficulty_profile(difficulty: AIDifficulty | str) -> AIDifficultyProfile:
    return DIFFICULTY_PROFILES[AIDifficulty(difficulty)]


@dataclass
class AdaptiveController:
    """Tracks player performance and nudges AI difficulty up or down."""

    win_history: list[bool] = field(default_factory=list)
    base_difficulty: AIDifficulty = AIDifficulty.MEDIUM

    _LEVELS: tuple[AIDifficulty, ...] = field(
        default=(
            AIDifficulty.EASY,
            AIDifficulty.MEDIUM,
            AIDifficulty.HARD,
            AIDifficulty.HISTORICAL,
        ),
        init=False,
        repr=False,
        compare=False,
    )

    def record_result(self, player_won: bool) -> None:
        """Record whether the player won the most recent game."""
        self.win_history.append(player_won)

    def current_difficulty(self) -> AIDifficulty:
        """Return difficulty adjusted for recent results.

        - Last 3 all player wins  → one level harder than base.
        - Last 3 all player losses → one level easier than base.
        - Mixed results            → base difficulty.
        """
        levels = self._LEVELS
        base_idx = levels.index(self.base_difficulty)
        if len(self.win_history) >= 3:
            last3 = self.win_history[-3:]
            if all(last3):
                return levels[min(base_idx + 1, len(levels) - 1)]
            if not any(last3):
                return levels[max(base_idx - 1, 0)]
        return self.base_difficulty

    def save(self, path: str | Path) -> None:
        """Persist win history and base difficulty to a JSON file."""
        data = {
            "win_history": self.win_history,
            "base_difficulty": str(self.base_difficulty),
        }
        Path(path).write_text(json.dumps(data))

    @classmethod
    def load(cls, path: str | Path) -> AdaptiveController:
        """Load an AdaptiveController from a previously saved JSON file."""
        data = json.loads(Path(path).read_text())
        return cls(
            win_history=data["win_history"],
            base_difficulty=AIDifficulty(data["base_difficulty"]),
        )


