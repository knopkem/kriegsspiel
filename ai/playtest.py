"""Batch AI-vs-AI playtesting for balance checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.game import GameState, VictoryLevel
from core.scenario import load_builtin_scenario
from core.units import Side

from .difficulty import AIDifficulty
from .opponent import SimpleAICommander


@dataclass(frozen=True, slots=True)
class PlaytestResult:
    scenario_name: str
    winner: str | None
    victory_level: str
    blue_score: int
    red_score: int
    turns_played: int


@dataclass(slots=True)
class BalancePlaytester:
    scenario_names: tuple[str, ...]
    games_per_scenario: int = 1
    turn_limit: int = 8
    difficulty: AIDifficulty = AIDifficulty.MEDIUM

    def run(self) -> list[PlaytestResult]:
        results: list[PlaytestResult] = []
        seed = 1
        for scenario_name in self.scenario_names:
            for _ in range(self.games_per_scenario):
                scenario = load_builtin_scenario(scenario_name)
                game = GameState.from_scenario(scenario, rng_seed=seed)
                blue_ai = SimpleAICommander(Side.BLUE, difficulty=self.difficulty, seed=seed)
                red_ai = SimpleAICommander(Side.RED, difficulty=self.difficulty, seed=seed + 100)

                turns = 0
                while turns < self.turn_limit:
                    blue_ai.issue_orders(game)
                    red_ai.issue_orders(game)
                    game.advance_turn()
                    turns += 1
                    report = game.victory_report()
                    if report.level is VictoryLevel.DECISIVE:
                        break

                report = game.victory_report()
                winner = report.winner.value if report.winner is not None else None
                results.append(
                    PlaytestResult(
                        scenario_name=scenario_name,
                        winner=winner,
                        victory_level=report.level.value,
                        blue_score=report.blue_score,
                        red_score=report.red_score,
                        turns_played=turns,
                    )
                )
                seed += 1
        return results
