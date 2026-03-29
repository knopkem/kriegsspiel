# Contributing to Kriegsspiel

Thank you for your interest in contributing! This document covers the scenario JSON
format, how to run the tests, and the code style rules.

---

## Table of Contents

1. [Scenario JSON Format](#scenario-json-format)
2. [Creating Scenarios with the Editor](#creating-scenarios-with-the-editor)
3. [Running Tests](#running-tests)
4. [Code Style](#code-style)
5. [Architecture Overview](#architecture-overview)
6. [Adding New Terrain Types](#adding-new-terrain-types)
7. [Adding New Unit Types](#adding-new-unit-types)

---

## Scenario JSON Format

All scenarios live in `data/scenarios/`. The format is:

```json
{
  "scenario_id": "my_scenario",
  "title": "Human-Readable Title",
  "description": "One-paragraph summary shown on scenario select.",
  "briefing": "Optional longer briefing text (2-3 paragraphs). Shown before turn 1.",
  "difficulty_stars": 3,
  "starting_turn": 1,

  "map_rows": [
    "..fhh...vv",
    "..ffh..r..",
    "...hh.rr.."
  ],

  "units": [ ... ],
  "objectives": [ ... ],
  "reinforcements": [ ... ]
}
```

### Map rows

Each character in `map_rows` represents one hex. Rows are indexed top-to-bottom (r=0 at top),
columns left-to-right (q=0 at left). The map width is the length of the first row; height is
the number of rows.

| Char | Terrain |
|------|---------|
| `.`  | Open |
| `r`  | Road |
| `f`  | Forest |
| `h`  | Hill |
| `R`  | River |
| `v`  | Village |
| `m`  | Marsh |
| `w`  | Fortification |

Elevation is assigned procedurally based on hill clusters. To override elevation for
specific hexes, add an `"elevation_overrides"` dict: `{"q,r": meters, ...}`.

### Units

```json
{
  "id": "blue_inf1",
  "name": "1st Fusiliers",
  "type": "infantry",
  "side": "blue",
  "formation": "column",
  "hp": 10,
  "max_hp": 10,
  "strength": 100,
  "max_strength": 100,
  "morale": "steady",
  "fatigue": 0,
  "ammo": 60,
  "max_ammo": 60,
  "facing": "N",
  "position": {"q": 5, "r": 8}
}
```

**type** options: `infantry`, `cavalry`, `artillery`, `skirmisher`, `commander`, `supply_wagon`

**formation** options:
- Infantry: `column`, `line`, `square`, `skirmish`
- Cavalry: `column`, `line`
- Artillery: `limbered`, `unlimbered`
- Others: `column`

**facing** options: `N`, `NE`, `SE`, `S`, `SW`, `NW`

**morale** options: `steady`, `shaken`, `routing`, `broken`

Supply wagons use `ammo: 0`, `max_ammo: 0`, `type: "supply_wagon"`.
Commanders use `type: "commander"` and have 2 ability uses (handled automatically).

### Objectives

```json
{
  "id": "obj1",
  "name": "Hill Fort",
  "q": 12,
  "r": 8,
  "points": 3
}
```

Objectives award `points` VP to the side that controls them at turn end. A side controls
an objective when they have at least one non-routing unit on the hex and the enemy does not.

### Reinforcements

```json
{
  "turn": 6,
  "side": "blue",
  "entry_hex": [25, 39],
  "units": [
    {
      "id": "blue_reinf1",
      "name": "Reserve Infantry",
      "type": "infantry",
      "side": "blue",
      "formation": "column",
      "hp": 10, "max_hp": 10,
      "strength": 100, "max_strength": 100,
      "morale": "steady", "fatigue": 0,
      "ammo": 60, "max_ammo": 60,
      "facing": "N"
    }
  ]
}
```

`entry_hex` is `[q, r]`. The unit will be placed at that hex on the specified turn;
if occupied, the game tries adjacent hexes. The unit has no `position` field in the
reinforcement definition — position is assigned on arrival.

Multiple waves can be defined for the same side and turn. They are processed in order.

---

## Creating Scenarios with the Editor

Launch the standalone scenario editor:

```bash
python3 ui/scenario_editor_ui.py                       # new blank map
python3 ui/scenario_editor_ui.py --load my_scenario    # load existing
python3 ui/scenario_editor_ui.py --width 40 --height 30
```

### Editor hotkeys

| Key | Action |
|-----|--------|
| `T` | Switch to terrain-paint mode |
| `P` | Switch to unit-placement mode |
| `O` | Switch to objective-placement mode |
| `R` | Remove mode (click to delete) |
| `Tab` | Cycle current brush / unit template |
| `U` | Undo last action |
| `S` | Save (validates first, shows errors if invalid) |
| `L` | Load scenario from file |
| `N` | New blank map (prompts for size) |
| `Q` | Quit (warns if unsaved) |
| Arrow keys | Pan camera |
| Scroll | Zoom |

The editor exports standard scenario JSON compatible with the game loader.
Reinforcements must currently be added manually to the JSON file after export.

---

## Running Tests

The test suite is fully headless (no display required):

```bash
# All tests
SDL_VIDEODRIVER=dummy python3 -m unittest discover -s tests

# Specific module
SDL_VIDEODRIVER=dummy python3 -m unittest tests.test_combat
SDL_VIDEODRIVER=dummy python3 -m unittest tests.test_morale_cascade
SDL_VIDEODRIVER=dummy python3 -m unittest tests.test_ai_targeting

# Verbose
SDL_VIDEODRIVER=dummy python3 -m unittest discover -s tests -v
```

Tests are deterministic — they use seeded RNG. `seed=1` is the default throughout.

### Adding tests

New test files go in `tests/`. Follow the naming convention `test_<module>.py`.
Inherit from `unittest.TestCase`. Keep tests fast (<100 ms each) and headless.

---

## Code Style

- **PEP 8** throughout. Max line length: 100 chars.
- **Type hints everywhere** — function signatures, class attributes, return types.
- **`dataclass`** for domain objects. Use `slots=True` for hot-path classes.
- **No magic numbers** — constants in `config.py` or JSON data files.
- **Single-responsibility** — one class/concept per file; keep files under 300 LOC where practical.
- **Docstrings** on public classes and non-trivial methods. One-line for simple getters.
- **Comments** only where the _why_ isn't obvious from the code.
- **No `pygame` imports in `core/` or `ai/`** — keep the headless boundary strict.
- **Pure functions** for combat math, LOS, and scoring — no hidden side effects.
- **Deterministic** — pass RNG explicitly; never call `random.random()` directly.

### Import order

1. Standard library
2. Third-party (`pygame`)
3. Local `core/` imports
4. Local `ai/` imports
5. Local `ui/` imports

Use `from __future__ import annotations` at the top of every file.

---

## Architecture Overview

```
core/
  map.py              HexGridMap, HexCoord, TerrainType, A* pathfinding
  units.py            Unit dataclass, enums (UnitType, Formation, MoraleState, FacingDirection)
  orders.py           OrderBook, Order types
  combat.py           CombatResolver (ranged + melee), preview mode
  fog_of_war.py       VisibilitySnapshot, compute_visibility()
  game.py             GameState, advance_turn(), issue_player_order()
  messenger.py        MessengerSystem, courier delay, interception
  weather.py          WeatherState, time-of-day, Markov transitions
  scenario.py         JSON loader → GameState
  map_generator.py    Procedural map generation
  scenario_generator  Quick Battle generator
  campaign.py         CampaignState, HP carry-over, save/load
  tutorial.py         TutorialDirector, 10-step walkthrough
  scenario_editor.py  Headless editor model (undo stack, validate, export)
  persistence.py      GameState save/load

ai/
  opponent.py         SimpleAICommander — main decision loop
  tactics.py          TacticalPlanner, ReserveManager — per-unit decisions
  evaluation.py       BattlefieldEvaluator — threat scoring, terrain scoring
  strategy.py         ObjectiveSelector — strategic goal selection
  mcts.py             MCTSPlanner — Monte Carlo Tree Search
  belief.py           BeliefMap — probabilistic enemy position tracking
  difficulty.py       AIDifficultyProfile, get_difficulty_profile()
  adaptive.py         AdaptiveController — win-rate tracking, difficulty adjustment
  umpire.py           DigitalUmpire — order validation and sanitization
  playtest.py         Batch AI-vs-AI testing

ui/
  app.py              Main pygame loop, input, drawing orchestration
  map_renderer.py     Hex terrain/fog/unit rendering (3-layer cache)
  unit_renderer.py    NATO counter drawing
  animation.py        AnimationManager, movement/combat effects
  main_menu.py        Title screen
  scenario_select.py  Scenario browser
  quick_battle.py     Quick Battle config UI
  campaign_ui.py      Campaign progress screen
  difficulty_select.py Difficulty picker
  combat_log.py       Scrollable, filterable event log
  unit_detail.py      Left-panel unit stats
  minimap.py          Overview map widget
  tooltip.py          Hover info box
  context_menu.py     Right-click dropdown
  toast.py            Self-dismissing notification toasts
  order_panel.py      Order queue + End Turn button
  hud.py              HUD component container
  camera.py           Axial ↔ world ↔ screen transforms, zoom/pan
  bitmap_font.py      5×7 custom pixel font (no external font dependency)
  themes.py           Colour palette, colour-blind mode
  audio.py            Synthesised sound effects with graceful fallback
  input_handler.py    Formation cycle helper
  scenario_editor_ui.py Standalone scenario editor pygame app
```

---

## Adding New Terrain Types

1. Add the enum value to `core/map.py` `TerrainType`.
2. Add the character mapping in `core/scenario.py` `TERRAIN_CHAR_MAP`.
3. Add movement cost in `core/units.py` `movement_costs()` (or `DEFAULT_MOVEMENT_COSTS`).
4. Add combat modifiers in `core/combat.py` terrain modifier tables.
5. Add colour in `ui/themes.py` `TERRAIN_COLOURS`.
6. Add rendering pattern in `ui/map_renderer.py` `_draw_terrain_detail()`.
7. Add minimap colour in `ui/minimap.py`.
8. Add AI terrain scoring in `ai/evaluation.py` `terrain_score()`.
9. Add a test in `tests/test_map.py` or `tests/test_combat.py`.

## Adding New Unit Types

1. Add the enum value to `core/units.py` `UnitType`.
2. Add default stats (ammo, movement, vision range) in `core/units.py`.
3. Add combat handling in `core/combat.py` if the unit has special attack rules.
4. Add movement costs override if different from default.
5. Add NATO symbol rendering in `ui/unit_renderer.py` `_draw_symbol()`.
6. Add AI behaviour template in `ai/tactics.py` if role-specific logic is needed.
7. Add a factory function in `core/units.py` (e.g. `make_supply_wagon()`).
8. Add tests.
