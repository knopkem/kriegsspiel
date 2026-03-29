"""Custom Kriegsspiel dice and combat table loading."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
import random
from typing import Mapping


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_COMBAT_TABLES_PATH = DATA_DIR / "combat_tables.json"


class DieId(StrEnum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"


@dataclass(frozen=True, slots=True)
class DiceRoll:
    die_id: DieId
    face_index: int
    multiplier: float


@dataclass(frozen=True, slots=True)
class CombatTables:
    dice_profiles: Mapping[DieId, tuple[float, ...]]
    ranged_tables: Mapping[str, Mapping[str, int]]
    melee_tables: Mapping[str, int]
    terrain_fire_defense: Mapping[str, float]
    terrain_melee_defense: Mapping[str, float]
    formation_modifiers: Mapping[str, Mapping[str, float]]


def load_combat_tables(path: Path | None = None) -> CombatTables:
    table_path = path or DEFAULT_COMBAT_TABLES_PATH
    with table_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    dice_profiles = {
        DieId(key): tuple(float(value) for value in values)
        for key, values in raw["dice_profiles"].items()
    }
    return CombatTables(
        dice_profiles=dice_profiles,
        ranged_tables=raw["ranged_tables"],
        melee_tables=raw["melee_tables"],
        terrain_fire_defense=raw["terrain_fire_defense"],
        terrain_melee_defense=raw["terrain_melee_defense"],
        formation_modifiers=raw["formation_modifiers"],
    )


class KriegsspielDice:
    """Rolls the five custom dice used by the combat tables."""

    def __init__(
        self,
        *,
        tables: CombatTables | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.tables = tables or load_combat_tables()
        self.rng = rng or random.Random()

    def roll(self, die_id: DieId) -> DiceRoll:
        profile = self.tables.dice_profiles[die_id]
        face_index = self.rng.randrange(len(profile))
        return DiceRoll(
            die_id=die_id,
            face_index=face_index,
            multiplier=profile[face_index],
        )
