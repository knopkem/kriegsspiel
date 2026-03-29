"""Tactical decision helpers for the simple AI commander."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import TYPE_CHECKING

from core.game import GameState
from core.map import HexCoord
from core.units import Side, Unit

if TYPE_CHECKING:
    from core.map import HexGridMap
    from core.units import UnitType
    from .evaluation import BattlefieldEvaluator


@dataclass(slots=True)
class TacticalPlanner:
    rng: random.Random

    def choose_retreat_destination(
        self,
        unit: Unit,
        battle_map: "HexGridMap",
        evaluator: "BattlefieldEvaluator",
        enemies: list[Unit],
    ) -> HexCoord:
        """Retreat to best nearby defensive terrain, away from enemies."""
        from core.map import TerrainType
        if unit.position is None:
            return HexCoord(0, 0)

        enemy_positions = [e.position for e in enemies if e.position is not None]
        if not enemy_positions:
            return HexCoord(0, unit.position.r)

        ecq = sum(p.q for p in enemy_positions) / len(enemy_positions)
        ecr = sum(p.r for p in enemy_positions) / len(enemy_positions)
        away_dq = unit.position.q - ecq
        away_dr = unit.position.r - ecr

        best = None
        best_score = -999.0
        for coord in battle_map.coords():
            dist_from_self = unit.position.distance_to(coord)
            if dist_from_self < 1 or dist_from_self > 5:
                continue
            dq = coord.q - unit.position.q
            dr = coord.r - unit.position.r
            dot = dq * away_dq + dr * away_dr
            if dot <= 0:
                continue
            t = battle_map.terrain_at(coord)
            if t == TerrainType.RIVER:
                continue
            terrain_bonus = evaluator.terrain_score(unit, coord, battle_map)
            min_enemy_dist = min((coord.distance_to(p) for p in enemy_positions), default=99)
            score = terrain_bonus + min_enemy_dist * 0.2 - dist_from_self * 0.1
            if score > best_score:
                best_score = score
                best = coord

        if best is not None:
            return best
        if unit.side.value == "blue":
            return HexCoord(0, unit.position.r)
        return HexCoord(battle_map.width - 1, unit.position.r)

    def choose_approach_destination(self, game: GameState, unit: Unit, target: HexCoord) -> HexCoord:
        path = game.battle_map.find_path(unit.position, target, terrain_costs=unit.movement_costs())
        if len(path) >= 2:
            return path[min(2, len(path) - 1)]
        return target

    def assign_targets(
        self,
        units: list[Unit],
        visible_enemies: list[Unit],
        evaluator: "BattlefieldEvaluator",
    ) -> dict[str, Unit]:
        """Assign attack targets with focus-fire on highest-threat enemy."""
        from core.units import UnitType
        if not visible_enemies or not units:
            return {}

        reference = next((u for u in units if u.position is not None), None)
        if reference is None:
            return {}

        scored = sorted(
            [e for e in visible_enemies if e.position is not None],
            key=lambda e: evaluator.firepower_estimate(e) / (reference.position.distance_to(e.position) + 1),
            reverse=True,
        )
        if not scored:
            return {}

        primary_target = scored[0]
        assignments: dict[str, Unit] = {}

        for unit in units:
            if unit.position is None or unit.unit_type is UnitType.COMMANDER:
                continue
            dist_to_primary = unit.position.distance_to(primary_target.position)
            if dist_to_primary <= 8:
                assignments[unit.id] = primary_target
            else:
                best = evaluator.best_target(unit, visible_enemies)
                if best:
                    assignments[unit.id] = best

        return assignments

    def cavalry_flanking_destination(
        self,
        unit: Unit,
        enemies: list[Unit],
        battle_map: "HexGridMap",
    ) -> HexCoord | None:
        """Try to find a hex that flanks the enemy cluster."""
        from core.map import TerrainType
        if not enemies or unit.position is None:
            return None
        valid = [e for e in enemies if e.position is not None]
        if not valid:
            return None
        eq = sum(e.position.q for e in valid) / len(valid)
        er = sum(e.position.r for e in valid) / len(valid)
        for r_off in [3, -3, 2, -2]:
            target = HexCoord(int(eq), int(er + r_off))
            if not battle_map.in_bounds(target):
                continue
            terrain = battle_map.terrain_at(target)
            if terrain not in (TerrainType.FOREST, TerrainType.MARSH, TerrainType.RIVER):
                return target
        return None

    def artillery_deployment_hex(
        self,
        unit: Unit,
        battle_map: "HexGridMap",
        enemies: list[Unit],
    ) -> HexCoord | None:
        """Find a good HILL or OPEN hex with LOS to enemies."""
        from core.map import TerrainType
        if unit.position is None:
            return None
        candidates: list[tuple[HexCoord, TerrainType]] = []
        for coord in battle_map.coords():
            if unit.position.distance_to(coord) > 5:
                continue
            t = battle_map.terrain_at(coord)
            if t in (TerrainType.HILL, TerrainType.OPEN, TerrainType.FORTIFICATION):
                for enemy in enemies:
                    if enemy.position and battle_map.has_line_of_sight(coord, enemy.position):
                        candidates.append((coord, t))
                        break
        if not candidates:
            return None
        for coord, t in candidates:
            if t == TerrainType.HILL:
                return coord
        return candidates[0][0]

    def skirmisher_harassment_hex(
        self,
        unit: Unit,
        enemies: list[Unit],
        battle_map: "HexGridMap",
    ) -> HexCoord | None:
        """Stay at ~3-4 hex range from nearest enemy, preferably in cover."""
        from core.map import TerrainType
        if unit.position is None or not enemies:
            return None
        nearest = min(
            (e for e in enemies if e.position is not None),
            key=lambda e: unit.position.distance_to(e.position),
            default=None,
        )
        if nearest is None:
            return None
        best = None
        best_score = -999.0
        for coord in battle_map.coords():
            dist_to_enemy = coord.distance_to(nearest.position)
            if dist_to_enemy < 2 or dist_to_enemy > 5:
                continue
            dist_to_self = unit.position.distance_to(coord)
            if dist_to_self > 4:
                continue
            t = battle_map.terrain_at(coord)
            cover_bonus = 1.0 if t in (TerrainType.FOREST, TerrainType.VILLAGE) else 0.0
            score = cover_bonus - dist_to_self * 0.1
            if score > best_score:
                best_score = score
                best = coord
        return best


class ReserveManager:
    """Tracks which units should stay in reserve vs commit to battle."""

    def should_commit(self, unit: Unit, game: GameState, all_friendly: list[Unit]) -> bool:
        """Return True if unit should attack, False if it should hold in reserve."""
        from core.units import MoraleState, UnitType

        # (c) within 3 hexes of a visible enemy → always commit
        enemies = [
            u
            for u in game.units.values()
            if u.side is not unit.side and not u.is_removed and u.position is not None
        ]
        if unit.position is not None and enemies:
            if min(unit.position.distance_to(e.position) for e in enemies) <= 3:
                return True

        frontline = [
            u
            for u in all_friendly
            if u.unit_type is not UnitType.COMMANDER
            and not u.is_removed
            and u.position is not None
        ]

        frontline_ok = all(
            u.morale_state not in {MoraleState.ROUTING, MoraleState.BROKEN}
            for u in frontline
        )

        # Hold if comfortably winning and no crisis on the front
        opp = Side.BLUE if unit.side is Side.RED else Side.RED
        my_score = game.score_for_side(unit.side)
        opp_score = game.score_for_side(opp)
        if my_score - opp_score > 15 and frontline_ok:
            return False

        # (a) any frontline unit routing → plug the gap
        if any(
            u.morale_state in {MoraleState.ROUTING, MoraleState.BROKEN} for u in frontline
        ):
            return True

        # (b) frontline still has >60 % HP → side is strong, advance
        if frontline:
            avg_hp = sum(u.hit_points / u.max_hit_points for u in frontline) / len(frontline)
            if avg_hp > 0.6:
                return True

        return True  # default: commit

    def reserve_position(self, unit: Unit, game: GameState) -> HexCoord | None:
        """Return a safe hex ~5 steps toward own baseline from the friendly centroid."""
        friendly = [
            u
            for u in game.units.values()
            if u.side is unit.side and not u.is_removed and u.position is not None
        ]
        if not friendly:
            return None

        cq = sum(u.position.q for u in friendly) / len(friendly)
        cr = sum(u.position.r for u in friendly) / len(friendly)

        # r=0 is BLUE's baseline; r=height-1 is RED's baseline
        baseline_r = 0 if unit.side is Side.BLUE else game.battle_map.height - 1
        dr_total = baseline_r - cr
        dist = abs(dr_total)
        step = 5 * dr_total / dist if dist > 0.001 else 0.0

        target_q = max(0, min(game.battle_map.width - 1, int(round(cq))))
        target_r = max(0, min(game.battle_map.height - 1, int(round(cr + step))))
        return HexCoord(target_q, target_r)


