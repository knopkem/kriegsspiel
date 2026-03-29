# Kriegsspiel — Digital Wargame

A faithful Python/pygame digital adaptation of the 1824 Prussian wargame *Kriegsspiel*,
the first professional military simulation. Play on procedurally-generated or hand-authored
hex battlefields with period-accurate rules, atmospheric fog of war, and a challenging AI.

## Features

- **Hex-grid battlefield** — Five scenario maps from 10×8 to 60×45 hexes. Nine terrain
  types (open, road, forest, hill, river, village, marsh, fort, elevation). Three-state fog
  of war (unexplored / explored / visible) with line-of-sight blocking, last-known enemy
  ghost positions, and soft fog-edge shading.
- **Rich rules engine** — Ammo tracking, morale cascade and rout, entrenchment, flanking
  bonus, cavalry charge, weather effects, commander auras, elevation attack/defence
  modifiers, and the original Reisswitz exchange-piece combat tables.
- **Advanced AI** — MCTS lookahead planning, belief maps for enemy position estimation,
  focus-fire target selection, role specialisation (skirmisher screen, artillery support,
  cavalry exploitation), and four adaptive difficulty levels.
- **Modern UI** — NATO-style unit counters with HP/morale bars, context menu (right-click),
  movement path preview, attack-range overlay, scrollable combat log, minimap with
  camera frustum, notification toasts, hotkey reference overlay, and optional audio.
- **Scenarios** — Five hand-authored scenarios covering introductory to grand-tactical scale.
- **Procedural generation** — `core/map_generator.py` produces random playable maps given
  dimensions, hill density, forest %, river count, and village count.

## Installation

```bash
pip install -r requirements.txt
python3 main.py
```

## Controls

| Input | Action |
|-------|--------|
| `Enter` | End turn |
| `Escape` | Pause / Resume |
| `F1` / `?` | Hotkey reference |
| `C` | Toggle colour-blind mode |
| `F` | Cycle unit formation |
| `H` | Hold position order |
| `R` | Rally unit |
| Arrow keys | Pan camera |
| Scroll wheel | Zoom in / out |
| Middle-click drag | Pan camera |
| Left click | Select unit |
| Right click | Context menu (Move / Attack / Formation / Rally / Hold) |

## Scenarios

| Name | Map size | Description |
|------|----------|-------------|
| `tutorial` | 10×8 | Guided introduction to movement, combat, and orders |
| `skirmish_small` | 25×20 | Fast two-company skirmish across open ground |
| `assault_on_hill` | 35×25 | Blue attacks fortified hill held by Red |
| `full_battle` | 50×40 | Regimental engagement with artillery and cavalry |
| `grand_battle` | 60×45 | Brigade-scale action with reinforcements and objectives |

Load a specific scenario:

```bash
python3 main.py --scenario assault_on_hill
python3 main.py --scenario grand_battle
```

## Architecture

```
core/       Headless game engine — map, units, orders, combat, fog of war, scenarios
ai/         Decision-making — SimpleAICommander, MCTS planner, belief maps, strategy
ui/         Pygame rendering — app, HUD, map/unit renderer, themes, audio, camera
tools/      CLI utilities — profile_game.py for turn-resolution benchmarking
tests/      172 unit tests covering all engine subsystems
```

## Running Tests

```bash
python3 -m unittest discover -s tests
```

## Profiling

```bash
python3 tools/profile_game.py --scenario full_battle --turns 20
python3 tools/profile_game.py --scenario full_battle --quick   # elapsed time only
```

