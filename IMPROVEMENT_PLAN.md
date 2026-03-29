# Kriegsspiel — Improvement Plan

> **Baseline snapshot (March 2026):** 3,490 LOC across 36 files, 46 passing tests.
> The current build is a functional MVP: hex grid, basic units, simple combat, fog of
> war, a rule-based AI, and a minimal pygame UI. This plan details what to build next
> to turn it into a polished, deep, and enjoyable wargame.

---

## 1  Current State Assessment

### What works well
| System | Rating | Notes |
|--------|--------|-------|
| Hex grid & pathfinding | ★★★★ | Solid A*, LOS, terrain costs |
| Unit model | ★★★★ | Formations, morale chain, fatigue, exchange pieces |
| Combat resolver | ★★★★ | Ranged + melee, dice tables, terrain/formation modifiers |
| Order system | ★★★★ | Delayed queue, priority, status tracking |
| Fog of war engine | ★★★ | Three-state visibility, last-known positions |
| Scenario loader | ★★ | JSON-based but content is thin |
| AI opponent | ★★ | Reactive single-turn heuristics, easily exploitable |
| UI rendering | ★★ | Functional but visually basic: flat-colour hexes, text abbreviations for units |
| Test coverage | ★★ | 46 tests cover happy paths; many edge cases untested |

### Key weaknesses
1. **Maps are tiny** — largest scenario is 13×10 hexes (~1 km²); plan calls for 50–80 × 40–60.
2. **No visual feedback** — no HP bars, morale gauges, movement previews, or animations.
3. **AI is trivial** — greedy closest-target, no lookahead, no coordination, predictable retreat to map edge.
4. **Missing core rules** — messenger delays not wired into game loop, no morale cascade, no ammo, no reinforcements, no save/load.
5. **UI is spartan** — bitmap font only, no context menus, no settings screen, no pause, no end-game summary.
6. **No real terrain rendering** — flat solid-colour hexes; plan envisioned hillshaded DEM or at least textured hexes.
7. **Tutorial is a stub** — 3 hardcoded sentences, no interactive guidance.

---

## 2  Design Principles (Unchanged)

- **Map is king** — ≥75 % of screen; panels peripheral and collapsible.
- **Fog of war as first-class visual** — atmospheric, not just hidden tiles.
- **AI plays fair** — same fog, same rules, no cheating.
- **Progressive disclosure** — essential info at a glance; detail on hover/click/zoom.
- **Minimal clicks** — select → right-click → confirm in ≤3 interactions.
- **Headless core** — all game logic testable without pygame.
- **PEP 8, typed, modular** — composition over inheritance, single-responsibility files.

---

## 3  Improvement Phases

### Phase A — Richer Map & Terrain  *(foundation for everything visual)*

| ID | Task | Description |
|----|------|-------------|
| A1 | **Larger maps** | Increase `skirmish_small` to 25×20, `assault_on_hill` to 35×25, `full_battle` to 50×40. Add a new `grand_battle` at 80×60. Update scenario JSONs with richer hand-authored terrain strings. |
| A2 | **Terrain texturing** | Replace flat-colour hex fills with per-terrain procedural patterns drawn at render time (hash lines for forest, dots for marsh, diagonal for hills, wavy lines for rivers, small rectangles for villages, star-fort for fortifications). Keep it programmatic — no sprite sheets. |
| A3 | **Elevation shading** | Use hex `elevation` values (already stored but ignored) to apply a hillshade gradient: darker on north-facing slopes, lighter on south. This adds depth without external DEM data. |
| A4 | **Elevation affects gameplay** | Uphill movement costs +30 %; downhill −10 %. Elevation advantage gives +15 % ranged damage and +10 % melee defence. LOS now accounts for intervening high hexes blocking view to lower hexes behind them. |
| A5 | **Road & river connectivity** | Draw roads as tan centre-lines connecting adjacent road hexes; draw rivers as thick blue lines along hex edges between river hexes and their neighbours. |
| A6 | **Procedural map generator** | Create `core/map_generator.py`: given dimensions, hill density, forest %, river count, village count, generate a random but playable battlefield. Useful for skirmish mode and AI training. |

### Phase B — UI Overhaul  *(make it look and feel like a real wargame)*

| ID | Task | Description |
|----|------|-------------|
| B1 | **Proper unit counters** | Replace text-abbreviation rectangles with NATO-style counters: unit-type symbol (crossed infantry, diagonal cavalry, filled circle artillery), echelon size pip, designation label, HP bar, morale bar. Render programmatically with `pygame.draw`. Scale across 5 zoom levels. |
| B2 | **Unit status visualisation** | Show HP bar (green → yellow → red), morale icon (shield steady / cracked shaken / broken routing), fatigue pip (green-yellow-red dot), and formation silhouette on each counter. |
| B3 | **Movement preview & path** | On right-click, show a dashed-line path from selected unit to destination with turn-cost label. Ghost unit at destination. Confirm with left-click, cancel with Escape. |
| B4 | **Attack range overlay** | When a unit is selected, highlight attack-range hexes in translucent red rings. If hovering over an enemy in range, show estimated damage tooltip. |
| B5 | **Context menu** | Right-click on a hex or unit opens a small radial or dropdown menu: Move Here / Attack / Formation / Rally / Hold / Retreat. Replaces the current implicit right-click-only-moves. |
| B6 | **Minimap upgrade** | Render terrain colours on the minimap, show fog of war coverage, draw camera frustum rectangle, and flash unit-conflict dots. |
| B7 | **Combat log overhaul** | Scrollable (mouse wheel), filterable by event type (combat / movement / morale / objective), colour-coded entries, clickable to pan camera to event location. |
| B8 | **Unit detail panel upgrade** | Add visual stat bars, unit portrait area showing the NATO counter at large scale, combat stats (firepower, range, move remaining this turn), current order, and ETA. Expandable/collapsible. |
| B9 | **Turn resolution animation** | After both sides submit orders, animate: units slide along paths (0.3 s per hex), ranged fire shows brief flash lines, melee shows crossed-swords icon, damage numbers float up, morale-change icons pulse. Playback speed adjustable (1×/2×/4×/skip). |
| B10 | **Fog of war visuals** | Unexplored hexes get a dense parchment-fog overlay at 60 % opacity. Previously-seen hexes are desaturated. Fog reveal/close animates with a 0.3 s fade. Last-known enemy positions show a ghosted counter with "?" badge and turn number. |
| B11 | **End-turn & pause UX** | "End Turn" button prominent in order panel; also `Enter` hotkey. Add a pause overlay (`Escape`) with Resume / Save / Settings / Quit. |
| B12 | **End-game summary screen** | On game over: show victory report, score breakdown, casualty tables per unit, turn-by-turn score graph (simple line chart drawn with pygame.draw), and "Replay" button. |
| B13 | **Notification toasts** | Brief, self-dismissing pop-ups for key events: "Unit routed!", "Objective captured!", "Messenger intercepted!". Appear top-centre, fade after 3 s. |
| B14 | **Hotkey reference overlay** | Press `?` or `F1` to show a translucent overlay listing all keyboard shortcuts. |

### Phase C — Core Rules Depth  *(make the simulation richer)*

| ID | Task | Description |
|----|------|-------------|
| C1 | **Wire messenger system into game loop** | Orders issued to distant units actually travel via `MessengerSystem`. The player submits an order; it arrives after `delay_turns` turns. Intercepted orders are lost (with notification). |
| C2 | **Morale cascade** | When a unit routs, adjacent friendly units within 2 hexes must pass a morale check or degrade one step. Commander presence mitigates (50 % chance to ignore cascade). Cascade propagates outward max 2 times. |
| C3 | **Ammunition tracking** | Infantry: 60 rounds (≈10 full volleys). Artillery: 40 rounds. Skirmishers: 30 rounds. Each ranged attack consumes rounds. When empty, unit can only melee or retreat. Resupply via supply wagons (new unit type) or by holding a village hex for 3 turns. |
| C4 | **Reinforcement waves** | Scenarios can define reinforcement entries: `{"turn": 8, "side": "blue", "units": [...], "entry_hex": [0, 5]}`. Units appear at the map edge and are controllable from the next turn. |
| C5 | **Supply wagons & logistics** | New unit type: supply wagon. Slow (road-only, 100 paces/turn). If a combat unit is within 5 hexes of a friendly supply wagon, it recovers 10 ammo/turn and −5 fatigue/turn. Destroying an enemy wagon is worth 3 VP. |
| C6 | **Flanking bonus** | If an attacker's hex is behind the defender's facing direction (rear 2 hexes of the 6-neighbour ring), melee damage +40 % and defender morale degrades an extra step. Requires tracking unit facing. |
| C7 | **Unit facing** | Each unit has a facing direction (one of 6 hex edges). Changing facing costs 1/4 of a movement turn. Facing determines flanking eligibility and formation frontage. |
| C8 | **Cavalry charge & pursuit** | Cavalry in column formation can declare a charge (double movement, +50 % melee damage, +15 fatigue). If the defender routs, cavalry may pursue 1–2 hexes automatically (breakthrough). Charging into a square triggers massive attacker casualties. |
| C9 | **Entrenchment** | A unit that holds the same hex for 2+ consecutive turns gains "entrenched" status: +25 % ranged defence, +15 % melee defence. Lost immediately on movement. |
| C10 | **Weather & time of day** | Scenario can specify weather (clear / rain / fog / snow) and time phase (dawn / day / dusk / night). Rain: −2 hex vision, −20 % ranged damage. Fog: −4 hex vision. Night: −3 hex vision, +30 % morale penalty for combat. |
| C11 | **Commander abilities** | Commanders get 2 special abilities per game: **Forced March** (one unit ignores fatigue for 1 turn), **Inspire** (one unit recovers 2 morale steps), **Last Stand** (+50 % melee defence for 1 turn). Adds strategic depth without complexity. |
| C12 | **Save / Load** | Serialise full `GameState` + replay frames to a JSON file. Load and resume mid-game. Auto-save each turn. |

### Phase D — Smarter AI  *(the plan's "well-playing adversary")*

| ID | Task | Description |
|----|------|-------------|
| D1 | **Threat-based targeting** | Replace closest-enemy targeting with a threat score: `enemy_firepower × exposure / (distance + 1)`. Prioritise high-threat targets (artillery, cavalry in charge range). |
| D2 | **Terrain-aware positioning** | AI evaluates terrain bonuses when choosing destinations. Prefer hills for artillery, forests for infantry defence, roads for fast advance. Weight terrain value in move scoring. |
| D3 | **Focus-fire coordination** | When multiple friendly units can attack the same enemy, concentrate fire on the highest-priority target rather than each unit picking independently. |
| D4 | **Unit role specialisation** | Cavalry: scout ahead, screen, and flank. Skirmishers: harass and retreat. Artillery: deploy on high ground, stay limbered until in range. Infantry: form the main line. Implement as role-based behaviour templates in `ai/tactics.py`. |
| D5 | **Multi-turn planning** | Implement a simple 3-turn lookahead using Monte Carlo rollouts. For each candidate order set, simulate 3 turns of random play ×50 rollouts. Pick the order set with the best average `side_score`. Run in a bounded time budget (0.5 s). |
| D6 | **Reserve management** | AI holds back 20–30 % of forces as a reserve. Reserves commit only when: (a) an objective is contestable, (b) a friendly unit is about to be destroyed, or (c) a flanking opportunity arises. |
| D7 | **Retreat to defensible terrain** | Replace "retreat to map edge" with "retreat to nearest hill/forest/village hex behind the front line". Makes the AI much harder to rout. |
| D8 | **Morale exploitation** | AI preferentially attacks shaken/routing enemies to trigger cascades. Avoids attacking steady enemies in fortifications unless at 3:1+ advantage. |
| D9 | **Adaptive difficulty** | Track player win rate over sessions. If player wins >60 %, silently bump AI to next difficulty. If player loses >60 %, ease off. Stored in a local `~/.kriegsspiel/stats.json`. |
| D10 | **Fog-of-war inference** | AI maintains a probabilistic belief map of enemy positions. When an enemy was last seen moving north 3 turns ago, estimate its current position using movement budget projection. |

### Phase E — Content & Scenarios  *(things to actually play)*

| ID | Task | Description |
|----|------|-------------|
| E1 | **Scenario: Ligny 1815** | Historical battle, ~60×45 map, 20+ units per side, terrain from actual topography. Briefing text, historical objectives, reinforcement schedule. |
| E2 | **Scenario: Möckern 1813** | Smaller historical engagement, ~40×30, attacker/defender asymmetry. Good for learning advanced mechanics. |
| E3 | **Skirmish generator** | "Quick Battle" mode: player picks map size (small/medium/large), army composition budget, and difficulty. Map is procedurally generated (Phase A6). |
| E4 | **Campaign mode (stretch)** | A linked sequence of 3–5 battles where surviving units carry over. Casualties, veterancy, and fatigue persist between battles. Simple strategic map for choosing the next engagement. |
| E5 | **Interactive tutorial** | Replace the 3-step stub with a 10-step guided walkthrough: movement, terrain, formations, combat, morale, fatigue, fog of war, orders queue, rally, and victory conditions. Each step constrains the player (grey out unrelated controls) and validates completion before advancing. |
| E6 | **Scenario editor (stretch)** | Simple in-game editor: paint terrain, place units, set objectives, define reinforcements, export to JSON. Enables community content. |

### Phase F — Polish & Quality  *(make it solid)*

| ID | Task | Description |
|----|------|-------------|
| F1 | **Expand test suite to ≥150 tests** | Cover: AI targeting logic, morale cascade, ammo depletion, reinforcement arrival, save/load round-trip, replay playback, all combat edge cases (0 HP, max range, square vs charge), formation cycling, scenario validation, victory scoring. |
| F2 | **Automated balance testing** | Extend `ai/playtest.py` to run 100 AI-vs-AI games per scenario per difficulty. Output win-rate tables, average game length, most/least effective units, and objective capture rates. Flag imbalances (>60 % win rate for one side). |
| F3 | **Performance profiling** | Profile rendering loop. Pre-bake the terrain surface once; only re-render the fog/unit overlay each frame. Target 60 FPS on maps up to 80×60 at all zoom levels. |
| F4 | **Accessibility pass** | Add a colour-blind mode (shape-only unit differentiation, high-contrast palette). Scalable UI text (small/medium/large). Screen-reader-friendly combat log output. |
| F5 | **Audio (stretch)** | Ambient wind/birds during planning phase, musket volley on ranged fire, cannon boom for artillery, drum roll on turn resolution, trumpet on cavalry charge. All optional and toggleable. |
| F6 | **README & docs refresh** | Update README with screenshots, full feature list, controls reference, scenario descriptions, and AI difficulty guide. Add a CONTRIBUTING.md for the scenario JSON format. |

---

## 4  Priority & Dependency Map

```
Phase A (Maps)  ──────────────────────────┐
  A1 larger maps                          │
  A2 terrain textures ← A1               │
  A3 elevation shading ← A1              │
  A4 elevation gameplay ← A3             ├── unlocks Phase B visuals
  A5 road/river lines ← A1               │
  A6 procedural generator ← A1           │
                                          │
Phase B (UI) ←────────────────────────────┘
  B1 unit counters
  B2 status visualisation ← B1
  B3 movement preview
  B4 attack range overlay
  B5 context menu
  B6 minimap upgrade
  B7 combat log overhaul
  B8 unit detail upgrade ← B1, B2
  B9 turn resolution animation ← B3
  B10 fog of war visuals
  B11 end-turn & pause UX
  B12 end-game summary
  B13 notification toasts
  B14 hotkey overlay

Phase C (Rules) ── can start in parallel with B ──
  C1 messenger wiring
  C2 morale cascade
  C3 ammunition
  C4 reinforcements
  C5 supply wagons ← C3
  C6 flanking bonus ← C7
  C7 unit facing
  C8 cavalry charge ← C7
  C9 entrenchment
  C10 weather & time
  C11 commander abilities
  C12 save / load

Phase D (AI) ← C1–C8 ideally done first ──
  D1 threat targeting
  D2 terrain positioning
  D3 focus fire ← D1
  D4 role specialisation
  D5 multi-turn planning ← D1, D2
  D6 reserve management ← D5
  D7 retreat to terrain ← D2
  D8 morale exploitation ← C2
  D9 adaptive difficulty
  D10 fog inference

Phase E (Content) ← A6, B9, C4 ──
  E1 Ligny scenario
  E2 Möckern scenario
  E3 skirmish generator ← A6
  E4 campaign mode (stretch) ← E1, E2
  E5 interactive tutorial ← B5, B14
  E6 scenario editor (stretch)

Phase F (Polish) ← all above ──
  F1 test expansion
  F2 balance testing ← D5
  F3 performance profiling ← A1, B9
  F4 accessibility
  F5 audio (stretch)
  F6 docs refresh
```

### Suggested build order (interleaved)

| Sprint | Focus | Tasks |
|--------|-------|-------|
| **S1** | Map foundation + core UI | A1, A2, A3, A5, B1, B2, B3 |
| **S2** | Gameplay rules + UI feedback | A4, C1, C2, C7, C6, B4, B5, B10 |
| **S3** | AI upgrade + content | D1, D2, D3, D4, D7, B6, B7, B8, E5 |
| **S4** | Deep simulation + AI planning | C3, C4, C5, C8, C9, D5, D6, D8, B9, B11 |
| **S5** | Scenarios + polish | A6, E1, E2, E3, C10, C11, C12, B12, B13, B14 |
| **S6** | Quality + stretch goals | F1–F6, D9, D10, E4, E6 |

---

## 5  Coding Standards (Carried Forward)

- **PEP 8**, type hints throughout, `dataclass` for domain objects.
- **Layered architecture**: `core/` (headless logic) → `ai/` (decision-making) → `ui/` (rendering).
- **Composition over inheritance**; single-responsibility modules.
- **Pure functions** for combat math, LOS, scoring; dependency injection for RNG/AI policies.
- **No magic numbers** — constants in `config.py` or `data/` JSON files.
- **Testable headless** — all core + AI logic runnable without pygame.
- **Deterministic simulation** — seeded RNG for reproducibility and replay.

---

## 6  Success Criteria

| Milestone | Criteria |
|-----------|----------|
| **Playable beta** | 50×40 map, NATO counters, movement preview, morale cascade, messenger delays, AI with threat targeting + focus fire |
| **Feature-complete** | All Phase A–D tasks done, 3+ scenarios with reinforcements, save/load, turn animations |
| **Release-quality** | ≥150 tests, balance-tested, accessibility pass, audio, docs, 60 FPS on 80×60 maps |
