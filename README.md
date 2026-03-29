# Kriegsspiel — Digital Wargame

A faithful Python/pygame digital adaptation of the 1824 Prussian wargame *Kriegsspiel*,
the first professional military simulation. Play on procedurally-generated or hand-authored
hex battlefields with period-accurate rules, atmospheric fog of war, and a challenging AI
adversary that respects the same fog of war and rules as the player.

---

## Features

### Simulation
- **Hex-grid battlefield** — Seven scenario maps from 10×8 to 60×45 hexes plus procedural
  Quick Battle generation. Nine terrain types (open, road, forest, hill, river, village,
  marsh, fortification, elevation) each with movement and combat modifiers.
- **Fog of war** — Three-state visibility (unexplored / explored / visible) with line-of-sight
  blocking, last-known enemy ghost counters, atmospheric cloud overlay, and soft fog-edge
  shading. AI respects the same fog — no cheating.
- **Rich rules engine** — Ammunition tracking (infantry 60rds, artillery 40rds, skirmishers 30rds),
  morale cascade and rout contagion, entrenchment after 2 hold turns (+25% ranged defence),
  flanking bonus (+40% melee damage from rear arc), cavalry charge and pursuit, weather
  (clear/rain/fog, day/night cycle), commander abilities (Forced March, Inspire, Last Stand),
  supply wagons for resupply, and messenger delays wired into the order system.
- **Elevation** — Uphill movement +30% cost, downhill −10%; ranged attacker +15% damage,
  defender +10% from high ground. Directional hillshade rendering (north slopes darker).
- **Reinforcements** — Scenario-defined waves arrive at the map edge on the specified turn
  (Ligny, Möckern, Full Battle and Grand Battle all include reinforcement schedules).

### AI Opponent
- **Four difficulty levels** — Easy (reactive), Medium (coordinated focus fire, terrain-aware),
  Hard (MCTS 3-turn lookahead, role specialisation), Historical (deepest simulation, 4-turn MCTS).
- **MCTS planning** — Monte Carlo Tree Search with configurable depth and 1 s time budget.
- **Role specialisation** — Cavalry scouts fog boundary and flanks; skirmishers harass at
  optimal range and retreat when threatened; artillery seeks high ground; infantry holds
  defensible terrain facing the enemy.
- **Reserve management** — Holds 20–30% of forces back; cavalry commits for flanking/pursuit,
  artillery repositions to cover routing friendlies, infantry plugs gaps.
- **Morale exploitation** — Prioritises shaken (1.5×) and routing (2.0×) targets to cascade.
- **Fog inference** — Probabilistic enemy position tracking using movement projection (Hard+).
- **Adaptive difficulty** — Tracks win/loss history in `~/.kriegsspiel/stats.json`; silently
  adjusts after 3 consecutive wins or losses.

### UI
- **NATO-style unit counters** — Unit-type symbol (infantry ✕, cavalry /, artillery ●,
  skirmisher ···, commander ✦), HP bar (green→yellow→red), morale bar, facing chevron,
  entrenchment dashes. Scales across 5 zoom levels; circles at low zoom.
- **Atmospheric rendering** — Terrain detail patterns (forest canopy circles with trunks,
  hill contour arcs, marsh reeds, village houses with chimneys, fortification bastions),
  directional elevation hillshade, road and river connectivity lines.
- **Context menu** — Right-click any hex for Move / Attack / Formation / Rally / Hold.
- **Movement preview** — Right-click destination shows dashed path + ghost unit. Confirm
  with left-click; cancel with Escape.
- **Damage estimate tooltip** — Hover over enemy in range to see estimated HP damage and
  morale risk before committing.
- **Animation** — Units slide along paths; ranged fire flash lines; melee crossed-swords;
  floating damage numbers; morale cascade ring. Speed: 1×/2×/4×/Skip (Space).
- **Minimap** — Terrain colours, fog coverage, camera frustum, unit positions, combat pulses.
- **Combat log** — Scrollable, colour-coded, filterable by category (All/Combat/Movement/
  Morale/Orders); click an entry to pan camera to the event location.
- **Score graph** — End-game screen shows turn-by-turn score history as a line chart.
- **Casualty table** — End-game shows per-unit HP, status, and kills.
- **Notification toasts** — Self-dismissing popups for key events (routing, objective captured,
  messenger intercepted).
- **Hotkey overlay** — Press `F1` or `?` for a complete reference.
- **Colour-blind mode** — Press `C` to switch to a shape+colour-blind-safe palette.

### Content
- **7 hand-authored scenarios** including two historical battles (Ligny 1815, Möckern 1813)
  with briefing text, reinforcement schedules, and supply wagons.
- **Quick Battle** — Procedural map with configurable size, force composition, and difficulty.
- **Campaign mode** — Linked sequence of battles with HP carry-over between engagements.
- **Scenario editor** — In-game tool (`python3 ui/scenario_editor_ui.py`) to paint terrain,
  place units and objectives, define reinforcements, and export JSON.
- **10-step interactive tutorial** with contextual guidance.

---

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Requires Python ≥ 3.11 and pygame ≥ 2.6.

---

## Controls

| Input | Action |
|-------|--------|
| `Enter` | End turn |
| `Escape` | Pause / Resume |
| `F1` / `?` | Hotkey reference overlay |
| `C` | Toggle colour-blind mode |
| `F` | Cycle unit formation |
| `H` | Hold position order |
| `R` | Rally unit |
| `1` / `2` / `4` | Animation speed 1×/2×/4× |
| `Space` | Skip all animations |
| Arrow keys | Pan camera |
| Scroll wheel | Zoom in / out |
| Middle-click drag | Pan camera |
| Left click | Select unit |
| Right click | Context menu |

---

## Scenarios

| Name | Map | Units/side | Stars | Notes |
|------|-----|-----------|-------|-------|
| `tutorial` | 10×8 | 2 | ★ | Guided intro to movement, terrain, and combat |
| `skirmish_small` | 25×20 | 4 | ★★ | Fast two-company skirmish across open ground |
| `assault_on_hill` | 35×25 | 5 | ★★★ | Attacker storms a fortified hill |
| `full_battle` | 50×40 | 7+wagons | ★★★★ | Regimental battle with reinforcements |
| `ligny_1815` | 50×40 | 11+wagons | ★★★★ | Napoleon vs Blücher, June 16 1815 |
| `mockern_1813` | 40×35 | 10+wagons | ★★★★ | Yorck's assault on Möckern village |
| `grand_battle` | 60×45 | 10+wagons | ★★★★★ | Brigade-scale action |

```bash
# Launch directly into any scenario
python3 main.py --scenario ligny_1815 --difficulty hard
python3 main.py --scenario grand_battle --seed 42

# Quick Battle (procedural map)
python3 main.py --mode quick_battle

# Main menu (default)
python3 main.py
```

---

## AI Difficulty Guide

| Level | MCTS depth | Focus fire | Role specialisation | Fog inference | Notes |
|-------|-----------|-----------|---------------------|--------------|-------|
| Easy | Off | Off | Off | Off | Reactive, greedy targets |
| Medium | 2 turns | ✓ | Flanking only | Off | Coordinated, terrain-aware |
| Hard | 3 turns | ✓ | Full | ✓ | Dangerous; exploits morale cascades |
| Historical | 4 turns | ✓ | Full | ✓ | Maximum depth; intended for veterans |

Adaptive difficulty tracks your last 3 results and adjusts automatically.

---

## Architecture

```
core/       Headless game engine (map, units, orders, combat, fog of war, scenarios,
            messenger, weather, campaign, tutorial, persistence, scenario editor model)
ai/         Decision-making (SimpleAICommander, MCTS planner, belief maps, tactics,
            evaluation, strategy, adaptive difficulty controller)
ui/         Pygame rendering (app loop, HUD panels, map/unit renderer, animation manager,
            main menu, scenario select, quick battle UI, campaign UI, themes, audio, camera)
data/       Scenario JSON files and configuration
tools/      CLI utilities (profile_game.py, playtest.py)
tests/      227 unit tests covering all engine subsystems (headless, deterministic)
```

### Key design principles
- **Layered**: `core/` → `ai/` → `ui/`. Core never imports pygame.
- **Headless-testable**: all game logic runs without a display. `SDL_VIDEODRIVER=dummy`.
- **Deterministic**: seeded RNG throughout for reproducible replays and testing.
- **Composition over inheritance**: dataclasses and single-responsibility modules.
- **PEP 8, fully typed**: `pyright`/`mypy` clean, type hints everywhere.

---

## Running Tests

```bash
# All 227 tests (headless)
SDL_VIDEODRIVER=dummy python3 -m unittest discover -s tests

# Single module
SDL_VIDEODRIVER=dummy python3 -m unittest tests.test_combat
```

## Profiling

```bash
python3 tools/profile_game.py --scenario full_battle --turns 20
python3 tools/profile_game.py --scenario grand_battle --quick
```

Benchmark results (M-series Mac, 1280×800):

| Scenario | Map | FPS (normal frame) | Notes |
|----------|-----|--------------------|-------|
| full_battle | 50×40 | ~354 | 2.8 ms/frame |
| grand_battle | 60×45 | ~293 | 3.4 ms/frame |

Terrain surface cached per zoom level; fog surface cached per turn. Full 60×45 map renders in <4 ms.

