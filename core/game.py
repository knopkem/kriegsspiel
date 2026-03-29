"""Turn engine and game-state orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Iterable

from .combat import AttackKind, CombatResolver
from .fog_of_war import FogOfWarEngine, VisibilitySnapshot
from .map import HexCoord, HexGridMap, TerrainType
from .messenger import MessengerSystem, is_intercepted
from .orders import Order, OrderBook, OrderType
from .replay import ReplayRecorder
from .scenario import Scenario
from .units import CommanderAbility, MoraleState, Side, Unit, UnitType
from .weather import TimeOfDay, WeatherState


@dataclass(frozen=True, slots=True)
class GameEvent:
    turn: int
    category: str
    message: str
    coord: "HexCoord | None" = None


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


@dataclass(frozen=True, slots=True)
class ReinforcementWave:
    """A batch of units that arrives at the battlefield on a specified turn."""

    turn: int
    units: list[Unit]
    entry_coords: list[HexCoord]


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
    reinforcements: list[ReinforcementWave] = field(default_factory=list)
    weather: WeatherState = field(default_factory=WeatherState)
    score_history: list[tuple[int, int]] = field(default_factory=list)
    max_turns: int | None = None

    def __post_init__(self) -> None:
        rng = random.Random(self.rng_seed)
        if self.fog_engine is None:
            self.fog_engine = FogOfWarEngine(self.battle_map)
        if self.messenger_system is None:
            self.messenger_system = MessengerSystem(self.battle_map)
        if self.combat_resolver is None:
            self.combat_resolver = CombatResolver(rng=rng)
        self.visibility = self.fog_engine.update(
            self.units.values(),
            current_turn=self.current_turn,
            visibility_modifier=self.weather.visibility_range_modifier,
        )
        self.replay.capture(
            turn=self.current_turn,
            units=self.units.values(),
            scores=self._score_map(),
            events=("Initial deployment",),
        )

    @classmethod
    def from_scenario(cls, scenario: Scenario, *, rng_seed: int = 1) -> "GameState":
        from .units import (
            make_artillery_battery,
            make_cavalry_squadron,
            make_commander,
            make_infantry_half_battalion,
            make_skirmisher_detachment,
            make_supply_wagon,
            Side,
        )

        builders = {
            "infantry": make_infantry_half_battalion,
            "cavalry": make_cavalry_squadron,
            "artillery": make_artillery_battery,
            "skirmisher": make_skirmisher_detachment,
            "commander": make_commander,
            "supply_wagon": make_supply_wagon,
        }

        waves: list[ReinforcementWave] = []
        for wave_data in scenario.reinforcements:
            wave_units: list[Unit] = []
            for unit_spec in wave_data["units"]:
                builder = builders[unit_spec["type"]]
                unit_side = Side(unit_spec["side"])
                kwargs: dict = {}
                if unit_spec["type"] == "commander":
                    kwargs["command_radius"] = unit_spec.get("command_radius", 6)
                wave_units.append(builder(unit_spec["id"], unit_spec["name"], unit_side, **kwargs))
            entry_coords = [HexCoord(*c) for c in wave_data["entry_coords"]]
            waves.append(ReinforcementWave(turn=wave_data["turn"], units=wave_units, entry_coords=entry_coords))

        return cls(
            battle_map=scenario.build_map(),
            units=scenario.build_units(),
            current_turn=scenario.starting_turn,
            rng_seed=rng_seed,
            objectives=scenario.objectives,
            reinforcements=waves,
            max_turns=scenario.max_turns,
        )

    def advance_turn(self) -> list[GameEvent]:
        for unit in self.units.values():
            unit.last_stand_active = False
            unit.charged = False

        previous_positions: dict[str, HexCoord | None] = {
            uid: unit.position for uid, unit in self.units.items()
        }

        ready_orders = self.order_book.release_orders(self.current_turn)
        turn_events: list[GameEvent] = []

        ability_orders = [o for o in ready_orders if o.order_type is OrderType.COMMANDER_ABILITY]
        formation_orders = [o for o in ready_orders if o.order_type is OrderType.CHANGE_FORMATION]
        movement_orders = [o for o in ready_orders if o.order_type in {OrderType.MOVE, OrderType.RETREAT}]
        hold_orders = [o for o in ready_orders if o.order_type is OrderType.HOLD]
        rally_orders = [o for o in ready_orders if o.order_type is OrderType.RALLY]
        attack_orders = [o for o in ready_orders if o.order_type is OrderType.ATTACK]

        turn_events.extend(self._resolve_commander_ability_orders(ability_orders))
        turn_events.extend(self._resolve_formation_orders(formation_orders))
        turn_events.extend(self._resolve_movement_orders(movement_orders))
        turn_events.extend(self._resolve_hold_orders(hold_orders))
        turn_events.extend(self._resolve_rally_orders(rally_orders))
        turn_events.extend(self._resolve_attack_orders(attack_orders, previous_positions))

        turn_events.extend(self._process_reinforcements())

        self.visibility = self.fog_engine.update(
            self.units.values(),
            current_turn=self.current_turn,
            visibility_modifier=self.weather.visibility_range_modifier,
        )
        self._apply_supply_recovery()
        self.weather.advance(random.Random(self.rng_seed + self.current_turn))
        self.event_log.extend(turn_events)
        self.replay.capture(
            turn=self.current_turn,
            units=self.units.values(),
            scores=self._score_map(),
            events=(event.message for event in turn_events),
        )
        self.score_history.append((
            self.score_for_side(Side.BLUE),
            self.score_for_side(Side.RED),
        ))
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
                unit.consecutive_hold_turns = 0
                fatigue_cost = max(4, moved_hexes * (6 if order.order_type is OrderType.RETREAT else 5))
                unit.add_fatigue(fatigue_cost)
                events.append(GameEvent(self.current_turn, "movement", f"{unit.name} moves to {destination}.", coord=destination))
                if destination != order.destination:
                    self.order_book.issue(
                        order.order_type,
                        unit.id,
                        current_turn=self.current_turn,
                        delay_turns=1,
                        priority=order.priority,
                        destination=order.destination,
                        notes=order.notes,
                        replace_existing_from_turn=self.current_turn + 1,
                    )
            else:
                events.append(GameEvent(self.current_turn, "movement", f"{unit.name} holds position; no path or movement budget.", coord=unit.position))
            self.order_book.mark_resolved(order.order_id)
        return events

    def _resolve_hold_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            unit = self.units[order.unit_id]
            unit.recover_fatigue(10)
            unit.consecutive_hold_turns += 1
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

    def _resolve_attack_orders(
        self,
        orders: list[Order],
        previous_positions: dict[str, HexCoord | None],
    ) -> list[GameEvent]:
        events: list[GameEvent] = []
        pre_morale = {uid: u.morale_state for uid, u in self.units.items()}
        for order in orders:
            attacker = self.units[order.unit_id]
            defender = self.units[order.target_unit_id]
            if attacker.is_removed or defender.is_removed or attacker.position is None or defender.position is None:
                self.order_book.mark_resolved(order.order_id)
                continue

            distance = attacker.position.distance_to(defender.position)
            if distance > self.combat_resolver.max_range(attacker) and distance > 1:
                events.append(GameEvent(self.current_turn, "combat", f"{attacker.name} cannot reach {defender.name}.", coord=attacker.position))
                self.order_book.mark_resolved(order.order_id)
                continue

            if (
                attacker.unit_type is UnitType.CAVALRY
                and distance <= 1
                and previous_positions.get(attacker.id) != attacker.position
            ):
                attacker.charged = True

            result = self.combat_resolver.resolve_attack(
                attacker,
                defender,
                distance_hexes=distance,
                defender_terrain=self.battle_map.terrain_at(defender.position),
                last_stand=defender.last_stand_active,
                artillery_effectiveness_modifier=self.weather.artillery_effectiveness_modifier,
            )
            self.order_book.mark_resolved(order.order_id)
            events.append(GameEvent(self.current_turn, "combat", result.summary, coord=defender.position))

            if (
                result.attack_kind is AttackKind.MELEE
                and attacker.unit_type is UnitType.CAVALRY
                and result.defender_damage >= result.attacker_damage
                and defender.morale_state in (MoraleState.ROUTING, MoraleState.BROKEN)
                and attacker.position is not None
                and defender.position is not None
            ):
                events.extend(self._cavalry_pursuit(attacker, defender.position))

        newly_routed = [
            uid for uid, u in self.units.items()
            if u.morale_state in (MoraleState.ROUTING, MoraleState.BROKEN)
            and pre_morale.get(uid) not in (MoraleState.ROUTING, MoraleState.BROKEN)
        ]
        events.extend(self._apply_morale_cascade(newly_routed))
        return events

    def _apply_morale_cascade(self, newly_routed: list[str]) -> list[GameEvent]:
        """For each newly-routed unit, check adjacent friendly units for morale contagion."""
        events: list[GameEvent] = []
        rng = random.Random(self.rng_seed + self.current_turn + 9999)
        processed: set[str] = set()
        queue = list(newly_routed)
        depth = 0
        while queue and depth < 2:
            next_queue = []
            for routing_id in queue:
                routing_unit = self.units.get(routing_id)
                if routing_unit is None or routing_unit.position is None:
                    continue
                for unit in self.units.values():
                    if unit.id in processed or unit.id == routing_id:
                        continue
                    if unit.side != routing_unit.side or unit.is_removed:
                        continue
                    if unit.morale_state not in (MoraleState.STEADY, MoraleState.SHAKEN):
                        continue
                    if unit.position is None:
                        continue
                    dist = unit.position.distance_to(routing_unit.position)
                    if dist > 2:
                        continue
                    chance = 0.35
                    if self.friendly_commander_support(unit):
                        chance = 0.15
                    if rng.random() < chance:
                        unit.degrade_morale(1)
                        processed.add(unit.id)
                        events.append(GameEvent(self.current_turn, "morale",
                            f"{unit.name} shaken by nearby rout ({routing_unit.name}).",
                            coord=unit.position))
                        if unit.morale_state in (MoraleState.ROUTING, MoraleState.BROKEN):
                            next_queue.append(unit.id)
            queue = next_queue
            depth += 1
        return events

    def _resolve_commander_ability_orders(self, orders: list[Order]) -> list[GameEvent]:
        events: list[GameEvent] = []
        for order in orders:
            commander = self.units.get(order.unit_id)
            if commander is None or commander.is_removed or commander.commander_ability_uses <= 0:
                self.order_book.mark_resolved(order.order_id)
                continue
            target = self.units.get(order.target_unit_id or "")
            if target is None or target.is_removed:
                self.order_book.mark_resolved(order.order_id)
                continue
            ability = order.notes.replace("ability:", "") if order.notes else ""
            if ability == CommanderAbility.FORCED_MARCH:
                target.fatigue = max(0, target.fatigue - 40)
                events.append(GameEvent(self.current_turn, "command",
                    f"{commander.name} orders forced march for {target.name}."))
            elif ability == CommanderAbility.INSPIRE:
                target.improve_morale(2)
                events.append(GameEvent(self.current_turn, "command",
                    f"{commander.name} inspires {target.name} to {target.morale_state.value}."))
            elif ability == CommanderAbility.LAST_STAND:
                target.last_stand_active = True
                events.append(GameEvent(self.current_turn, "command",
                    f"{commander.name} orders {target.name} to make a last stand."))
            commander.commander_ability_uses -= 1
            self.order_book.mark_resolved(order.order_id)
        return events

    def _apply_supply_recovery(self) -> None:
        """Units adjacent to supply wagons or in villages recover ammo, unless it is night."""
        if self.weather.time_of_day is TimeOfDay.NIGHT:
            return

        wagons: list[Unit] = [
            u for u in self.units.values()
            if u.unit_type is UnitType.SUPPLY_WAGON and not u.is_removed and u.position is not None
        ]

        for unit in self.units.values():
            if unit.is_removed or unit.position is None:
                continue

            wagon_nearby = any(
                w.side is unit.side and w.position is not None and unit.position.distance_to(w.position) <= 1
                for w in wagons
            )

            if wagon_nearby:
                unit.resupply_ammo(15)
            elif self.battle_map.terrain_at(unit.position) == TerrainType.VILLAGE:
                if unit.consecutive_hold_turns >= 1:
                    unit.resupply_ammo(10)

    def issue_player_order(
        self,
        order_type: "OrderType",
        unit_id: str,
        *,
        destination: "HexCoord | None" = None,
        target_unit_id: str | None = None,
        formation=None,
        priority: int = 100,
    ) -> "Order | None":
        """Issue an order with messenger delay from nearest friendly commander.

        Returns the issued :class:`Order`, or ``None`` if the messenger was
        intercepted by an enemy unit along the courier path.
        """
        unit = self.units[unit_id]
        delay = 0
        commander_pos: HexCoord | None = None
        if unit.position is not None:
            for cmd in self.units.values():
                if cmd.unit_type is UnitType.COMMANDER and cmd.side is unit.side and not cmd.is_removed and cmd.position is not None:
                    if self.messenger_system is not None:
                        delay = self.messenger_system.delay_turns(cmd.position, unit.position)
                    commander_pos = cmd.position
                    break

        if commander_pos is not None and unit.position is not None:
            path = commander_pos.line_to(unit.position)
            enemy_units = [u for u in self.units.values() if u.side is not unit.side and not u.is_removed]
            rng = random.Random(self.rng_seed ^ self.current_turn ^ hash(unit_id))
            if is_intercepted(path, enemy_units, rng):
                self.event_log.append(GameEvent(
                    self.current_turn,
                    "MessengerIntercepted",
                    f"Messenger intercepted! Order to {unit.name} lost.",
                ))
                return None

        return self.order_book.issue(
            order_type,
            unit_id,
            current_turn=self.current_turn,
            delay_turns=delay,
            priority=priority,
            destination=destination,
            target_unit_id=target_unit_id,
            formation=formation,
        )

    def _reachable_destination(self, unit: Unit, path: list[HexCoord]) -> HexCoord:
        if not path:
            return unit.position

        budget = unit.turn_movement_budget() / self.battle_map.hex_size_meters
        spent = 0.0
        current = path[0]
        terrain_costs = unit.movement_costs()

        for step in path[1:]:
            step_cost = self.battle_map.movement_cost(step, terrain_costs)
            if spent + step_cost > budget:
                break

            enemy_present = any(occupant.side is not unit.side for occupant in self.units_at(step))
            if enemy_present:
                break

            spent += step_cost
            current = step
        return current

    def _process_reinforcements(self) -> list[GameEvent]:
        events: list[GameEvent] = []
        for wave in self.reinforcements:
            if self.current_turn != wave.turn:
                continue
            occupied_this_wave: set[HexCoord] = set()
            for unit in wave.units:
                placed = False
                for coord in wave.entry_coords:
                    if (
                        self.battle_map.in_bounds(coord)
                        and not self.units_at(coord)
                        and coord not in occupied_this_wave
                    ):
                        unit.position = coord
                        self.units[unit.id] = unit
                        occupied_this_wave.add(coord)
                        events.append(GameEvent(
                            self.current_turn,
                            "ReinforcementArrival",
                            f"{unit.name} arrives at {coord}.",
                        ))
                        placed = True
                        break
                if not placed:
                    # Fall back to first valid-bounds coord regardless of occupancy
                    fallback = next(
                        (c for c in wave.entry_coords if self.battle_map.in_bounds(c)),
                        wave.entry_coords[0] if wave.entry_coords else None,
                    )
                    if fallback is not None:
                        unit.position = fallback
                        self.units[unit.id] = unit
                    events.append(GameEvent(
                        self.current_turn,
                        "ReinforcementArrival",
                        f"{unit.name} could not find an entry point.",
                    ))
        return events

    def _cavalry_pursuit(self, cavalry: Unit, defeated_pos: HexCoord) -> list[GameEvent]:
        if cavalry.position is None or cavalry.position == defeated_pos:
            return []
        candidates = [
            h for h in cavalry.position.neighbors()
            if self.battle_map.in_bounds(h)
            and not any(u.side is not cavalry.side and not u.is_removed for u in self.units_at(h))
            and h.distance_to(defeated_pos) < cavalry.position.distance_to(defeated_pos)
        ]
        if not candidates:
            return []
        target = min(candidates, key=lambda h: h.distance_to(defeated_pos))
        cavalry.position = target
        return [GameEvent(self.current_turn, "pursuit", f"{cavalry.name} pursues to {target}.")]

    def _score_map(self) -> dict[str, int]:
        return {
            Side.BLUE.value: self.score_for_side(Side.BLUE),
            Side.RED.value: self.score_for_side(Side.RED),
        }
