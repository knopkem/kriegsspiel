"""Difficulty profiles for the simple AI opponent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AIDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    HISTORICAL = "historical"


@dataclass(frozen=True, slots=True)
class AIDifficultyProfile:
    aggression: float
    retreat_threshold: float
    random_move_bias: float
    objective_bias: float


DIFFICULTY_PROFILES: dict[AIDifficulty, AIDifficultyProfile] = {
    AIDifficulty.EASY: AIDifficultyProfile(aggression=0.8, retreat_threshold=0.35, random_move_bias=0.3, objective_bias=0.9),
    AIDifficulty.MEDIUM: AIDifficultyProfile(aggression=1.0, retreat_threshold=0.28, random_move_bias=0.15, objective_bias=1.0),
    AIDifficulty.HARD: AIDifficultyProfile(aggression=1.15, retreat_threshold=0.22, random_move_bias=0.05, objective_bias=1.15),
    AIDifficulty.HISTORICAL: AIDifficultyProfile(aggression=0.95, retreat_threshold=0.3, random_move_bias=0.08, objective_bias=1.1),
}


def get_difficulty_profile(difficulty: AIDifficulty | str) -> AIDifficultyProfile:
    return DIFFICULTY_PROFILES[AIDifficulty(difficulty)]

