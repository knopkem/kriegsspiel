# Kriegsspiel — Improvement Plan v2

> **Audit snapshot (March 2026):** 10,730 LOC across 78 Python files, 227 passing
> tests, 7 hand-authored scenarios (10×8 to 60×45). The game is a functional MVP
> with solid core mechanics (combat, morale cascade, ammunition, weather, fog of
> war, facing/flanking, entrenchment, commander abilities) and a workable pygame
> UI (NATO counters, context menus, minimap, toasts, hotkey overlay). This plan
> identifies the gaps that prevent the game from feeling polished and fun, and
> prioritises the highest-impact improvements.

---

## 1  Honest Gap Assessment

### What works well (no further investment needed)
| System | Status | Notes |
|--------|--------|-------|
| Hex grid, pathfinding, LOS | ★★★★★ | Solid A*, terrain costs, facing-aware |
| Unit model | ★★★★★ | Formations, morale chain, fatigue, ammo, facing, entrenchment |
| Combat resolver | ★★★★★ | Ranged + melee, flanking, charge, elevation bonus, weather modifiers |
| Order system + messenger delays | ★★★★ | Delayed queue with distance-based courier delay |
| Fog of war (engine + visuals) | ★★★★★ | Three-state visibility, atmospheric cloud overlay, ghost counters |
| Morale cascade | ★★★★ | 2-hop propagation, commander mitigation |
| Weather & time | ★★★★ | Full day/night cycle, rain/fog modifiers on visibility/combat |
| NATO-style unit counters | ★★★★ | Type symbols, HP/morale bars, formation indicator |
| Context menu & hotkeys | ★★★★ | Right-click actions, F1 overlay, pause menu |
| Toast notifications | ★★★★ | Self-dismissing event popups |
| Scenario editor | ★★★★ | Full standalone editor with terrain/units/objectives |
| Test suite | ★★★★★ | 227 tests, headless, deterministic |

### What needs work (ranked by player impact)

| Problem | Impact | Root Cause |
|---------|--------|------------|
| **No main menu** — game drops into a hardcoded scenario | 🔴 Critical | `main.py` hardcodes scenario list; no menu screen; campaign/skirmish not exposed |
| **No turn animations** — orders resolve instantly, game feels lifeless | 🔴 Critical | Zero animation framework; units teleport, combat has no visual feedback |
| **No movement preview** — right-click blindly queues moves | 🟠 High | Missing dashed-path + ghost-unit confirmation step |
| **AI is exploitable** — no role specialisation, MCTS effectively disabled | 🟠 High | `lookahead_depth=0` on Easy/Normal; cavalry/skirmisher roles are stubs |
| **No reinforcements in any scenario** — mechanic works but unused | 🟠 High | All 7 scenario JSONs have empty reinforcement lists |
| **Campaign/skirmish hidden** — cool features exist but no UI path to them | 🟠 High | `CampaignState` and `generate_skirmish()` not wired to any menu |
| **Maps look flat** — elevation data stored but not rendered as hillshade | 🟡 Medium | Shading is just a 22% brightness reduction; no directional gradient |
| **Terrain textures minimal** — dots and lines only | 🟡 Medium | Procedural patterns are very basic |
| **Combat log not interactive** — can't filter or click to pan | 🟡 Medium | Missing event-type filter + click-to-location |
| **End-game summary thin** — no casualty table, no score graph | 🟡 Medium | Just a text overlay with final scores |
| **AI adaptive difficulty missing** — D9 not implemented at all | 🟡 Medium | No win-rate tracking or difficulty adjustment |
| **Damage estimate tooltip missing** — no hover preview before attacking | 🟡 Medium | Attack overlay shows range but not expected outcome |
| **Historical scenarios lack flavour** — no briefings, no reinforcement schedules | 🟡 Medium | Ligny/Möckern are plain maps with generic objectives |
| **Supply wagons unused** — unit type exists, no scenario includes them | 🟢 Low | Easy content fix |
| **Messenger interception cosmetic** — calculated but never consumed | 🟢 Low | Risk computed then ignored |
| **Audio is synthesized bleeps** — no ambient, no real sound design | 🟢 Low | Works as placeholders; not immersion-breaking |
| **README outdated** — missing screenshots, feature list, controls | 🟢 Low | Documentation debt |

---

## 2  Design Principles (Unchanged)

- **Map is king** — ≥75% of screen; panels peripheral and collapsible.
- **Fog of war as first-class visual** — atmospheric, not just hidden tiles.
- **AI plays fair** — same fog, same rules, no cheating.
- **Progressive disclosure** — essential info at a glance; detail on hover/click/zoom.
- **Minimal clicks** — select → right-click → confirm in ≤3 interactions.
- **Headless core** — all game logic testable without pygame.
- **PEP 8, typed, modular** — composition over inheritance, single-responsibility files.

---

## 3  Improvement Phases

### Phase G — Main Menu & Game Modes  *(make the game accessible)*

| ID | Task | Description |
|----|------|-------------|
| G1 | **Main menu screen** | Title screen with options: Quick Battle, Campaign, Scenario Select, Tutorial, Editor, Quit. Rendered in pygame with the bitmap font at scale 3. Parchment background. Mouse-driven selection. |
| G2 | **Scenario select screen** | List all `data/scenarios/*.json` with name, map size, unit count, difficulty rating. Click to start. Show scenario description/briefing text. |
| G3 | **Quick Battle UI** | Expose `generate_skirmish()`: let player pick map size (small/medium/large), force type (infantry/cavalry/balanced/heavy), AI difficulty (easy/medium/hard). Generate and launch. |
| G4 | **Campaign UI** | Campaign screen showing linked battles on a simple strategic map. Start campaign, resume saved campaign, show battle results between engagements. Wire `CampaignState` into the game loop with HP carry-over. |
| G5 | **Expose all scenarios in CLI** | Update `main.py` argument parser to accept all 7 scenarios + `--mode campaign` + `--mode skirmish`. Auto-discover JSON files instead of hardcoded choices list. |
| G6 | **Difficulty select** | Before any battle, let the player choose Easy/Medium/Hard/Historical. Wire into AI profile selection. Show tooltip explaining what changes per difficulty. |

### Phase H — Turn Animation & Visual Feedback  *(make the game feel alive)*

| ID | Task | Description |
|----|------|-------------|
| H1 | **Animation framework** | Create `ui/animation.py` with `AnimationManager` class. Tracks active animations with start time, duration, interpolation. Renders as overlay after map+units. Game loop enters "animating" state during playback (input blocked). |
| H2 | **Unit movement animation** | After turn resolution, units slide along their movement path at 0.3s per hex. Use linear interpolation of world coordinates. Queue multiple unit moves for parallel playback. |
| H3 | **Ranged fire effect** | Brief flash line (yellow for musket, orange for artillery) from attacker to target, lasting 0.2s. Small impact burst at target. |
| H4 | **Melee combat effect** | Crossed-swords icon pulsing at combat hex for 0.4s. Attacker and defender units briefly shake (2px oscillation). |
| H5 | **Damage numbers** | Floating damage numbers rise from hit units: red "-12 HP" text drifts upward and fades over 1s. Morale changes shown as blue text ("-1 Morale"). |
| H6 | **Morale cascade visual** | When cascade triggers, show expanding translucent red ring from the routing unit, with brief "!" icon on each affected unit. |
| H7 | **Playback speed control** | Bottom-right buttons: 1×, 2×, 4×, Skip. Skip instantly completes all pending animations. Speed multiplier applies to all animation durations. |
| H8 | **Movement preview path** | Right-click on destination shows dashed yellow line along A* path with per-hex turn cost labels. Ghost unit at destination (50% opacity). Left-click confirms, Escape cancels. Replace current instant-queue behaviour. |
| H9 | **Damage estimate tooltip** | When hovering over an enemy in attack range, show tooltip: "Est. damage: 8–14 HP, Morale risk: Shaken→Routing". Computed by running combat resolver in preview mode (no side effects). |

### Phase I — AI Depth  *(make the opponent challenging and believable)*

| ID | Task | Description |
|----|------|-------------|
| I1 | **Enable MCTS on Medium+** | Set `lookahead_depth=2` for Medium, `3` for Hard, `4` for Historical. Currently all zero (disabled). Verify time budget stays under 1s per turn. |
| I2 | **Unit role behaviours** | Replace stub role templates with actual behavioural logic: Cavalry scouts ahead (move toward fog boundary), screens flanks, charges weak targets. Skirmishers harass at max range then retreat. Artillery seeks high ground, stays limbered until in range. Infantry holds the line, rotates facing toward threats. |
| I3 | **Morale exploitation** | AI preferentially attacks shaken/routing enemies to trigger cascades. Avoids attacking steady enemies in fortifications unless 3:1+ advantage. Score shaken targets at 1.5× priority, routing at 2×. |
| I4 | **Adaptive difficulty** | Track player win-rate in `~/.kriegsspiel/stats.json`. After 3 consecutive wins, silently increase difficulty. After 3 consecutive losses, decrease. Show current effective difficulty in pause menu. |
| I5 | **Improved retreat logic** | AI retreats to nearest hill/forest/village hex behind the front line (not toward map edge). Evaluates terrain defense bonus + distance from enemy centroid. Units regroup near commanders when possible. |
| I6 | **Reserve commitment triggers** | Expand reserve logic beyond infantry: cavalry reserves commit for flanking opportunities, artillery reserves reposition to cover breaches. Trigger conditions: objective contested, friendly unit below 30% HP, 2+ enemies concentrated on one flank. |

### Phase J — Scenario Enrichment  *(give players reasons to play)*

| ID | Task | Description |
|----|------|-------------|
| J1 | **Add reinforcements to Ligny** | Prussian reinforcements arrive turn 6 (2 infantry, 1 cavalry from south edge). French reinforcements turn 8 (1 infantry, 1 artillery from west). Update JSON with `reinforcements` array. |
| J2 | **Add reinforcements to Möckern** | Defender gets 1 infantry + 1 artillery at turn 5 from north. Attacker gets 2 cavalry at turn 7 from south. |
| J3 | **Add reinforcements to full_battle** | Both sides get 2-unit waves at turns 6 and 10. Entry hexes on opposite map edges. |
| J4 | **Historical briefings** | Add `briefing` field to Ligny and Möckern JSONs: 2-3 paragraph historical context, strategic situation, victory conditions. Display on scenario select screen and as opening overlay before turn 1. |
| J5 | **Supply wagons in scenarios** | Add 1 supply wagon per side to full_battle, grand_battle, Ligny, and Möckern. Place behind front lines on road hexes. |
| J6 | **Scenario difficulty ratings** | Add `difficulty_stars` (1-5) to each scenario JSON. Tutorial=1, skirmish=2, assault=3, full_battle=4, Ligny/Möckern=4, grand_battle=5. Show on select screen. |
| J7 | **Wire messenger interception** | Complete the interception mechanic: when enemy cavalry/skirmisher is within 2 hexes of the courier path, roll for interception (25% base chance). Intercepted orders are lost with toast notification. |

### Phase K — UI Polish  *(close remaining gaps)*

| ID | Task | Description |
|----|------|-------------|
| K1 | **Combat log filtering** | Add filter buttons (or Tab to cycle) at top of combat log panel: All, Combat, Movement, Morale, Orders. Filter by event category. |
| K2 | **Combat log click-to-pan** | Store event coordinates in `GameEvent`. Click a log entry to pan camera to that hex and briefly highlight it. |
| K3 | **End-game casualty table** | On game-over screen, show scrollable table: unit name, starting HP, final HP (or "Destroyed"), kills, damage dealt. Sort by damage dealt descending. |
| K4 | **End-game score graph** | Draw a simple turn-by-turn line chart (pygame.draw.lines) showing blue vs red cumulative score over time. Record score each turn in `GameState.score_history`. |
| K5 | **Elevation hillshade** | Apply directional gradient to hex fills: north-facing hex edges 15% darker, south-facing 10% lighter. Use elevation difference between neighbours to compute shade. Rebuild terrain surface on zoom change (already cached). |
| K6 | **Richer terrain patterns** | Improve procedural patterns at zoom ≥0.8: forest gets 5-7 varied circles + trunk lines, hills get contour arcs, marsh gets reed-like vertical lines + water shimmer, village gets 2-3 house rectangles + chimney. All drawn with pygame.draw (no sprites). |
| K7 | **Unit facing indicator** | Draw a small white arrow or chevron on the unit counter pointing in the facing direction. Only visible at zoom ≥1.0. |
| K8 | **Entrenchment visual** | Draw small sandbag/earthwork lines (3 short brown dashes) behind entrenched units on the map. |
| K9 | **Replay button** | On game-over screen, add "Replay" button that reloads the same scenario with the same seed. |
| K10 | **Minimap conflict pulse** | When combat occurs, briefly flash a white dot on the minimap at the combat hex location (0.5s pulse). |

### Phase L — Quality & Documentation  *(ship-ready polish)*

| ID | Task | Description |
|----|------|-------------|
| L1 | **Performance verification** | Profile at 60×45 (grand_battle) and 80×60 (generated). Verify ≥30 FPS with animations active. Document results. Fix any bottleneck found. |
| L2 | **UI text scaling** | Add small/medium/large text size option in pause menu → Settings. Scale `BitmapFont` scale parameter and all panel dimensions accordingly. |
| L3 | **README rewrite** | Full README with: feature list, screenshots (capture via pygame.image.save), controls reference, scenario descriptions, AI difficulty guide, installation instructions, architecture overview. |
| L4 | **CONTRIBUTING.md** | Document scenario JSON format, how to create custom scenarios with the editor, test running instructions, code style rules. |
| L5 | **Expand test coverage for new features** | Add tests for: animation manager timing, main menu navigation (headless), campaign flow end-to-end, reinforcement arrival in scenarios, messenger interception, adaptive difficulty file I/O. Target: ≥280 tests. |

---

## 4  Priority & Dependency Map

```
Phase G (Menus) ── no deps, start immediately ──
  G1 main menu
  G2 scenario select ← G1
  G3 quick battle UI ← G1
  G4 campaign UI ← G1
  G5 CLI update
  G6 difficulty select ← G1

Phase H (Animation) ── start after G1 ──
  H1 animation framework
  H2 movement animation ← H1
  H3 ranged fire effect ← H1
  H4 melee effect ← H1
  H5 damage numbers ← H1
  H6 cascade visual ← H1
  H7 playback speed ← H1
  H8 movement preview (no dep on H1; can start in parallel)
  H9 damage tooltip (no dep on H1; can start in parallel)

Phase I (AI) ── can start in parallel with H ──
  I1 enable MCTS
  I2 role behaviours ← I1
  I3 morale exploitation
  I4 adaptive difficulty
  I5 improved retreat
  I6 reserve triggers ← I2

Phase J (Content) ── can start in parallel ──
  J1 Ligny reinforcements
  J2 Möckern reinforcements
  J3 full_battle reinforcements
  J4 historical briefings ← G2 (display on scenario select)
  J5 supply wagons
  J6 difficulty ratings ← G2
  J7 messenger interception

Phase K (UI Polish) ── start after H done ──
  K1 log filtering
  K2 log click-to-pan
  K3 casualty table ← H (animation done, game-over screen richer)
  K4 score graph
  K5 elevation hillshade
  K6 terrain patterns
  K7 facing indicator
  K8 entrenchment visual
  K9 replay button
  K10 minimap pulse ← H1

Phase L (Quality) ── final phase ──
  L1 performance ← H, K
  L2 text scaling
  L3 README ← all above
  L4 CONTRIBUTING ← L3
  L5 test expansion ← all above
```

### Suggested build order

| Sprint | Focus | Tasks |
|--------|-------|-------|
| **S1** | Game entry + animation foundation | G1, G2, G5, G6, H1, H8, H9 |
| **S2** | Turn animations + quick battle | H2, H3, H4, H5, H7, G3, G4 |
| **S3** | AI upgrade + scenario content | I1, I2, I3, I5, J1, J2, J3, J5 |
| **S4** | Polish round 1 | H6, J4, J6, J7, K1, K2, K5, K6 |
| **S5** | Polish round 2 + quality | K3, K4, K7, K8, K9, K10, I4, I6 |
| **S6** | Ship prep | L1, L2, L3, L4, L5 |

---

## 5  Coding Standards (Unchanged)

- **PEP 8**, type hints throughout, `dataclass` for domain objects.
- **Layered architecture**: `core/` (headless logic) → `ai/` (decision-making) → `ui/` (rendering).
- **Composition over inheritance**; single-responsibility modules.
- **Pure functions** for combat math, LOS, scoring; dependency injection for RNG/AI policies.
- **No magic numbers** — constants in `config.py` or `data/` JSON files.
- **Testable headless** — all core + AI logic runnable without pygame.
- **Deterministic simulation** — seeded RNG for reproducibility and replay.
- **New UI code**: each major feature gets its own module (e.g., `ui/animation.py`,
  `ui/main_menu.py`, `ui/score_graph.py`). Keep `app.py` as a thin orchestrator.

---

## 6  Success Criteria

| Milestone | Criteria |
|-----------|----------|
| **Playable beta** | Main menu → scenario select → play with turn animations, movement preview, reinforcements arriving, AI using MCTS. ≥30 FPS on 60×45. |
| **Feature-complete** | All Phase G–K tasks done, campaign mode playable end-to-end, adaptive difficulty working, historical briefings in place. |
| **Release-quality** | ≥280 tests, performance verified, README with screenshots, CONTRIBUTING.md, text scaling option. |

---

## 7  What We're NOT Changing

These systems are solid and don't need rework:

- Core combat math, morale cascade, weather, facing/flanking
- Fog of war engine + visuals (atmospheric and well-cached)
- NATO unit counter rendering
- Map renderer caching architecture (3-layer system, 540× speedup already achieved)
- Order system + messenger delays
- Scenario editor (standalone, fully functional)
- Toast notification system
- Hotkey overlay, context menu, pause menu
- Test infrastructure (headless, deterministic)
