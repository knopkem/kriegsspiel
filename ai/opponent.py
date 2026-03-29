"""Rule-based solo opponent."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

from core.game import GameState
from core.orders import Order
from core.units import Formation, MoraleState, Side, Unit, UnitType

from .difficulty import AIDifficulty, AIDifficultyProfile, get_difficulty_profile
from .evaluation import BattlefieldEvaluator
from .strategy import ObjectiveSelector
from .tactics import TacticalPlanner
from .umpire import DigitalUmpire


@dataclass(slots=True)
class SimpleAICommander:
    side: Side
    difficulty: AIDifficulty = AIDifficulty.MEDIUM
    seed: int = 1
    evaluator: BattlefieldEvaluator = field(default_factory=BattlefieldEvaluator)
    strategy: ObjectiveSelector = field(default_factory=ObjectiveSelector)
    umpire: DigitalUmpire = field(default_factory=DigitalUmpire)
    profile: AIDifficultyProfile = field(init=False)
    rng: random.Random = field(init=False)
    tactics: TacticalPlanner = field(init=False)

    def __post_init__(self) -> None:
        self.profile = get_difficulty_profile(self.difficulty)
        self.rng = random.Random(self.seed)
        self.tactics = TacticalPlanner(self.rng)

    def issue_orders(self, game: GameState) -> list[Order]:
        issued: list[Order] = []
        visibility = game.visibility[self.side]
        visible_enemies = [
            game.units[unit_id]
            for unit_id in visibility.visible_enemy_units
            if unit_id in game.units
        ]

        for unit in self._active_units(game):
            if unit.unit_type is UnitType.COMMANDER:
                continue

            order = self._choose_order(game, unit, visible_enemies, visibility.last_known_enemies)
            if order is None:
                continue
            issued.append(self.umpire.sanitize_order(game, order))
        return issued

    def _active_units(self, game: GameState) -> list[Unit]:
        units = [
            unit
            for unit in game.units.values()
            if unit.side is self.side and not unit.is_removed and unit.position is not None
        ]
        return sorted(units, key=lambda unit: (unit.unit_type.value, unit.id))

    def _choose_order(self, game: GameState, unit: Unit, visible_enemies, last_known) -> Order | None:
        if unit.morale_state in {MoraleState.ROUTING, MoraleState.BROKEN} or unit.casualty_ratio >= self.profile.retreat_threshold:
            destination = self.tactics.choose_retreat_destination(game, unit)
            return game.order_book.issue_retreat(unit.id, destination, current_turn=game.current_turn, priority=20)

        target = self.evaluator.best_target(game, unit, visible_enemies)
        if target is not None:
            distance = unit.position.distance_to(target.position)
            if distance <= game.combat_resolver.max_range(unit) or distance <= 1:
                if unit.unit_type is UnitType.ARTILLERY and unit.formation is Formation.LIMBERED:
                    return game.order_book.issue_change_formation(
                        unit.id,
                        Formation.UNLIMBERED,
                        current_turn=game.current_turn,
                        priority=10,
                    )
                return game.order_book.issue_attack(
                    unit.id,
                    target.id,
                    current_turn=game.current_turn,
                    priority=10,
                )

            if unit.unit_type is UnitType.INFANTRY and distance <= 3 and unit.formation is Formation.COLUMN:
                return game.order_book.issue_change_formation(
                    unit.id,
                    Formation.LINE,
                    current_turn=game.current_turn,
                    priority=15,
                )

            destination = self.tactics.choose_approach_destination(game, unit, target.position)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=30)

        if last_known:
            remembered = min(last_known.values(), key=lambda item: unit.position.distance_to(item.position))
            destination = self.tactics.choose_approach_destination(game, unit, remembered.position)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=40)

        objective = self.strategy.choose_focus_objective(game, self.side, unit)
        if objective is not None:
            destination = self.tactics.choose_approach_destination(game, unit, objective.position)
            if unit.unit_type is UnitType.INFANTRY and self.rng.random() < self.profile.random_move_bias:
                neighbors = game.battle_map.neighbors(unit.position)
                if neighbors:
                    destination = self.rng.choice(neighbors)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=50)

        return game.order_book.issue_hold(unit.id, current_turn=game.current_turn, priority=60)
