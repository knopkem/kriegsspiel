"""Core domain models for the Kriegsspiel simulation."""

from .combat import AttackKind, CombatResolver, CombatResult
from .dice import CombatTables, DiceRoll, DieId, KriegsspielDice, load_combat_tables
from .fog_of_war import FogOfWarEngine, LastKnownEnemy, VisibilitySnapshot, VisibilityState
from .game import GameEvent, GameState, VictoryLevel, VictoryReport
from .map import HexCell, HexCoord, HexGridMap, TerrainType
from .messenger import MessengerSystem
from .orders import Order, OrderBook, OrderStatus, OrderType
from .replay import ReplayFrame, ReplayRecorder, UnitSnapshot
from .scenario import Scenario, ScenarioObjective, load_builtin_scenario, load_scenario
from .tutorial import TutorialDirector, TutorialStep
from .units import (
    FatigueLevel,
    Formation,
    InfantryExchangeState,
    MoraleState,
    Side,
    Unit,
    UnitType,
    make_artillery_battery,
    make_cavalry_squadron,
    make_commander,
    make_infantry_half_battalion,
    make_skirmisher_detachment,
)

__all__ = [
    "AttackKind",
    "CombatResolver",
    "CombatResult",
    "CombatTables",
    "DiceRoll",
    "DieId",
    "FatigueLevel",
    "FogOfWarEngine",
    "Formation",
    "GameEvent",
    "GameState",
    "HexCell",
    "HexCoord",
    "HexGridMap",
    "InfantryExchangeState",
    "KriegsspielDice",
    "LastKnownEnemy",
    "MessengerSystem",
    "MoraleState",
    "Order",
    "OrderBook",
    "OrderStatus",
    "OrderType",
    "ReplayFrame",
    "ReplayRecorder",
    "Scenario",
    "ScenarioObjective",
    "Side",
    "TerrainType",
    "Unit",
    "UnitSnapshot",
    "UnitType",
    "VisibilitySnapshot",
    "VisibilityState",
    "VictoryLevel",
    "VictoryReport",
    "load_builtin_scenario",
    "load_combat_tables",
    "load_scenario",
    "make_artillery_battery",
    "make_cavalry_squadron",
    "make_commander",
    "make_infantry_half_battalion",
    "make_skirmisher_detachment",
    "TutorialDirector",
    "TutorialStep",
]
