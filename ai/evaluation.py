"""Heuristic battlefield evaluation for AI order selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from core.game import GameState
from core.units import Side, Unit, UnitType

if TYPE_CHECKING:
    from core.map import HexCoord, HexGridMap


UNIT_WEIGHTS: dict[UnitType, float] = {
    UnitType.INFANTRY: 1.0,
    UnitType.CAVALRY: 1.15,
    UnitType.ARTILLERY: 1.3,
    UnitType.SKIRMISHER: 0.7,
    UnitType.COMMANDER: 1.5,
}


@dataclass(slots=True)
class BattlefieldEvaluator:
    """Scores unit and side states from a given side's perspective."""

    def unit_value(self, unit: Unit) -> float:
        base = unit.max_hit_points * UNIT_WEIGHTS[unit.unit_type]
        return base * unit.combat_effectiveness

    def side_score(self, game: GameState, side: Side) -> float:
        friendly = sum(self.unit_value(unit) for unit in game.units.values() if unit.side is side and not unit.is_removed)
        enemy = sum(self.unit_value(unit) for unit in game.units.values() if unit.side is not side and not unit.is_removed)
        objective = game.score_for_side(side) * 8
        return friendly - enemy + objective

    def firepower_estimate(self, unit: Unit) -> float:
        """Estimate a unit's offensive threat value."""
        base = unit.combat_effectiveness * unit.max_hit_points / 10.0
        type_multiplier = {
            UnitType.ARTILLERY: 1.5,
            UnitType.CAVALRY: 1.2,
            UnitType.INFANTRY: 1.0,
            UnitType.SKIRMISHER: 0.8,
            UnitType.COMMANDER: 0.4,
        }.get(unit.unit_type, 1.0)
        return base * type_multiplier

    def best_target(self, unit: Unit, visible_enemies: Iterable[Unit], use_morale_exploitation: bool = True) -> Unit | None:
        """Pick highest-threat visible enemy. When use_morale_exploitation is True,
        prefer routing/shaken/broken enemies (easier finish)."""
        from core.units import MoraleState
        enemies = list(visible_enemies)
        if not enemies:
            return None
        if unit.position is None:
            return enemies[0]

        best = None
        best_score = -1.0
        for enemy in enemies:
            if enemy.position is None:
                continue
            dist = unit.position.distance_to(enemy.position)
            fp = self.firepower_estimate(enemy)
            threat = fp / (dist + 1)
            if use_morale_exploitation:
                if enemy.morale_state is MoraleState.BROKEN:
                    threat *= 2.5
                elif enemy.morale_state is MoraleState.ROUTING:
                    threat *= 2.0
                elif enemy.morale_state is MoraleState.SHAKEN:
                    threat *= 1.5
            if threat > best_score:
                best_score = threat
                best = enemy
        return best

    def terrain_score(self, unit: Unit, coord: "HexCoord", battle_map: "HexGridMap") -> float:
        """Score 0.0–2.0: how good this terrain type is for this unit type."""
        from core.map import TerrainType
        terrain = battle_map.terrain_at(coord)
        scores_by_type = {
            UnitType.INFANTRY: {
                TerrainType.HILL: 0.3, TerrainType.FOREST: 0.5,
                TerrainType.FORTIFICATION: 0.8, TerrainType.VILLAGE: 0.4,
                TerrainType.MARSH: -0.2, TerrainType.ROAD: 0.0, TerrainType.OPEN: 0.0,
            },
            UnitType.ARTILLERY: {
                TerrainType.HILL: 0.8, TerrainType.OPEN: 0.2,
                TerrainType.FORTIFICATION: 0.4, TerrainType.ROAD: 0.1,
                TerrainType.FOREST: -0.5, TerrainType.MARSH: -0.8,
            },
            UnitType.CAVALRY: {
                TerrainType.OPEN: 0.4, TerrainType.ROAD: 0.3,
                TerrainType.FOREST: -0.8, TerrainType.MARSH: -0.6,
                TerrainType.HILL: -0.1, TerrainType.RIVER: -1.0,
            },
            UnitType.SKIRMISHER: {
                TerrainType.FOREST: 0.6, TerrainType.HILL: 0.2,
                TerrainType.VILLAGE: 0.3, TerrainType.MARSH: 0.1,
            },
            UnitType.COMMANDER: {
                TerrainType.VILLAGE: 0.3, TerrainType.HILL: 0.2,
            },
        }
        type_scores = scores_by_type.get(unit.unit_type, {})
        return max(0.0, 1.0 + type_scores.get(terrain, 0.0))

    def best_defensive_hex(
        self,
        unit: Unit,
        candidates: Iterable["HexCoord"],
        battle_map: "HexGridMap",
    ) -> "HexCoord | None":
        """Pick the terrain-best hex from candidates for this unit type."""
        best_coord = None
        best_score = -999.0
        for coord in candidates:
            s = self.terrain_score(unit, coord, battle_map)
            if s > best_score:
                best_score = s
                best_coord = coord
        return best_coord

