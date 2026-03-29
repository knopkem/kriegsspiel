"""Batch AI-vs-AI playtesting for balance checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.game import GameState, VictoryLevel
from core.scenario import load_builtin_scenario
from core.units import Side, UnitType

from .difficulty import AIDifficulty
from .opponent import SimpleAICommander


@dataclass(frozen=True)
class PlaytestResult:
    scenario_name: str
    games_played: int
    blue_wins: int
    red_wins: int
    draws: int
    avg_turns: float
    avg_blue_units_remaining: float
    avg_red_units_remaining: float

    @property
    def win_rate_blue(self) -> float:
        """Fraction of games won by Blue."""
        return self.blue_wins / self.games_played if self.games_played > 0 else 0.0

    @property
    def balance_score(self) -> float:
        """Distance from 50/50; 0.0 = perfectly balanced, 0.5 = one side always wins."""
        return abs(self.win_rate_blue - 0.5)


@dataclass(slots=True)
class BalancePlaytester:
    scenario_names: tuple[str, ...]
    games_per_scenario: int = 10
    turn_limit: int = 8
    difficulty: AIDifficulty = AIDifficulty.MEDIUM

    def run(self) -> list[PlaytestResult]:
        results: list[PlaytestResult] = []
        seed = 1
        for scenario_name in self.scenario_names:
            blue_wins = 0
            red_wins = 0
            draws = 0
            total_turns = 0
            total_blue_remaining = 0
            total_red_remaining = 0

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
                if report.winner is Side.BLUE:
                    blue_wins += 1
                elif report.winner is Side.RED:
                    red_wins += 1
                else:
                    draws += 1

                total_turns += turns
                total_blue_remaining += sum(
                    1 for u in game.units.values()
                    if u.side is Side.BLUE
                    and not u.is_removed
                    and u.unit_type is not UnitType.COMMANDER
                )
                total_red_remaining += sum(
                    1 for u in game.units.values()
                    if u.side is Side.RED
                    and not u.is_removed
                    and u.unit_type is not UnitType.COMMANDER
                )
                seed += 1

            n = self.games_per_scenario
            results.append(
                PlaytestResult(
                    scenario_name=scenario_name,
                    games_played=n,
                    blue_wins=blue_wins,
                    red_wins=red_wins,
                    draws=draws,
                    avg_turns=total_turns / n,
                    avg_blue_units_remaining=total_blue_remaining / n,
                    avg_red_units_remaining=total_red_remaining / n,
                )
            )
        return results


def generate_balance_report(results: list[PlaytestResult]) -> str:
    """Return a formatted text table summarising balance across scenarios.

    Scenarios with ``balance_score < 0.15`` are marked ★ (well-balanced).
    """
    header = (
        f"{'Scenario':<20} | {'Games':>5} | {'Blue%':>5} | {'Red%':>5} |"
        f" {'Draw%':>5} | {'AvgTurns':>8} | Balance"
    )
    separator = "-" * len(header)
    rows = [header, separator]
    for r in results:
        n = r.games_played
        blue_pct = f"{r.win_rate_blue * 100:.0f}%"
        red_pct = f"{r.red_wins / n * 100:.0f}%"
        draw_pct = f"{r.draws / n * 100:.0f}%"
        star = " ★" if r.balance_score < 0.15 else ""
        rows.append(
            f"{r.scenario_name:<20} | {n:>5} |"
            f" {blue_pct:>5} | {red_pct:>5} |"
            f" {draw_pct:>5} | {r.avg_turns:>8.1f} |"
            f" {r.balance_score:.2f}{star}"
        )
    return "\n".join(rows)
