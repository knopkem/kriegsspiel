"""Turn engine and game-state orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Iterable

from .combat import CombatResolver
from .fog_of_war import FogOfWarEngine, VisibilitySnapshot
from .map import HexCoord, HexGridMap
from .messenger import MessengerSystem
from .orders import Order, OrderBook, OrderType
from .replay import ReplayRecorder
from .scenario import Scenario
from .units import MoraleState, Side, Unit, UnitType


@dataclass(frozen=True, slots=True)
class GameEvent:
    turn: int
    category: str
    message: str


class VictoryLevel(StrEnum):
    DECISIVE = "decisive"
    MARGINAL = "marginal"
    DRAW = "draw"


@dataclass(frozen=True, slots=True)
class VictoryReport:
    winner: Side | None
    level: VictoryLevel
    blue_score: int
    red_score: int
    margin: int


@dataclass(slots=True)
class GameState:
    battle_map: HexGridMap
    units: dict[str, Unit]
    order_book: OrderBook = field(default_factory=OrderBook)
    current_turn: int = 1
    rng_seed: int = 1
    objectives: tuple = ()
    fog_engine: FogOfWarEngine | None = None
    messenger_system: MessengerSystem | None = None
    combat_resolver: CombatResolver | None = None
    event_log: list[GameEvent] = field(default_factory=list)
    visibility: dict[Side, VisibilitySnapshot] = field(default_factory=dict)
    replay: ReplayRecorder = field(default_factory=ReplayRecorder)

    def __post_init__(self) -> None:
        rng = random.Random(self.rng_seed)
        if self.fog_engine is None:
            self.fog_engine = FogOfWarEngine(self.battle_map)
        if self.messenger_system is None:
            self.messenger_system = MessengerSystem(self.battle_map)
        if self.combat_resolver is None:
            self.combat_resolver = CombatResolver(rng=rng)
        self.visibility = self.fog_engine.update(self.units.values(), current_turn=self.current_turn)
        self.replay.capture(
            turn=self.current_turn,
            units=self.units.values(),
            scores=self._score_map(),
            events=("Initial deployment",),
        )

    @classmethod
    def from_scenario(cls, scenario: Scenario, *, rng_seed: int = 1) -> "GameState":
        return cls(
            battle_map=scenario.build_map(),
            units=scenario.build_units(),
            current_turn=scenario.starting_turn,
            rng_seed=rng_seed,
            objectives=scenario.objectives,
        )

    def advance_turn(self) -> list[GameEvent]:
        ready_orders = self.order_book.release_orders(self.current_turn)
        turn_events: list[GameEvent] = []

        formation_orders = [o for o in ready_orders if o.order_type is OrderType.CHANGE_FORMATION]
        movement_orders = [o for o in ready_orders if o.order_type in {OrderType.MOVE, OrderType.RETREAT}]
        hold_orders = [o for o in ready_orders if o.order_type is OrderType.HOLD]
        rally_orders = [o for o in ready_orders if o.order_type is OrderType.RALLY]
        attack_orders = [o for o in ready_orders if o.order_type is OrderType.ATTACK]

        turn_events.extend(self._resolve_formation_orders(formation_orders))
        turn_events.extend(self._resolve_movement_orders(movement_orders))
        turn_events.extend(self._resolve_hold_orders(hold_orders))
        turn_events.extend(self._resolve_rally_orders(rally_orders))
        turn_events.extend(self._resolve_attack_orders(attack_orders))

        self.visibility = self.fog_engine.update(self.units.values(), current_turn=self.current_turn)
        self.event_log.extend(turn_events)
        self.replay.capture(
            turn=self.current_turn,
            units=self.units.values(),
            scores=self._score_map(),
            events=(event.message for event in turn_events),
        )
        self.current_turn += 1
        return turn_events

    def score_for_side(self, side: Side) -> int:
        score = 0
        for objective in self.objectives:
            occupying = [unit for unit in self.units_at(objective.position) if unit.side is side and not unit.is_removed]
            if occupying:
                score += objective.points
        enemy_losses = sum(unit.max_hit_points - unit.hit_points for unit in self.units.values() if unit.side is not side)
        score += enemy_losses // 10
        return score

    def victory_report(self) -> VictoryReport:
        blue_score = self.score_for_side(Side.BLUE)
        red_score = self.score_for_side(Side.RED)
        margin = abs(blue_score - red_score)

        blue_field_units = any(
            unit.side is Side.BLUE and unit.unit_type is not UnitType.COMMANDER and not unit.is_removed
            for unit in self.units.values()
        )
        red_field_units = any(
            unit.side is Side.RED and unit.unit_type is not UnitType.COMMANDER and not unit.is_removed
            for unit in self.units.values()
        )

        if not blue_field_units and not red_field_units:
            return VictoryReport(None, VictoryLevel.DRAW, blue_score, red_score, margin)
        if not red_field_units:
            return VictoryReport(Side.BLUE, VictoryLevel.DECISIVE, blue_score, red_score, margin)
        if not blue_field_units:
            return VictoryReport(Side.RED, VictoryLevel.DECISIVE, blue_score, red_score, margin)

        if margin >= 12:
            winner = Side.BLUE if blue_score > red_score else Side.RED
            return VictoryReport(winner, VictoryLevel.DECISIVE, blue_score, red_score, margin)
        if margin >= 5:
            winner = Side.BLUE if blue_score > red_score else Side.RED
            return VictoryReport(winner, VictoryLevel.MARGINAL, blue_score, red_score, margin)
        return VictoryReport(None, VictoryLevel.DRAW, blue_score, red_score, margin)

    def units_at(self, coord: HexCoord) -> list[Unit]:
        return [
            unit
            for unit in self.units.values()
            if unit.position == coord and not unit.is_removed
        ]

    def friendly_commander_support(self, unit: Unit) -> bool:
        for other in self.units.values():
            if other.side is not unit.side or other.unit_type is not UnitType.COMMANDER:
                continue
            if other.position is None or unit.position is None or other.is_removed:
                continue
            if other.position.distance_to(unit.position) <= other.commander_radius:
                return True
        return False

    def _resolve_formation_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            unit = self.units[order.unit_id]
            unit.change_formation(order.formation)
            unit.add_fatigue(2)
            self.order_book.mark_resolved(order.order_id)
            events.append(GameEvent(self.current_turn, "formation", f"{unit.name} forms {unit.formation.value}."))
        return events

    def _resolve_movement_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            unit = self.units[order.unit_id]
            if unit.position is None or unit.is_removed:
                self.order_book.mark_resolved(order.order_id)
                continue

            path = self.battle_map.find_path(unit.position, order.destination, terrain_costs=unit.movement_costs())
            destination = self._reachable_destination(unit, path)
            if destination != unit.position:
                moved_hexes = unit.position.distance_to(destination)
                unit.position = destination
                fatigue_cost = max(4, moved_hexes * (6 if order.order_type is OrderType.RETREAT else 5))
                unit.add_fatigue(fatigue_cost)
                events.append(GameEvent(self.current_turn, "movement", f"{unit.name} moves to {destination}."))
            else:
                events.append(GameEvent(self.current_turn, "movement", f"{unit.name} holds position; no path or movement budget."))
            self.order_book.mark_resolved(order.order_id)
        return events

    def _resolve_hold_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            unit = self.units[order.unit_id]
            unit.recover_fatigue(10)
            self.order_book.mark_resolved(order.order_id)
            events.append(GameEvent(self.current_turn, "hold", f"{unit.name} holds and recovers fatigue."))
        return events

    def _resolve_rally_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            unit = self.units[order.unit_id]
            if unit.morale_state is MoraleState.STEADY:
                message = f"{unit.name} is already steady."
            elif unit.morale_state is MoraleState.BROKEN:
                message = f"{unit.name} is broken and cannot rally."
            else:
                chance = 0.55
                if self.friendly_commander_support(unit):
                    chance += 0.2
                if unit.fatigue >= 70:
                    chance -= 0.15
                success = random.Random(self.rng_seed + self.current_turn + len(self.event_log)).random() < chance
                if success:
                    unit.improve_morale(1)
                    unit.recover_fatigue(6)
                    message = f"{unit.name} rallies to {unit.morale_state.value}."
                else:
                    unit.add_fatigue(3)
                    message = f"{unit.name} fails to rally."
            self.order_book.mark_resolved(order.order_id)
            events.append(GameEvent(self.current_turn, "rally", message))
        return events

    def _resolve_attack_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            attacker = self.units[order.unit_id]
            defender = self.units[order.target_unit_id]
            if attacker.is_removed or defender.is_removed or attacker.position is None or defender.position is None:
                self.order_book.mark_resolved(order.order_id)
                continue

            distance = attacker.position.distance_to(defender.position)
            if distance > self.combat_resolver.max_range(attacker) and distance > 1:
                events.append(GameEvent(self.current_turn, "combat", f"{attacker.name} cannot reach {defender.name}."))
                self.order_book.mark_resolved(order.order_id)
                continue

            result = self.combat_resolver.resolve_attack(
                attacker,
                defender,
                distance_hexes=distance,
                defender_terrain=self.battle_map.terrain_at(defender.position),
            )
            self.order_book.mark_resolved(order.order_id)
            events.append(GameEvent(self.current_turn, "combat", result.summary))
        return events

    def _reachable_destination(self, unit: Unit, path: list[HexCoord]) -> HexCoord:
        if not path:
            return unit.position

        budget = unit.turn_movement_budget()
        spent = 0.0
        current = path[0]
        terrain_costs = unit.movement_costs()

        for step in path[1:]:
            step_cost = self.battle_map.movement_cost(step, terrain_costs) * 100
            if spent + step_cost > budget:
                break

            enemy_present = any(occupant.side is not unit.side for occupant in self.units_at(step))
            if enemy_present:
                break

            spent += step_cost
            current = step
        return current

    def _score_map(self) -> dict[str, int]:
        return {
            Side.BLUE.value: self.score_for_side(Side.BLUE),
            Side.RED.value: self.score_for_side(Side.RED),
        }
