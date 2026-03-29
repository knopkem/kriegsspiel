"""Lightweight MCTS planner for multi-turn lookahead."""
from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass, field

TIME_BUDGET_SECONDS = 1.0

from core.game import GameState
from core.units import Side, UnitType

from .evaluation import BattlefieldEvaluator


@dataclass
class MCTSNode:
    state: GameState
    side: Side
    parent: MCTSNode | None
    children: list[MCTSNode] = field(default_factory=list)
    visits: int = 0
    total_score: float = 0.0
    untried_actions: list = field(default_factory=list)

    @property
    def ucb1(self) -> float:
        if self.visits == 0:
            return float("inf")
        if self.parent is None or self.parent.visits == 0:
            return self.total_score / self.visits
        exploit = self.total_score / self.visits
        explore = math.sqrt(2 * math.log(self.parent.visits) / self.visits)
        return exploit + explore


class MCTSPlanner:
    """MCTS planner using GameState.advance_turn() as the simulation model.

    Lightweight implementation: instead of full game trees (too slow),
    it evaluates N random "order variations" for a single unit over
    ``lookahead_depth`` turns, scores the resulting position, and returns
    the best order.
    """

    def __init__(
        self,
        side: Side,
        evaluator: BattlefieldEvaluator,
        lookahead_depth: int = 2,
        n_simulations: int = 40,
        rng: random.Random | None = None,
    ) -> None:
        self.side = side
        self.evaluator = evaluator
        self.lookahead_depth = lookahead_depth
        self.n_simulations = n_simulations
        self.rng = rng or random.Random()

    def best_move_destination(
        self,
        game: GameState,
        unit_id: str,
        candidates: list,
    ) -> object | None:
        """Evaluate candidate move destinations via shallow rollout.

        Args:
            game: Current GameState (not modified).
            unit_id: The unit making the move.
            candidates: List of HexCoord destinations to evaluate.

        Returns the HexCoord that maximises expected score after lookahead.
        """
        if not candidates:
            return None

        best_dest = None
        best_score = float("-inf")
        deadline = time.monotonic() + TIME_BUDGET_SECONDS

        for dest in candidates[: self.n_simulations]:
            if time.monotonic() > deadline:
                break
            try:
                score = self._rollout(game, unit_id, dest)
            except Exception:
                continue
            if score > best_score:
                best_score = score
                best_dest = dest

        return best_dest

    def _rollout(self, game: GameState, unit_id: str, destination: object) -> float:
        """Simulate lookahead_depth turns starting from moving unit to destination."""
        state = copy.deepcopy(game)
        unit = state.units.get(unit_id)
        if unit is None or unit.position is None or unit.is_removed:
            return 0.0

        steps = max(1, self.lookahead_depth)
        for _ in range(steps):
            # Issue candidate destination for the evaluated unit each step.
            if not unit.is_removed and unit.position is not None:
                try:
                    state.order_book.issue_move(
                        unit_id, destination, current_turn=state.current_turn
                    )
                except Exception:
                    pass

            # Issue random moves for all other non-commander units (both sides).
            for u in list(state.units.values()):
                if u.is_removed or u.position is None or u.id == unit_id:
                    continue
                if u.unit_type is UnitType.COMMANDER:
                    continue
                neighbors = state.battle_map.neighbors(u.position)
                if neighbors:
                    try:
                        state.order_book.issue_move(
                            u.id,
                            self.rng.choice(neighbors),
                            current_turn=state.current_turn,
                        )
                    except Exception:
                        pass

            try:
                state.advance_turn()
            except Exception:
                break

        return self._score_state(state, self.side)

    def _score_state(self, game: GameState, side: Side) -> float:
        """VP difference: own score minus opponent score."""
        opp = Side.BLUE if side is Side.RED else Side.RED
        return float(game.score_for_side(side) - game.score_for_side(opp))
