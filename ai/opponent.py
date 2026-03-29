"""Rule-based solo opponent."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import TYPE_CHECKING

from core.game import GameState
from core.map import HexCoord, TerrainType
from core.orders import Order
from core.units import Formation, MoraleState, Side, Unit, UnitType

from .belief import BeliefMap
from .difficulty import AIDifficulty, AIDifficultyProfile, get_difficulty_profile
from .evaluation import BattlefieldEvaluator
from .strategy import ObjectiveSelector
from .tactics import ReserveManager, TacticalPlanner
from .umpire import DigitalUmpire

if TYPE_CHECKING:
    from .mcts import MCTSPlanner


@dataclass(slots=True)
class SimpleAICommander:
    side: Side
    difficulty: AIDifficulty = AIDifficulty.MEDIUM
    seed: int = 1
    evaluator: BattlefieldEvaluator = field(default_factory=BattlefieldEvaluator)
    strategy: ObjectiveSelector = field(default_factory=ObjectiveSelector)
    umpire: DigitalUmpire = field(default_factory=DigitalUmpire)
    belief_map: BeliefMap = field(default_factory=BeliefMap)
    profile: AIDifficultyProfile = field(init=False)
    rng: random.Random = field(init=False)
    tactics: TacticalPlanner = field(init=False)
    reserve_manager: ReserveManager = field(init=False)
    mcts: MCTSPlanner | None = field(init=False)

    def __post_init__(self) -> None:
        self.profile = get_difficulty_profile(self.difficulty)
        self.rng = random.Random(self.seed)
        self.tactics = TacticalPlanner(self.rng)
        self.reserve_manager = ReserveManager()
        self.mcts = None
        if self.profile.lookahead_depth > 0:
            from .mcts import MCTSPlanner as _MCTSPlanner
            n_sim = 20 if self.difficulty is AIDifficulty.MEDIUM else 40
            self.mcts = _MCTSPlanner(
                self.side,
                self.evaluator,
                lookahead_depth=self.profile.lookahead_depth,
                n_simulations=n_sim,
                rng=self.rng,
            )

    def issue_orders(self, game: GameState) -> list[Order]:
        issued: list[Order] = []
        visibility = game.visibility[self.side]
        visible_enemies = [
            game.units[unit_id]
            for unit_id in visibility.visible_enemy_units
            if unit_id in game.units
        ]

        if self.profile.use_belief_map:
            self.belief_map.update(visibility, game.current_turn)

        active_units = self._active_units(game)

        focus_assignments: dict[str, Unit] = {}
        if self.profile.use_focus_fire and visible_enemies:
            non_cmdr = [u for u in active_units if u.unit_type is not UnitType.COMMANDER]
            focus_assignments = self.tactics.assign_targets(
                non_cmdr, visible_enemies, self.evaluator,
                use_morale_exploitation=True,
            )

        for unit in active_units:
            game.order_book.cancel_future_orders_for_unit(unit.id, from_turn=game.current_turn)
            if unit.unit_type is UnitType.COMMANDER:
                continue

        # D6: Reserve management — extended to all combat unit types
            if self.profile.use_focus_fire:
                if not self.reserve_manager.should_commit(unit, game, active_units):
                    reserve_pos = self.reserve_manager.reserve_position(unit, game)
                    if reserve_pos is not None:
                        destination = self.tactics.choose_approach_destination(
                            game, unit, reserve_pos
                        )
                        order = game.order_book.issue_move(
                            unit.id,
                            destination,
                            current_turn=game.current_turn,
                            priority=50,
                        )
                        issued.append(self.umpire.sanitize_order(game, order))
                        continue

            order = self._choose_order(game, unit, visible_enemies, visibility.last_known_enemies, focus_assignments)
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

    def _choose_order(
        self,
        game: GameState,
        unit: Unit,
        visible_enemies: list[Unit],
        last_known,
        focus_assignments: dict[str, Unit] | None = None,
    ) -> Order | None:
        if unit.morale_state in {MoraleState.ROUTING, MoraleState.BROKEN} or unit.casualty_ratio >= self.profile.retreat_threshold:
            friendly_units = [
                u for u in game.units.values()
                if u.side is unit.side and not u.is_removed and u.position is not None
            ]
            destination = self.tactics.choose_retreat_destination(
                unit, game.battle_map, self.evaluator, visible_enemies,
                friendlies=friendly_units,
            )
            return game.order_book.issue_retreat(unit.id, destination, current_turn=game.current_turn, priority=20)

        # Get target: use focus-fire assignment when available, else best_target
        if focus_assignments and unit.id in focus_assignments:
            target = focus_assignments[unit.id]
        else:
            target = self.evaluator.best_target(
                unit, visible_enemies,
                use_morale_exploitation=self.profile.use_focus_fire,
            )

        # D8: Infantry vs steady fortified enemy — only attack if 3:1 advantage
        if (
            target is not None
            and unit.unit_type is UnitType.INFANTRY
            and target.morale_state is MoraleState.STEADY
            and target.position is not None
            and game.battle_map.terrain_at(target.position) is TerrainType.FORTIFICATION
            and unit.current_strength < 3 * target.current_strength
        ):
            other_targets = [e for e in visible_enemies if e is not target]
            target = self.evaluator.best_target(unit, other_targets) if other_targets else None

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

            # Role-specific approach destination
            approach_dest = target.position

            # I2: Compute enemy centroid for role decisions
            enemy_centroid: HexCoord | None = None
            if visible_enemies:
                eq = sum(e.position.q for e in visible_enemies if e.position) / len(visible_enemies)
                er = sum(e.position.r for e in visible_enemies if e.position) / len(visible_enemies)
                enemy_centroid = HexCoord(int(round(eq)), int(round(er)))

            if self.profile.use_flanking and unit.unit_type is UnitType.CAVALRY:
                flank = self.tactics.cavalry_flanking_destination(unit, visible_enemies, game.battle_map)
                if flank is not None:
                    approach_dest = flank
            elif self.profile.use_terrain_scoring and unit.unit_type is UnitType.ARTILLERY:
                arty = self.tactics.artillery_deployment_hex(unit, game.battle_map, visible_enemies)
                if arty is not None:
                    approach_dest = arty
            elif unit.unit_type is UnitType.SKIRMISHER:
                skr = self.tactics.skirmisher_harassment_hex(unit, visible_enemies, game.battle_map)
                if skr is not None:
                    approach_dest = skr
            elif unit.unit_type is UnitType.INFANTRY and self.profile.use_terrain_scoring:
                hold = self.tactics.infantry_hold_hex(unit, game.battle_map, enemy_centroid)
                if hold is not None and game.battle_map.terrain_at(hold).value in ("hill", "fortification", "village", "forest"):
                    approach_dest = hold

            # D5: MCTS refinement for ARTILLERY/CAVALRY
            if self.mcts is not None and unit.unit_type in {UnitType.ARTILLERY, UnitType.CAVALRY}:
                candidates: list[HexCoord] = [approach_dest]
                candidates += game.battle_map.neighbors(unit.position)[:3]
                # Deduplicate while preserving order
                seen: set[tuple[int, int]] = set()
                unique: list[HexCoord] = []
                for c in candidates:
                    key = (c.q, c.r)
                    if key not in seen:
                        seen.add(key)
                        unique.append(c)
                best = self.mcts.best_move_destination(game, unit.id, unique)
                if best is not None:
                    approach_dest = best

            destination = self.tactics.choose_approach_destination(game, unit, approach_dest)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=30)

        if last_known:
            remembered = min(last_known.values(), key=lambda item: unit.position.distance_to(item.position))
            destination = self.tactics.choose_approach_destination(game, unit, remembered.position)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=40)

        # D10: Belief map fallback when no visible/known enemies
        if self.profile.use_belief_map:
            estimated = self.belief_map.estimated_enemies(min_confidence=0.2)
            if estimated:
                best_belief = estimated[0]
                dest = best_belief.estimated_pos
                if not game.battle_map.in_bounds(dest):
                    dest = best_belief.last_known_pos
                destination = self.tactics.choose_approach_destination(game, unit, dest)
                return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=45)

        objective = self.strategy.choose_focus_objective(game, self.side, unit)
        if objective is not None:
            destination = self.tactics.choose_approach_destination(game, unit, objective.position)
            if unit.unit_type is UnitType.INFANTRY and self.rng.random() < self.profile.random_move_bias:
                neighbors = game.battle_map.neighbors(unit.position)
                if neighbors:
                    destination = self.rng.choice(neighbors)
            return game.order_book.issue_move(unit.id, destination, current_turn=game.current_turn, priority=50)

        return game.order_book.issue_hold(unit.id, current_turn=game.current_turn, priority=60)
