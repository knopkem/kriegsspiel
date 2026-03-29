# Kriegsspiel — Python Digital Adaptation Plan

## Problem Statement

Port the classic 1824 Prussian Kriegsspiel wargame to a Python-based digital game with:
- Faithful core mechanics (fog of war, simultaneous turns, written orders, combat tables)
- An AI adversary replacing the umpire for solo play
- An AI opponent that plays competently at multiple difficulty levels
- Identified gameplay balance improvements over the original

## Research Summary

### Original Game Essence (Reisswitz 1824)
- **Map**: Topographical, 1:8000 scale. Terrain types: open, road, woods, hills, rivers, villages, marshes
- **Units**: Lead/wooden blocks — infantry half-battalions (450 men, 90 HP), cavalry squadrons (90 riders, 60 HP), artillery batteries (4 calibers), skirmishers, officers
- **Turns**: Simultaneous, each = 2 minutes real time
- **Orders**: Written by players, submitted to umpire, who interprets and executes them
- **Fog of War**: Double-blind; only the umpire sees everything; pieces placed only for units visible to both sides
- **Communication**: Messengers with delay proportional to distance; can be intercepted
- **Combat**: 5 custom dice (I–V), firing tables for infantry/artillery, melee tables for hand-to-hand; results in HP damage
- **HP/Losses**: Infantry uses "exchange pieces" (5/6, 4/6 strength); cavalry/artillery tracked on losses table; half-battalion removed at 50% casualties
- **Victory**: Scenario-based objectives set by umpire (no fixed win conditions)

### Movement Rates (per 2-min turn, in paces; 1 pace ≈ 0.75m)
| Unit Type     | Road  | Open  | Woods/Bad |
|---------------|-------|-------|-----------|
| Infantry col. | 200   | 150   | 75–100    |
| Infantry line | 150   | 150   | 75        |
| Cavalry trot  | 300   | 225   | 110–150   |
| Cavalry gallop| 375   | 300   | —         |
| Horse Arty    | 300   | 200   | 100       |
| Foot Arty     | 200   | 150   | 50–100    |

### Combat Dice (original 5 custom dice)
- **Die I**: Infantry ranged fire (open), even melee, howitzer fire effects
- **Die II**: Skirmisher fire (cover), 3:2 melee odds
- **Die III**: Artillery fire (good conditions)
- **Die IV**: 3:1 melee odds
- **Die V**: Artillery fire (bad conditions), 4:1 melee odds

### Identified Flaws & Balance Issues in the Original
1. **Umpire bottleneck**: Game requires a trained, impartial expert. Games grind to a halt with more than a few units.
2. **Excessive complexity**: Detailed tables and bookkeeping make the game inaccessible and slow.
3. **Player elimination**: Officers can die in battle, permanently removing a player — frustrating and not fun.
4. **Cavalry dominance in melee**: Cavalry HP-per-man ratio (1.5 vs 0.2 for infantry) makes them disproportionately survivable against ranged fire, and decisive in melee without sufficient counters.
5. **No morale system**: Units fight at full effectiveness until destroyed. Real troops routed, panicked, or refused orders — none of this is modeled.
6. **No supply/fatigue**: Unlimited movement and combat capability — no penalty for sustained operations.
7. **Artillery lacks counter-battery**: No specific rules for artillery targeting other artillery effectively.
8. **Communication frustration**: Messenger delays can make the game feel unresponsive without adding tactical depth for casual players.
9. **Snowball effect**: Once one side gains an advantage, the loss of units compounds since there's no comeback mechanic (no reinforcement timing, no defensive bonuses for desperate situations).
10. **Deterministic victory conditions**: Scenario objectives are set by umpire, but there's no graduated victory system (decisive win vs marginal win).

## Proposed Improvements for the Digital Version
1. **Morale system**: Units have morale (Steady → Shaken → Routing → Broken). Affected by casualties, flanking, nearby routs, commander proximity. Routing units flee and can rally.
2. **Fatigue system**: Units accumulate fatigue from movement and combat. Fatigued units move slower and fight worse. Rest recovers fatigue.
3. **Improved cavalry balance**: Infantry in square formation gets massive melee defense vs cavalry (historically accurate). Cavalry charges expend significant fatigue. Cavalry cannot gallop through woods.
4. **Supply lines**: Optional rule — units far from supply sources gradually lose effectiveness.
5. **Graduated victory**: Points for objectives held, casualties inflicted, territory controlled. Decisive/marginal/draw outcomes.
6. **Defensive bonuses**: Units in cover, behind fortifications, or on hills get significant combat bonuses, giving losing side a fighting chance.
7. **Rally mechanic**: Broken units can attempt to rally near commanders, giving comeback potential.
8. **Simplified communication**: Digital version auto-delivers orders with distance-based delay, but no manual messenger management. Optional "advanced" mode for purists.
9. **Counter-battery fire**: Artillery can target enemy artillery with specific effectiveness tables.
10. **Commander abilities**: Officers provide morale bonuses and can issue special orders (forced march, last stand, etc.) rather than being fragile units that eliminate players.

---

## Architecture Overview

```
kriegsspiel/
├── README.md
├── requirements.txt
├── main.py                    # Entry point
├── config.py                  # Game constants, tuning parameters
│
├── core/                      # Pure game logic (no UI)
│   ├── __init__.py
│   ├── game.py                # Game state machine, turn loop
│   ├── map.py                 # Hex map, terrain, LOS, pathfinding
│   ├── units.py               # Unit types, stats, formations, HP/morale
│   ├── combat.py              # Combat resolution (ranged, melee, artillery)
│   ├── orders.py              # Order system (move, attack, form, rally)
│   ├── fog_of_war.py          # Visibility, scouting, hidden info
│   ├── messenger.py           # Communication delay simulation
│   ├── dice.py                # Custom dice system (faithful to original 5-die system)
│   └── scenario.py            # Scenario loader (objectives, deployment, victory)
│
├── ai/                        # AI systems
│   ├── __init__.py
│   ├── umpire.py              # AI umpire — adjudicates rules, resolves ambiguity
│   ├── opponent.py            # AI opponent — plays as enemy commander
│   ├── strategy.py            # High-level strategic planning (objectives, reserves)
│   ├── tactics.py             # Tactical decision-making (formations, targeting)
│   ├── evaluation.py          # Board evaluation heuristics
│   └── difficulty.py          # Difficulty scaling (easy/medium/hard/historical)
│
├── data/                      # Static game data
│   ├── combat_tables.json     # Firing and melee tables (from 1824 rules)
│   ├── movement_tables.json   # Movement rates by unit/terrain
│   ├── unit_templates.json    # Unit type definitions
│   └── scenarios/             # Scenario files
│       ├── tutorial.json
│       ├── skirmish_small.json
│       ├── assault_on_hill.json
│       └── full_battle.json
│
├── ui/                        # User interface (see UI/UX Design chapter)
│   ├── __init__.py
│   ├── app.py                 # Top-level pygame loop, event dispatch
│   ├── camera.py              # Camera (pan, zoom, world↔screen transforms)
│   ├── map_renderer.py        # Base terrain surface (DEM or custom)
│   ├── hex_overlay.py         # Hex grid lines, highlights, move/attack overlays
│   ├── fog_renderer.py        # Fog of war overlay rendering & animation
│   ├── unit_renderer.py       # NATO-style unit counters at all zoom levels
│   ├── hud.py                 # Top bar, turn/phase, settings
│   ├── minimap.py             # Minimap widget with camera rect & click-to-jump
│   ├── order_panel.py         # Right-side order queue panel
│   ├── unit_detail.py         # Left-side unit info detail card
│   ├── combat_log.py          # Bottom scrollable combat event log
│   ├── tooltip.py             # Floating hover tooltip system
│   ├── input_handler.py       # Mouse/keyboard input routing, hotkeys
│   ├── animation.py           # Turn resolution animations
│   ├── themes.py              # Colour palette, fonts, style constants
│   └── assets/                # Fonts, textures, sounds
│
└── tests/                     # Test suite
    ├── test_combat.py
    ├── test_movement.py
    ├── test_fog_of_war.py
    ├── test_morale.py
    ├── test_ai.py
    └── test_scenarios.py
```

---

## UI / UX Design

### Design Philosophy

The UI should evoke the *feel* of studying a Napoleonic-era campaign map in a general's
headquarters — parchment tones, clean cartographic lines, austere military aesthetics —
while providing the responsiveness and clarity of a modern strategy game. Every pixel of
screen real estate serves either situational awareness or order entry. Nothing decorative
that doesn't also inform.

**Guiding principles:**
1. **Map is king** — the map viewport dominates the screen (≥75% of area). All other
   panels are peripheral, collapsible, or overlaid semi-transparently.
2. **Progressive disclosure** — show only essential info at a glance; reveal detail on
   hover / click / zoom. Avoid cognitive overload.
3. **Fog of war as a first-class visual** — unexplored/out-of-sight terrain is not just
   hidden, it's *atmospherically* obscured (soft vignette, desaturated colours, subtle
   parchment texture) so the player *feels* the uncertainty.
4. **Minimal clicks** — selecting a unit, issuing a move, and confirming should take ≤3
   interactions. Context menus on right-click; drag for movement paths.
5. **Accessibility** — colour-blind-friendly palette with shape/pattern differentiation;
   scalable text; high-contrast mode toggle.

---

### Map System

#### Real Topographic Maps (Recommended Primary Approach)

Use freely available **SRTM DEM** (Shuttle Radar Topography Mission Digital Elevation
Model) data to render *real-world terrain* for historical and custom battlefields.

**Data pipeline:**
1. **Acquire DEM tiles** — SRTM 1-arc-second (~30 m resolution) from USGS EarthExplorer,
   OpenTopography, or CGIAR-CSI. GeoTIFF format. Cover any region on Earth.
2. **Load with `rasterio`** — read GeoTIFF into a NumPy elevation array. Crop to the
   scenario bounding box (e.g. 4 km × 3 km around a battlefield).
3. **Derive terrain layers:**
   - **Elevation** → colour ramp (greens for lowland, tans/browns for hills, grey for
     ridges). Continuous gradient, not flat colour bands.
   - **Hillshade** → compute a shaded-relief surface (azimuth 315°, altitude 45°) using
     NumPy. Multiply onto elevation colours for a 3D-like cartographic look.
   - **Slope** → classify into flat / gentle / steep / cliff. Steep slopes affect movement
     and LOS.
   - **Hydrography** — overlay river / stream vectors (from OpenStreetMap or
     Natural Earth) or detect from DEM flow-accumulation.
4. **Generate hex overlay** — project the hex grid onto the DEM surface. Each hex is
   assigned a terrain type based on the dominant elevation, slope, and land-cover within
   its boundary.
5. **Pre-render base surface** — bake the coloured DEM + hillshade + rivers + roads into
   a single high-res PNG at load time. This is the static background that never changes
   during play. Overlay hex borders, units, and fog on top at runtime.

**Advantages:** gorgeous, historically authentic terrain; every hill the real troops
fought over is in the right place; automatic LOS calculations from real elevation data;
infinite map variety by choosing different real-world locations.

**Performance note:** A 4 km × 3 km battlefield at 30 m DEM resolution is only ~130 × 100
elevation samples — trivial to process. The pre-baked base surface is a single texture blit
per frame.

#### Custom / Procedural Maps (Fallback & Tutorial)

For quick-start scenarios and tutorials, also support hand-authored hex maps defined in
JSON (terrain type per hex). A simple procedural generator can also create random
battlefields with configurable hill density, forest coverage, and river placement.

#### Map Dimensions & Scale

| Parameter        | Value                  | Rationale                                  |
|------------------|------------------------|--------------------------------------------|
| Hex size         | ~75 m across (100 paces) | Fine enough for company-level maneuver   |
| Typical map      | 50–80 hexes wide × 40–60 tall | ~4 × 3 km, a typical Napoleonic engagement |
| Large battle     | up to 150 × 100 hexes | ~11 × 7.5 km (e.g. full Waterloo field)    |
| Coordinate system| Axial (q, r) with cube conversion | Clean math for distance, LOS, rings     |

---

### Camera & Navigation

The map is far larger than the screen; the player navigates with a smooth camera system.

| Control              | Action                                               |
|----------------------|------------------------------------------------------|
| **Mouse drag (MMB)** | Pan the camera freely across the map                 |
| **Arrow keys / WASD**| Pan at a fixed speed (configurable)                  |
| **Scroll wheel**     | Zoom in / out (5 discrete levels, smooth interpolation)|
| **Minimap click**    | Jump camera to clicked location                      |
| **Home key**         | Centre camera on selected unit or HQ                 |
| **Edge scrolling**   | Optional: pan when cursor touches screen edge        |

**Zoom levels:**

| Level | Hex diameter on screen | What you see                              |
|-------|------------------------|-------------------------------------------|
| 1     | ~12 px                 | Full battlefield overview; units as dots   |
| 2     | ~24 px                 | Operational view; unit type icons visible  |
| 3     | ~48 px (default)       | Tactical view; full unit counters visible  |
| 4     | ~80 px                 | Close tactical; formation details, facing  |
| 5     | ~120 px                | Inspection; individual terrain features    |

Implementation: a `Camera` class holding `(x, y, zoom)`. World-to-screen and
screen-to-world transforms. Render only hexes within the viewport (frustum culling).
Zoom via `pygame.transform.smoothscale` of the pre-baked map surface, with unit sprites
rendered at native resolution on top.

---

### Unit Representation

#### Visual Style: NATO-Inspired Counters

Units are drawn as rectangular **counters** (like classic board-wargame chits) sitting on
their hex, using simplified **APP-6 / NATO military symbology** for instant recognition.

```
┌─────────────┐
│  ╳╳          │  ← unit-type symbol (infantry: ╳╳, cavalry: /, artillery: ●)
│  II          │  ← echelon size indicator (II = battalion, I = company, III = regiment)
│  3/Fus       │  ← designation (3rd Fusilier battalion)
│ ██████░░░░   │  ← HP bar (green→yellow→red as HP drops)
│ ▓▓▓▓▓░░░░░  │  ← morale bar (blue = steady, orange = shaken, red = routing)
└─────────────┘
```

**Colour coding:**
- **Player units**: Blue background, white symbols
- **Enemy units** (when visible): Red background, white symbols
- **Neutral / unknown**: Grey background

**At different zoom levels:**
- **Zoom 1–2:** Counter collapses to a coloured dot/pip with a unit-type icon (3×3 px symbol)
- **Zoom 3 (default):** Full counter as above, ~40×30 px
- **Zoom 4–5:** Counter expands; formation shape drawn on the hex (line, column, square);
  individual sub-unit pips visible; facing arrow shown

**Rendering approach:** Counters are rendered programmatically using `pygame.draw` and
`pygame.font` (no sprite sheets needed for counters). This keeps them resolution-independent
and makes it trivial to reflect real-time stat changes. A `UnitRenderer` class accepts a
`UnitView` dataclass and draws the appropriate counter.

#### Stacking & Overlap

Multiple units on the same hex are drawn as a slightly offset stack (top unit fully
visible, others peeking out beneath). A small badge shows the stack count. Clicking cycles
through the stack.

#### Selection & Highlighting

- **Hover:** Hex border brightens; quick tooltip with unit name + HP + morale.
- **Click (LMB):** Selects unit; hex glows with team colour; available movement hexes
  highlighted in translucent green; attack-range hexes in translucent red.
- **Multi-select (Shift+Click or drag-box):** Select multiple units for group orders.
- **Selected-unit trail:** A dashed line shows the planned movement path.

---

### Order Entry UX

Orders are the player's primary interaction. The UI must make issuing them fast and
intuitive while preserving the *feel* of writing orders to subordinates.

#### Quick Orders (Mouse)

| Interaction               | Order issued                                    |
|---------------------------|-------------------------------------------------|
| Select unit → RMB on hex  | **Move** to that hex (path auto-calculated)     |
| Select unit → RMB on enemy| **Attack** that enemy (move into range + fire)   |
| Select unit → `F` key     | Cycle **Formation** (line → column → square → skirmish)|
| Select unit → `R` key     | **Rally** (attempt to recover morale)            |
| Select unit → `H` key     | **Hold** position (stand and defend)             |
| Select unit → `G` key     | **Retreat** toward rear / supply                 |

A **ghost preview** of the unit at its destination appears before confirmation (`LMB` to
confirm, `Escape` to cancel). Movement cost (turns) and any fatigue warning shown inline.

#### Order Panel (Side Panel)

A collapsible panel on the right (~200 px wide) listing:
- Current turn's queued orders (editable until "End Turn")
- Each order shown as: `[unit icon] [order type] → [destination/target]`
- Drag to reorder priority; click ✕ to cancel
- "End Turn" button at the bottom (also bound to `Enter`)

#### Order Confirmation Phase

After both sides submit orders (or the AI finishes), a brief **resolution animation**
plays: units slide along paths, fire effects flash, casualties appear as floating numbers,
morale state changes pulse on the counter. Speed adjustable (1×, 2×, 4×, skip).

---

### HUD Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ [Turn 14] [Phase: Orders]  [⏱ 1:24]         [⚙ Settings] [? Help]│  ← Top bar
├───────────────────────────────────────────────┬────────────────────┤
│                                               │ ┌────────────────┐│
│                                               │ │  ORDER PANEL   ││
│                                               │ │                ││
│              MAP VIEWPORT                     │ │ 1. 3/Fus → D5  ││
│              (≥75% of screen)                 │ │ 2. 1/Hus → F8  ││
│                                               │ │ 3. Bty A Hold  ││
│                                               │ │                ││
│                                               │ │ [End Turn ↵]   ││
│                                               │ └────────────────┘│
├──────────┬────────────────────────────────────┴────────────────────┤
│ MINIMAP  │                    COMBAT LOG                          │  ← Bottom bar
│  ┌────┐  │ Turn 13: 3/Fus fires on 2/Gren — 12 HP damage         │
│  │    │  │ Turn 13: 1/Hus charges 4/Drag — melee, 3:2 odds       │
│  └────┘  │ Turn 13: Bty A bombards hex E6 — 8 HP, shaken         │
└──────────┴────────────────────────────────────────────────────────┘
```

| Panel          | Size / Position         | Content                                       |
|----------------|-------------------------|-----------------------------------------------|
| **Top bar**    | Full width, ~32 px tall | Turn number, phase, timer, settings, help      |
| **Map viewport** | Centre, fills remaining | Hex map with units, fog, terrain              |
| **Order panel**| Right, ~200 px, collapsible (Tab) | Current turn's order queue            |
| **Minimap**    | Bottom-left, ~150×120 px | Entire battlefield; camera rect shown; click to jump |
| **Combat log** | Bottom, ~100 px tall, scrollable | Chronological events with icons; filterable by type |
| **Unit info tooltip** | Floating near cursor | Appears on hover; shows name, type, HP, morale, fatigue, formation, orders |

#### Unit Info Detail Panel (Click)

When a unit is selected, a **detail card** slides in from the left (~250 px wide):

```
┌──────────────────────┐
│ 3rd Fusilier Bn      │
│ ╳╳  II               │
│ Commander: Maj. Braun │
├──────────────────────┤
│ HP:      ████░░ 67/90│
│ Morale:  ████████ Steady │
│ Fatigue: ██░░░░░░ Low│
│ Formation: Line       │
│ Facing:   NE          │
├──────────────────────┤
│ Strength: 378/450 men│
│ Firepower: 14 (eff.) │
│ Move:     3 hexes/turn│
│ Range:    4 hexes     │
├──────────────────────┤
│ Current order: Move→D5│
│ ETA: 2 turns          │
└──────────────────────┘
```

---

### Fog of War Visuals

The fog of war is the game's signature mechanic and deserves premium visual treatment.

| Visibility state    | Visual treatment                                        |
|---------------------|---------------------------------------------------------|
| **Visible**         | Full colour, full detail, unit counters shown           |
| **Previously seen** | Desaturated, slightly darkened; terrain visible but units removed; ghosted "last known position" markers for enemy units |
| **Never seen**      | Heavy fog overlay (semi-transparent parchment/cloud texture at ~60% opacity); hex borders barely visible; no terrain detail |

**Transition:** When fog lifts (unit moves into LOS), the reveal animates — fog fades out
over 0.3s with a subtle "clearing" effect. When fog rolls back in (unit leaves LOS), it
fades in gently.

**"Last known position" markers:** When an enemy unit was previously seen but is no longer
in LOS, a semi-transparent ghosted counter remains at its last observed position with a
small `?` badge and the turn number it was last seen (`T12`). This gives the player
something to reason about — "they were *here* 5 turns ago…"

---

### Resolution & Display

| Setting            | Default          | Notes                                     |
|--------------------|------------------|-------------------------------------------|
| Window size        | 1280 × 800       | Resizable; minimum 1024 × 768             |
| Fullscreen         | Optional (F11)   | Scales to native resolution               |
| Target FPS         | 60               | Map is mostly static; only units animate   |
| Colour palette     | Warm cartographic | Parchment base (#F5E6C8), forest green (#3A6B35), water blue (#4A7C9B), road tan (#C4A35A), hill brown (#8B6F47) |
| Font               | Clean sans-serif for UI (e.g. Source Sans Pro); serif for flavour text (e.g. EB Garamond) | Bundled as TTF in assets/ |

---

### Audio (Stretch Goal)

Understated ambient audio to reinforce atmosphere:
- **Background:** Distant birdsong, wind; subtle drums during combat phase
- **Events:** Musket volley crack (ranged fire), cannon boom (artillery), cavalry trumpet
  (charge), cheer/groan (morale shift)
- **UI:** Soft click on selection, paper-rustle on order submission, bell chime on turn end

All audio optional and individually togglable.

---

### Updated Architecture (UI layer)

The original `ui/` directory is expanded to match the design above:

```
ui/
├── __init__.py
├── app.py                  # Top-level pygame loop, event dispatch
├── camera.py               # Camera class (pan, zoom, world↔screen transforms)
├── map_renderer.py         # Renders base terrain surface (DEM or custom)
├── hex_overlay.py          # Draws hex grid lines, highlights, movement/attack overlays
├── fog_renderer.py         # Fog of war overlay rendering & animation
├── unit_renderer.py        # Draws NATO-style unit counters at all zoom levels
├── hud.py                  # Top bar, turn/phase indicator, settings button
├── minimap.py              # Minimap widget with camera rect & click-to-jump
├── order_panel.py          # Right-side order queue panel
├── unit_detail.py          # Left-side unit info detail card
├── combat_log.py           # Bottom scrollable combat event log
├── tooltip.py              # Floating hover tooltip system
├── input_handler.py        # Mouse/keyboard input routing, hotkeys
├── animation.py            # Turn resolution animations (movement, fire, morale)
├── themes.py               # Colour palette, font definitions, style constants
└── assets/
    ├── fonts/              # Bundled TTF files
    ├── textures/           # Fog texture, parchment background
    └── sounds/             # Optional audio files
```

---

## Implementation Todos

### Phase 1: Core Engine
1. **hex-map-system** — Implement hex grid map with terrain types (open, road, forest, hill, river, village, marsh, fortification). Include A* pathfinding and line-of-sight (LOS) raycasting.
2. **unit-system** — Unit classes: Infantry, Cavalry, Artillery, Skirmisher, Commander. Each has HP, morale, fatigue, formation state, movement rates. Exchange-piece logic for infantry.
3. **dice-and-combat-tables** — Implement the 5-die system faithfully. Build combat resolution for: infantry fire, skirmisher fire, artillery fire (good/bad conditions), melee at various odds (even, 3:2, 3:1, 4:1). Load tables from JSON.
4. **order-system** — Orders: Move, Attack, Change Formation, Rally, Hold, Retreat. Orders are queued and executed simultaneously. Support order delays.
5. **turn-engine** — Simultaneous turn resolution: collect orders → resolve movement → resolve combat → apply morale/fatigue → update fog of war → check victory.

### Phase 2: Fog of War & Communication
6. **fog-of-war** — Each side only sees units within LOS of their own units. Terrain blocks LOS (forests, hills, buildings). Scouting units (cavalry, skirmishers) have extended vision range.
7. **messenger-system** — Orders between commanders and units have distance-based delay. Option to send scouts for reconnaissance. Intercepted messages reveal enemy orders.

### Phase 3: Morale, Fatigue & Balance
8. **morale-system** — States: Steady → Shaken → Routing → Broken. Triggers: heavy casualties, flanking, nearby routs, isolated units. Rally attempts near commanders.
9. **fatigue-system** — Movement and combat generate fatigue. Fatigued units: reduced movement, reduced combat effectiveness, morale penalty. Rest removes fatigue.
10. **balance-tuning** — Infantry square vs cavalry, defensive terrain bonuses, counter-battery fire, graduated victory scoring. Playtest and tune all combat tables.

### Phase 4: AI Adversary
11. **ai-evaluation** — Board evaluation heuristic: unit strength, position, morale, control of objectives, threat assessment, line of retreat.
12. **ai-tactics** — Tactical AI: formation selection, targeting priority, flanking maneuvers, retreat decisions, artillery placement. Uses minimax or MCTS for local decisions.
13. **ai-strategy** — Strategic AI: main effort direction, reserve commitment, reconnaissance priorities, objective prioritization. Behavior-tree or utility-based system.
14. **ai-umpire** — Automated adjudication: interpret ambiguous orders, resolve edge cases, determine LOS disputes, manage scenario events.
15. **ai-difficulty** — Difficulty levels: Easy (delays decisions, ignores flanking), Medium (competent but predictable), Hard (optimizes with some fog exploitation limits), Historical (follows period doctrine).

### Phase 5: UI & Scenarios
16. **pygame-renderer** — Hex map rendering with terrain sprites, unit blocks (color-coded), fog overlay, movement/attack indicators, minimap.
17. **order-ui** — Click-to-select units, right-click to issue orders, order queue display, formation selector, rally button.
18. **hud-and-info** — Turn counter, phase indicator, selected unit stats, morale/fatigue bars, combat log, victory progress.
19. **scenarios** — Create 4 scenarios: Tutorial (small, guided), Small Skirmish (2–3 units each), Hill Assault (attacker/defender), Full Battle (10+ units, full rules).
20. **tutorial-mode** — Guided tutorial that introduces mechanics one at a time: movement → combat → fog → morale → full game.

### Phase 6: Polish & Testing
21. **test-suite** — Unit tests for all core systems (combat math, movement, LOS, morale transitions, AI decisions). Integration tests for full turn resolution.
22. **replay-system** — Record game state each turn. Allow replay with full information revealed (great for learning).
23. **balance-playtest** — Automated AI-vs-AI games to detect balance issues. Statistics on win rates by side, unit effectiveness, scenario fairness.

---

## AI Adversary Design (Detail)

### Architecture
The AI operates under the same fog-of-war constraints as the human player. It maintains a **belief state** — its best estimate of enemy positions based on:
- Last known positions of enemy units
- Scouting reports
- Sound of combat (artillery fire reveals approximate position)
- Logical inference (if enemy was moving north, they're probably further north now)

### Decision Layers
1. **Strategic Layer** (every 5–10 turns): Decide overall plan — attack left flank, defend center, probe with cavalry. Uses utility scoring of possible strategies.
2. **Tactical Layer** (every turn): For each unit group, decide specific orders — move to hex X, form line, target unit Y. Uses local search / minimax.
3. **Reactive Layer** (immediate): Respond to new information — enemy spotted, unit routing, flanked. Triggers immediate order adjustments.

### AI Techniques
- **Monte Carlo Tree Search (MCTS)**: For exploring possible outcomes of tactical decisions under uncertainty
- **Influence maps**: For understanding territorial control, threat zones, and safe corridors
- **Doctrine templates**: Pre-programmed tactical patterns (refuse flank, echelon attack, cavalry screen) that the AI can select from
- **Bayesian inference**: For updating belief state about hidden enemy positions

### Difficulty Scaling
| Level      | Planning Depth | Fog Handling       | Doctrine    | Mistakes       |
|------------|---------------|--------------------|-------------|----------------|
| Easy       | 1-2 turns     | Reacts only        | Basic       | Random delays  |
| Medium     | 3-5 turns     | Simple inference   | Standard    | Occasional     |
| Hard       | 5-10 turns    | Bayesian tracking  | Advanced    | Rare           |
| Historical | 3-5 turns     | Period-accurate    | Napoleonic  | Doctrinal only |

---

## Technology Stack
- **Python 3.11+**
- **pygame 2.x** for rendering and input
- **numpy** for efficient map/combat calculations
- **rasterio** for loading real-world DEM/GeoTIFF elevation data
- **json** for data tables and scenarios
- **pytest** for testing
- **dataclasses** for clean data models
- Optional: **pygame-gui** for UI widgets

## Python Coding Rules
- Follow common professional Python conventions: **PEP 8** style, clear naming, small focused modules, and readable control flow over clever shortcuts.
- Prefer **type hints throughout** and keep public interfaces explicit. Use `dataclass` or small immutable value objects for core domain data where appropriate.
- Keep the architecture **modular and layered**:
  - `core/` contains deterministic game rules and domain logic only
  - `ai/` depends on `core/` abstractions, not on UI details
  - `ui/` renders state and collects player input, but does not contain battle rules
  - `data/` stores configuration and tables, separated from code
- Favor **composition over inheritance** unless inheritance clearly models the domain.
- Keep functions and classes **single-responsibility**. Split files before they become large or mix unrelated concerns.
- Avoid hidden side effects. Prefer pure functions for combat math, LOS, visibility, scoring, and other deterministic calculations.
- Use **dependency injection** for pluggable systems such as AI policies, scenario loaders, random number generators, and rules variants.
- Define stable internal interfaces with **protocols / abstract base classes** where multiple implementations are expected.
- Centralize constants and tuning parameters in configuration/data files instead of scattering magic numbers across the codebase.
- Handle errors explicitly and fail loudly in development for invalid game states or malformed scenario data.
- Write docstrings for non-obvious public classes, modules, and algorithms; keep inline comments brief and only where they add real clarity.
- Maintain strong testability: core systems must run headless, without pygame, so they can be unit tested independently.
- Preserve deterministic simulation when needed by allowing seeded randomness for tests, AI evaluation, and replay generation.
- Prefer standard library solutions first, and add third-party dependencies only when they clearly improve correctness or maintainability.

## Key Design Decisions
1. **Hex grid, not continuous map**: Hexes provide clean movement, LOS, and combat geometry while preserving the free-form feel. Hex size = ~100 paces (75m), giving fine granularity.
2. **Simultaneous turns preserved**: Both sides submit orders, then resolution happens — faithful to the original's core design.
3. **Custom dice preserved but automated**: The 5-die system is implemented faithfully in code; players see the roll results in the combat log.
4. **Fog of war is the core feature**: The entire UI is built around showing only what the player's side can see. The "reveal" at game end is a key moment.
5. **AI plays by the same rules**: The AI opponent never cheats — it operates under the same fog of war and information constraints as the player.

## Implementation Progress
- Completed the planned core engine: hex map, LOS, pathfinding, unit system, delayed orders, combat tables, morale, fatigue, fog of war, messenger delays, scenarios, replay capture, and turn engine.
- Implemented a playable pygame prototype with zoom/pan, order entry, selected-unit details, minimap, event log, and tutorial overlay.
- Added a rule-based AI opponent, AI evaluation helpers, digital umpire sanitization, and an AI-vs-AI balance playtest runner.
- Verified the project with a full automated suite (`45` tests passing), syntax compilation, and a headless pygame app initialization check.
