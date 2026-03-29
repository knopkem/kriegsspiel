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
    from core.fog_of_war import VisibilitySnapshot
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
        friendlies: list[Unit] | None = None,
    ) -> HexCoord:
        """Retreat to best nearby defensive terrain, away from enemies.

        Scores candidates by:
        - Terrain defense value (FORTIFICATION best, MARSH avoided)
        - Proximity to friendly commander (+0.5 within 3 hexes)
        - Distance from nearest enemy (+0.1 per hex)
        """
        from core.map import TerrainType
        from core.units import UnitType

        _TERRAIN_DEFENSE: dict = {
            TerrainType.FORTIFICATION: 3.0,
            TerrainType.HILL: 2.0,
            TerrainType.FOREST: 1.5,
            TerrainType.VILLAGE: 1.5,
            TerrainType.OPEN: 1.0,
            TerrainType.ROAD: 0.8,
            TerrainType.RIVER: 0.0,
        }

        if unit.position is None:
            return HexCoord(0, 0)

        enemy_positions = [e.position for e in enemies if e.position is not None]
        if not enemy_positions:
            return HexCoord(0, unit.position.r)

        ecq = sum(p.q for p in enemy_positions) / len(enemy_positions)
        ecr = sum(p.r for p in enemy_positions) / len(enemy_positions)
        away_dq = unit.position.q - ecq
        away_dr = unit.position.r - ecr

        # Locate friendly commander for the regrouping bonus.
        friendly_cmdr = None
        if friendlies:
            friendly_cmdr = next(
                (f for f in friendlies if f.unit_type is UnitType.COMMANDER and f.position is not None),
                None,
            )

        best = None
        best_score = -999.0
        for coord in battle_map.coords():
            dist_from_self = unit.position.distance_to(coord)
            if dist_from_self < 1 or dist_from_self > 6:
                continue
            dq = coord.q - unit.position.q
            dr = coord.r - unit.position.r
            dot = dq * away_dq + dr * away_dr
            if dot <= 0:
                continue
            t = battle_map.terrain_at(coord)
            if t == TerrainType.MARSH:
                continue
            terrain_defense = _TERRAIN_DEFENSE.get(t, 1.0)
            min_enemy_dist = min((coord.distance_to(p) for p in enemy_positions), default=99)
            score = terrain_defense + min_enemy_dist * 0.1
            if friendly_cmdr is not None and coord.distance_to(friendly_cmdr.position) <= 3:
                score += 0.5
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
        use_morale_exploitation: bool = False,
    ) -> dict[str, Unit]:
        """Assign attack targets with focus-fire on highest-threat enemy."""
        from core.units import MoraleState, UnitType
        if not visible_enemies or not units:
            return {}

        reference = next((u for u in units if u.position is not None), None)
        if reference is None:
            return {}

        def _threat_score(e: Unit) -> float:
            if e.position is None:
                return 0.0
            fp = evaluator.firepower_estimate(e)
            dist = reference.position.distance_to(e.position)
            threat = fp / (dist + 1)
            if use_morale_exploitation:
                if e.morale_state is MoraleState.BROKEN:
                    threat *= 2.5
                elif e.morale_state is MoraleState.ROUTING:
                    threat *= 2.0
                elif e.morale_state is MoraleState.SHAKEN:
                    threat *= 1.5
            return threat

        scored = sorted(
            [e for e in visible_enemies if e.position is not None],
            key=_threat_score,
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
                best = evaluator.best_target(unit, visible_enemies, use_morale_exploitation=use_morale_exploitation)
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
        """Stay at ~3-4 hex range from nearest enemy in cover. Retreat if too close."""
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

        current_dist = unit.position.distance_to(nearest.position)
        # If enemy is too close, retreat to cover first
        ideal_min, ideal_max = (3, 5) if current_dist >= 3 else (5, 7)

        best = None
        best_score = -999.0
        for coord in battle_map.coords():
            dist_to_enemy = coord.distance_to(nearest.position)
            if dist_to_enemy < ideal_min or dist_to_enemy > ideal_max:
                continue
            dist_to_self = unit.position.distance_to(coord)
            if dist_to_self > 4:
                continue
            t = battle_map.terrain_at(coord)
            if t in (TerrainType.RIVER, TerrainType.MARSH):
                continue
            cover_bonus = 1.5 if t == TerrainType.FOREST else 1.0 if t == TerrainType.VILLAGE else 0.0
            # Prefer hexes that have LOS to the enemy
            los_bonus = 0.5 if battle_map.has_line_of_sight(coord, nearest.position) else 0.0
            score = cover_bonus + los_bonus - dist_to_self * 0.1
            if score > best_score:
                best_score = score
                best = coord
        return best

    def cavalry_scout_hex(
        self,
        unit: Unit,
        visibility: "VisibilitySnapshot",
        battle_map: "HexGridMap",
        enemy_centroid: HexCoord | None,
    ) -> HexCoord | None:
        """Cavalry scouts toward fog boundary to reveal hidden hexes."""
        from core.fog_of_war import VisibilityState
        if unit.position is None:
            return None

        # Find hexes at the edge of vision (EXPLORED adjacent to HIDDEN)
        fog_edge: list[HexCoord] = []
        for coord in battle_map.coords():
            if visibility.visibility_state(coord) is not VisibilityState.HIDDEN:
                continue
            for nb in battle_map.neighbors(coord):
                if visibility.visibility_state(nb) is VisibilityState.VISIBLE:
                    fog_edge.append(nb)
                    break

        if not fog_edge:
            return None

        # Pick fog-edge hex that is: closest to unit, away from enemy centroid
        best = None
        best_score = -999.0
        for coord in fog_edge:
            dist_to_self = unit.position.distance_to(coord)
            if dist_to_self > 8:
                continue
            from core.map import TerrainType
            t = battle_map.terrain_at(coord)
            if t in (TerrainType.FOREST, TerrainType.MARSH):
                continue
            # Prefer being away from enemy centroid (flanking recon)
            flank_bonus = 0.0
            if enemy_centroid is not None:
                # Reward hexes perpendicular to enemy centroid direction
                dq = coord.q - enemy_centroid.q
                dr = coord.r - enemy_centroid.r
                flank_bonus = (abs(dq) - abs(dr)) * 0.1
            score = -dist_to_self * 0.3 + flank_bonus
            if score > best_score:
                best_score = score
                best = coord
        return best

    def infantry_hold_hex(
        self,
        unit: Unit,
        battle_map: "HexGridMap",
        enemy_centroid: HexCoord | None,
    ) -> HexCoord | None:
        """Infantry holds defensible ground near current position facing the enemy."""
        from core.map import TerrainType
        if unit.position is None:
            return None
        best = None
        best_score = -999.0
        for coord in battle_map.neighbors(unit.position):
            t = battle_map.terrain_at(coord)
            if t in (TerrainType.RIVER, TerrainType.MARSH):
                continue
            defense_score = {
                TerrainType.FORTIFICATION: 3.0,
                TerrainType.HILL: 2.0,
                TerrainType.VILLAGE: 1.5,
                TerrainType.FOREST: 1.2,
            }.get(t, 1.0)
            enemy_dist = coord.distance_to(enemy_centroid) if enemy_centroid else 0
            # Prefer positions closer to enemy (hold ground, not retreat)
            score = defense_score - enemy_dist * 0.05
            if score > best_score:
                best_score = score
                best = coord
        return best if best_score > 1.0 else None


class ReserveManager:
    """Tracks which units should stay in reserve vs commit to battle."""

    def should_commit(self, unit: Unit, game: GameState, all_friendly: list[Unit]) -> bool:
        """Return True if unit should attack, False if it should hold in reserve."""
        from core.units import MoraleState, UnitType

        # Always commit if within 3 hexes of a visible enemy
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

        frontline_routing = [
            u for u in frontline
            if u.morale_state in {MoraleState.ROUTING, MoraleState.BROKEN}
        ]
        frontline_ok = not frontline_routing

        opp = Side.BLUE if unit.side is Side.RED else Side.RED
        my_score = game.score_for_side(unit.side)
        opp_score = game.score_for_side(opp)
        winning_comfortably = my_score - opp_score > 15

        # --- Cavalry: commit for flanking opportunity ---
        if unit.unit_type is UnitType.CAVALRY:
            # Commit if there are routing enemies to pursue
            if enemies:
                routing_enemies = [
                    e for e in enemies
                    if e.morale_state in {MoraleState.ROUTING, MoraleState.BROKEN}
                    and e.position is not None
                ]
                if routing_enemies:
                    return True
            # Commit if frontline is routing and cavalry can plug the gap
            if frontline_routing:
                return True
            # Hold cavalry in reserve when winning to preserve for pursuit
            if winning_comfortably and frontline_ok:
                return False
            return True  # cavalry default: commit for flanking

        # --- Artillery: reposition to cover breaches, hold in reserve until needed ---
        if unit.unit_type is UnitType.ARTILLERY:
            # Commit if there are routing friendlies (provide covering fire)
            if frontline_routing:
                return True
            # Hold artillery back if frontline is healthy
            if frontline:
                avg_hp = sum(u.hit_points / u.max_hit_points for u in frontline) / len(frontline)
                if avg_hp > 0.7 and frontline_ok:
                    return False  # let infantry advance first
            return True

        # --- Infantry reserve logic ---
        # Hold if comfortably winning and no crisis on the front
        if winning_comfortably and frontline_ok:
            return False

        # Plug the gap if any frontline unit is routing
        if frontline_routing:
            return True

        # Frontline still has >60% HP → advance
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


