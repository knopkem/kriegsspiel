#!/usr/bin/env python3
"""Profile game turn resolution performance."""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

# Ensure the project root is on sys.path when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.difficulty import AIDifficulty
from ai.opponent import SimpleAICommander
from core.game import GameState, VictoryLevel
from core.scenario import load_builtin_scenario
from core.units import Side


def run_profile(scenario_name: str, n_turns: int = 20, quick: bool = False) -> None:
    """Load *scenario_name*, drive both sides with :class:`SimpleAICommander` for
    *n_turns* turns, then print timing and (optionally) cProfile hotspots.
    """
    scenario = load_builtin_scenario(scenario_name)

    if quick:
        game = GameState.from_scenario(scenario, rng_seed=1)
        blue_ai = SimpleAICommander(Side.BLUE, difficulty=AIDifficulty.MEDIUM, seed=1)
        red_ai = SimpleAICommander(Side.RED, difficulty=AIDifficulty.MEDIUM, seed=101)

        start = time.perf_counter()
        for _ in range(n_turns):
            blue_ai.issue_orders(game)
            red_ai.issue_orders(game)
            game.advance_turn()
            if game.victory_report().level is VictoryLevel.DECISIVE:
                break
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"Scenario : {scenario_name}")
        print(f"Turns    : {n_turns}")
        print(f"Total    : {elapsed_ms:.1f} ms")
        print(f"Per turn : {elapsed_ms / n_turns:.2f} ms")
        return

    # ── full cProfile run ────────────────────────────────────────────────────
    game = GameState.from_scenario(scenario, rng_seed=1)
    blue_ai = SimpleAICommander(Side.BLUE, difficulty=AIDifficulty.MEDIUM, seed=1)
    red_ai = SimpleAICommander(Side.RED, difficulty=AIDifficulty.MEDIUM, seed=101)

    pr = cProfile.Profile()
    start = time.perf_counter()
    pr.enable()
    for _ in range(n_turns):
        blue_ai.issue_orders(game)
        red_ai.issue_orders(game)
        game.advance_turn()
        if game.victory_report().level is VictoryLevel.DECISIVE:
            break
    pr.disable()
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Scenario : {scenario_name}")
    print(f"Turns    : {n_turns}")
    print(f"Total    : {elapsed_ms:.1f} ms")
    print(f"Per turn : {elapsed_ms / n_turns:.2f} ms")
    print()
    print("Top 10 hotspots:")
    print("-" * 60)
    sio = io.StringIO()
    ps = pstats.Stats(pr, stream=sio).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(10)
    print(sio.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile game turn resolution performance.")
    parser.add_argument("--scenario", default="full_battle", help="Scenario name (default: full_battle)")
    parser.add_argument("--turns", type=int, default=20, help="Number of turns to simulate (default: 20)")
    parser.add_argument("--quick", action="store_true", help="Skip profiler, just print elapsed time")
    args = parser.parse_args()
    run_profile(args.scenario, args.turns, args.quick)
