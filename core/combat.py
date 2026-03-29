"""Combat resolution for ranged fire and melee."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import random

from .dice import CombatTables, DieId, KriegsspielDice, load_combat_tables
from .map import TerrainType
from .units import Formation, MoraleState, Unit, UnitType


class AttackKind(StrEnum):
    RANGED = "ranged"
    MELEE = "melee"


@dataclass(frozen=True, slots=True)
class CombatResult:
    attack_kind: AttackKind
    attacker_id: str
    defender_id: str
    attacker_damage: int
    defender_damage: int
    attacker_morale: MoraleState
    defender_morale: MoraleState
    attacker_fatigue: int
    defender_fatigue: int
    die_id: DieId
    die_face_index: int
    summary: str


class CombatResolver:
    """Resolves combat using simplified digital versions of the 1824 tables."""

    def __init__(
        self,
        *,
        tables: CombatTables | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.tables = tables or load_combat_tables()
        self.dice = KriegsspielDice(tables=self.tables, rng=rng)

    def max_range(self, unit: Unit) -> int:
        if unit.unit_type is UnitType.INFANTRY:
            return 4
        if unit.unit_type is UnitType.SKIRMISHER:
            return 5
        if unit.unit_type is UnitType.ARTILLERY:
            return 10 if unit.formation is Formation.UNLIMBERED else 0
        return 0

    def resolve_attack(
        self,
        attacker: Unit,
        defender: Unit,
        *,
        distance_hexes: int,
        defender_terrain: TerrainType,
        last_stand: bool = False,
        artillery_effectiveness_modifier: float = 1.0,
    ) -> CombatResult:
        if distance_hexes <= 1:
            return self.resolve_melee(attacker, defender, defender_terrain=defender_terrain, last_stand=last_stand)
        return self.resolve_ranged(
            attacker,
            defender,
            distance_hexes=distance_hexes,
            defender_terrain=defender_terrain,
            artillery_effectiveness_modifier=artillery_effectiveness_modifier,
        )

    def resolve_ranged(
        self,
        attacker: Unit,
        defender: Unit,
        *,
        distance_hexes: int,
        defender_terrain: TerrainType,
        artillery_effectiveness_modifier: float = 1.0,
    ) -> CombatResult:
        rounds_per_volley = {
            UnitType.INFANTRY: 3,
            UnitType.ARTILLERY: 5,
            UnitType.SKIRMISHER: 2,
        }.get(attacker.unit_type, 1)
        if not attacker.consume_ammo(rounds_per_volley):
            return CombatResult(
                attack_kind=AttackKind.RANGED,
                attacker_id=attacker.id,
                defender_id=defender.id,
                attacker_damage=0,
                defender_damage=0,
                attacker_morale=attacker.morale_state,
                defender_morale=defender.morale_state,
                attacker_fatigue=attacker.fatigue,
                defender_fatigue=defender.fatigue,
                die_id=DieId.I,
                die_face_index=0,
                summary=f"{attacker.name} is out of ammunition.",
            )

        if distance_hexes > self.max_range(attacker):
            raise ValueError("Target is out of range for the attacker's unit type.")

        table_key, die_id = self._ranged_profile(attacker, defender, distance_hexes, defender_terrain)
        band_key = str(distance_hexes)
        base_damage = self.tables.ranged_tables[table_key][band_key]
        die_roll = self.dice.roll(die_id)

        attack_power = base_damage * die_roll.multiplier * attacker.combat_effectiveness
        defense = self._ranged_defense_multiplier(defender, defender_terrain)

        if (
            attacker.position is not None
            and defender.position is not None
            and defender.is_flank_attack_from(attacker.position)
        ):
            defense *= 0.85

        if attacker.unit_type is UnitType.ARTILLERY:
            attack_power *= artillery_effectiveness_modifier

        damage = max(0, round(attack_power / defense))
        applied_damage = defender.apply_damage(damage)

        attacker_fatigue = self._apply_fatigue(attacker, amount=4 if attacker.unit_type is not UnitType.ARTILLERY else 5)
        defender_fatigue = self._apply_fatigue(defender, amount=2 if applied_damage else 0)

        self._apply_morale_after_ranged(defender, applied_damage)

        summary = (
            f"{attacker.name} fires on {defender.name} at {distance_hexes} hexes "
            f"for {applied_damage} damage."
        )
        return CombatResult(
            attack_kind=AttackKind.RANGED,
            attacker_id=attacker.id,
            defender_id=defender.id,
            attacker_damage=0,
            defender_damage=applied_damage,
            attacker_morale=attacker.morale_state,
            defender_morale=defender.morale_state,
            attacker_fatigue=attacker_fatigue,
            defender_fatigue=defender_fatigue,
            die_id=die_id,
            die_face_index=die_roll.face_index,
            summary=summary,
        )

    def resolve_melee(
        self,
        attacker: Unit,
        defender: Unit,
        *,
        defender_terrain: TerrainType,
        last_stand: bool = False,
    ) -> CombatResult:
        odds_key, die_id = self._melee_profile(attacker, defender)
        base_damage = self.tables.melee_tables[odds_key]
        die_roll = self.dice.roll(die_id)

        attacker_power = base_damage * die_roll.multiplier * attacker.combat_effectiveness
        defender_power = (base_damage * 0.8) * defender.combat_effectiveness

        if (
            attacker.position is not None
            and defender.position is not None
            and defender.is_flank_attack_from(attacker.position)
        ):
            attacker_power *= 1.25

        if attacker.charged:
            attacker_power *= 1.3

        if defender.is_entrenched:
            attacker_power /= 1.15
        if last_stand:
            attacker_power /= 1.5

        attacker_damage = self._calculate_melee_damage(
            attack_power=defender_power,
            defender=attacker,
            defender_terrain=TerrainType.OPEN,
            attacker=defender,
        )
        defender_damage = self._calculate_melee_damage(
            attack_power=attacker_power,
            defender=defender,
            defender_terrain=defender_terrain,
            attacker=attacker,
        )

        applied_to_attacker = attacker.apply_damage(attacker_damage)
        applied_to_defender = defender.apply_damage(defender_damage)

        attacker_fatigue = self._apply_fatigue(attacker, amount=8)
        defender_fatigue = self._apply_fatigue(defender, amount=8)

        self._apply_morale_after_melee(attacker, applied_to_attacker, won=applied_to_defender >= applied_to_attacker)
        self._apply_morale_after_melee(defender, applied_to_defender, won=applied_to_defender <= applied_to_attacker)

        summary = (
            f"{attacker.name} engages {defender.name} in melee: "
            f"{applied_to_defender} dealt, {applied_to_attacker} taken."
        )
        return CombatResult(
            attack_kind=AttackKind.MELEE,
            attacker_id=attacker.id,
            defender_id=defender.id,
            attacker_damage=applied_to_attacker,
            defender_damage=applied_to_defender,
            attacker_morale=attacker.morale_state,
            defender_morale=defender.morale_state,
            attacker_fatigue=attacker_fatigue,
            defender_fatigue=defender_fatigue,
            die_id=die_id,
            die_face_index=die_roll.face_index,
            summary=summary,
        )

    def _ranged_profile(
        self,
        attacker: Unit,
        defender: Unit,
        distance_hexes: int,
        defender_terrain: TerrainType,
    ) -> tuple[str, DieId]:
        if attacker.unit_type is UnitType.INFANTRY:
            return "infantry_open", DieId.I
        if attacker.unit_type is UnitType.SKIRMISHER:
            return "skirmisher_cover", DieId.II
        if attacker.unit_type is UnitType.ARTILLERY:
            good_conditions = (
                defender_terrain not in {TerrainType.FOREST, TerrainType.VILLAGE}
                and distance_hexes <= 6
            )
            if good_conditions:
                return "artillery_good", DieId.III
            return "artillery_bad", DieId.V
        raise ValueError(f"{attacker.unit_type} cannot make a ranged attack.")

    def _melee_profile(self, attacker: Unit, defender: Unit) -> tuple[str, DieId]:
        ratio = max(attacker.current_strength, 1) / max(defender.current_strength, 1)
        if ratio >= 4.0:
            return "four_to_one", DieId.V
        if ratio >= 3.0:
            return "three_to_one", DieId.IV
        if ratio >= 1.5:
            return "three_to_two", DieId.II
        return "even", DieId.I

    def _ranged_defense_multiplier(self, defender: Unit, terrain: TerrainType) -> float:
        terrain_modifier = self.tables.terrain_fire_defense[terrain.value]
        formation_modifier = self.tables.formation_modifiers["ranged"].get(defender.formation.value, 1.0)
        result = terrain_modifier * formation_modifier
        if defender.is_entrenched:
            result *= 1.25
        return result

    def _calculate_melee_damage(
        self,
        *,
        attack_power: float,
        defender: Unit,
        defender_terrain: TerrainType,
        attacker: Unit,
    ) -> int:
        terrain_modifier = self.tables.terrain_melee_defense[defender_terrain.value]
        formation_modifier = self.tables.formation_modifiers["melee"].get(defender.formation.value, 1.0)

        if (
            attacker.unit_type is UnitType.CAVALRY
            and defender.unit_type is UnitType.INFANTRY
            and defender.formation is Formation.SQUARE
        ):
            terrain_modifier *= 1.8
            formation_modifier *= 1.8

        if attacker.unit_type is UnitType.ARTILLERY and defender.unit_type is UnitType.ARTILLERY:
            terrain_modifier *= 0.85

        damage = round(attack_power / (terrain_modifier * formation_modifier))
        return max(0, damage)

    @staticmethod
    def _apply_fatigue(unit: Unit, *, amount: int) -> int:
        if amount <= 0:
            return unit.fatigue
        unit.add_fatigue(amount)
        return unit.fatigue

    @staticmethod
    def _apply_morale_after_ranged(defender: Unit, damage: int) -> None:
        if damage <= 0:
            return
        steps = 0
        if damage >= max(1, math.ceil(defender.max_hit_points * 0.15)):
            steps += 1
        if defender.casualty_ratio >= (1 / 3):
            steps += 1
        if defender.fatigue >= 70:
            steps += 1
        if steps:
            defender.degrade_morale(steps)

    @staticmethod
    def _apply_morale_after_melee(unit: Unit, damage: int, *, won: bool) -> None:
        steps = 0
        if damage > 0:
            steps += 1
        if damage >= max(1, math.ceil(unit.max_hit_points * 0.2)):
            steps += 1
        if not won:
            steps += 1
        if steps:
            unit.degrade_morale(steps)

