# Frozen Soldat — Codebase Bootstrap & Architecture Guide

> **Purpose.** This is the orientation doc for anyone (human or AI) picking up the game's single HTML file cold. Read it *first* so you touch the right ~400 lines instead of grepping blind through 35k. It's a **map of intent** — how this code thinks and where the load-bearing patterns live — not a line-by-line spec. Its companion, **`CODE_MAP.md`**, is the *location* index (grep-able anchors → what's there). Use them together: this guide for *why/how*, the map for *where*. See §0.5.
>
> **Status.** Current as of Phase D (Prestige) plus later save-schema additions (migration head **v11** — see §8). The game is a single-file, ~35k-line, vanilla-JS + HTML5 Canvas top-down shooter. Zero external assets: every sprite, sound, and UI element is drawn/synthesized at runtime. (The main file has been referred to over time as `LATEST_MASTER.html` / `index.html`; treat whichever single large `.html` file you're handed as the codebase.)
>
> **Golden rule of this codebase:** *Abstractions are earned, not preemptive.* Registries appeared where things were genuinely being added repeatedly. Follow that discipline — only introduce a new abstraction once you've hand-edited the same spot ~3 times. If a change doesn't make a **future concrete edit cheaper**, it's decoration.

---

## 0. How to work in this file (read this even if you skip the rest)

1. **Don't ingest the whole file.** It's ~30k lines. Grep for the registry or method you need, read that plus its neighbors, and trust the choke points below.
2. **Adding content = adding a registry entry**, not writing new systems. Menus, shops, kits, missions, bosses, and Armory upgrades are all data-driven. See §3.
3. **Respect the regression-sensitive zones (§7).** A few choke points ripple across the whole game. Handle them with tongs.
4. **Match the existing pattern rather than inventing one.** If you're adding a gated shop item, copy how the last gated item was done. If you're adding a menu row, copy the last menu row. Consistency here is worth more than cleverness.
5. **Every JS edit: re-validate.** Extract the main `<script>` block and `node --check` it before shipping. Cheap insurance against a stray brace in a monolith.

---

## 0.5. This guide + `CODE_MAP.md` (read this to orient in ~2 minutes)

You are typically handed **three files**: this guide, `CODE_MAP.md`, and the game `.html`.
They divide labor:

* **This guide = intent.** Architecture, patterns, choke points, "how the code thinks." Stable; changes rarely. Read the sections relevant to your task in full.
* **`CODE_MAP.md` = location.** A grep index: ~600 entries, each a **literal anchor string** that appears in the file, with a one-line "what/does." It tells you *where* a system physically lives. Every anchor was verified grep-able when the map was built.
* **The `.html` = truth.** When guide, map, and code disagree, the order of trust is **code → map → guide** (the code is reality; the map was written reading the code; the guide is the oldest and most abstract). Known drift is fine and expected — flag it, don't be paralyzed by it.

**How much to read up front.** Don't ingest the `.html`. Do this instead:
1. Skim this guide's §0, §0.5, §1, and §9 (feature-area quick reference) — that's the lay of the land.
2. Open `CODE_MAP.md`, read its **cheat sheet** and **table of contents** only.
3. From your task, pick the anchor(s) you need, `grep -n 'anchor' <file>.html`, and read ~150–400 lines locally.

That's the whole loop. You should be editing the right ~300 lines within a couple of minutes, never having loaded the monolith whole.

### The living-docs contract (important — do this on every change)

These docs only stay useful if they move with the code. **Whenever you change the code, ask: does this change something the guide or the map describes?** If yes, update that doc *in the same response*, as part of the deliverable — never as a "you might also want to…" afterthought.

* **Added a system / registry entry / method / screen?** Add a `CODE_MAP.md` entry: a backtick anchor that **literally appears** in your new code, a one-line *What*, a one-line *Does*, and *Refs* where obvious. Place it in the section that matches its architecture.
* **Renamed or moved something the map already indexes?** Update that anchor so it still greps.
* **Introduced a new pattern, choke point, tradeoff, or phase?** That's *intent* — update **this guide** (the relevant section, or §9 if it's a new feature area), not just the map.
* **Changed the save schema?** Bump the migration head note in §8 and add the map's migration summary.
* **Don't silently regenerate whole files.** Prefer surgical, in-place edits and then *report what you changed* (see `AGENT_INSTRUCTIONS.md` for the exact diff-report format). Rewriting the entire 4k-line map every time invites drift and truncation; touch only what changed.

If you're not sure whether something belongs in a doc, the test is the same as the golden rule: **would recording it make a future edit cheaper or safer?** If yes, record it. If it's just noise, leave it.

> Operational specifics — read order per task type, the diff-report format, the anchor-verification script, and how to behave with vs. without file-write access — live in **`AGENT_INSTRUCTIONS.md`**. This guide stays focused on architecture.

---

## 1. Architectural Philosophy: Composition, Registries, and Parameter Scaling

The reason this file stays navigable at its size comes down to a few disciplines:

### 1a. Data-driven registries (the real MVP)
Core content lives in plain arrays/objects that the UI, purchase logic, save system, and reset logic all read from **one** source. Adding a thing = one entry, and everything downstream wires up "for free."

Registries you'll actually touch:
* `Weapons` — weapon stat blocks (dmg, fireRate, ammoKey, color…).
* `BossTypes` — boss registry; adding an entry auto-populates the Dev Dashboard spawner.
* `PERK_DEFS` — perk-case / Chaos-Draft perk pool.
* `ARMORY_UPGRADES` — **the exemplar.** Render, buy, refund, reset, *and* Phase-B shop-gating + Phase-D prestige-max-check all iterate this one array. Adding a meta-upgrade is a single entry.
* `OPERATOR_KITS` / `KIT_ORDER` / `KIT_SHOP_REBATE` — operator kits (loadout, passive, shop rebate).
* `MISSIONS` / `MISSION_ORDER` — extraction missions (+ mission modifiers).
* `ESCALATION_PROTOCOLS` / `ESCALATION_ORDER` — opt-in extraction risk toggles.
* `CORRUPTED_OVERCLOCKS` — cursed overclocks with trade-offs.
* `PRESTIGE_THEMES` — (Phase D) 10 menu color themes + badge accents, indexed by prestige level.

**Litmus test before you write imperative code:** "Is there already a registry for this category?" If yes, add an entry. If you're about to write a big `if/else` chain that mirrors an existing registry, that's the smell that the *thing you're editing* wants to become data-driven too (see §6, the shop).

### 1b. Multiplicative modifier chaining
Combat params are computed at the moment of action, not stored on rigid sheets. Bullet damage ≈ `base × difficulty × hollowPoint × cursedOC × pointBlank × sprint`. A new upgrade injects one multiplier at spawn-time; weapon/bullet classes don't change.

### 1c. Temporal manipulation via `dt` scaling
Whole-entity speedups (e.g. the **Enraged** boss trait at <50% HP) are done by scaling the `dt` handed to `entity.update()`, *not* by touching internal logic. Because movement, animation, reload, and cooldowns are all `dt`-derived, scaling `dt` accelerates everything uniformly with no desync. **This is a regression-sensitive lever — see §7.**

### 1d. Shared-property discriminators (the known wart — see §5)
Base-class loops identify the player via a property only `Player` has: `if (this.maxStamina !== undefined)`. Cheap, avoids `instanceof`, but it's an *implicit contract*. Flagged in §5 as the one latent bug.

---

## 2. Layout & High-Level Components

* **Single file:** `LATEST_MASTER.html` — engine, rendering, AI, A* pathfinding, UI, audio synthesis, all inline.
* **Canvas 2D** (`this.ctx`) with camera scaling, viewport culling, composite lighting. `draw()` **early-returns in the `start` state** — the world is NOT rendered on the main menu (important for menu-time effects; see §7).
* **DOM/CSS overlays** for all menus (main menu, shop, Chaos Draft + Black Market, Armory, HUD, dev dashboard, prestige FX). Cyber-neon theme driven by CSS custom props (`--neon-blue`, `--neon-green`, `--dark-bg`, …) at the top of `<style>`.
* **Audio:** `const audio = new AudioEngine()` — everything synthesized (Web Audio). Useful hooks: `audio.playPickup('money'|'weapon')`, `audio.playExplosion(vol,x,y)`, `audio.playTadah()`, `audio.playBakedSound(...)`.
* **DOM utils:** `toggleClass(id, class, force)`, `setHtml(id, html)`.

---

## 3. Entity Hierarchy & Physics

```
Entity
 ├─ Player        (hp, armor, stamina, inventory, ammo, perks, overclocks)
 ├─ Enemy         (steering, patrol, target selection)
 │   └─ Boss      (state machines, sub-parts, difficulty modifiers)
 ├─ Bullet
 ├─ FPVDrone / BossDrone / EnemyFragGrenade  (specialized actors)
 └─ (particles, items handled via pools)
```

* `Entity` — position/velocity/radius, `updatePhysics(dt, walls)`, circle-vs-circle / circle-vs-AABB collision.
* `Player` — health/armor/stamina, `inventory`, `ammo`/`maxAmmo`, perks, `runOverclocks` slot (`p1`/`p2`). Aim is **intent → weighted actual angle** (`updateAimWeight`), not direct assignment.
* `Enemy`/`Boss` — steering + patrol; bosses override with state machines and per-run trait modifiers (Chaos Draft mutations).

Class anchors (grep): `class Entity` `class Player` `class Enemy` `class Boss` `class Bullet` `class FPVDrone` `class RunLedger` `class Game`.

---

## 4. The Game object & run pipeline

`class Game` is the god-object (see §5). Key run-lifecycle methods:

* `buildRunConfig()` — snapshots the rules of a run into an immutable-ish `RunConfig` (mode, modifiers, mission, escalations, kits, reward rules). **Resolve-at-snapshot pattern:** decisions are made once here, then downstream code reads plain data. Mirror this for anything run-scoped.
* `startNewGame()` — the big reset. All run-scoped state is (re)initialized here. **If you add run-scoped state, reset it here** or it leaks across runs (e.g. `chaosDraftState`, `runOverclocks`).
* `RunLedger` — **the single write path for in-run stats + Intel.** Never write `saveData.intel` directly for rewards; call `ledger.addIntel(amount, source)`. It handles eligibility (sandbox/god/tainted runs earn 0) and crash-safe persistence. **Regression-sensitive — §7.**
* `openShopInterface()` — inter-wave shop; also the branch point for Chaos Draft (skips shop, runs the draft). Long imperative button-config block (see §6).
* `loadGameData()` / `saveGameData()` + `SAVE_MIGRATIONS` — see §8.

---

## 5. Known pain points (honest, deliberate tradeoffs)

These are *documented choices*, not accidents. None currently block feature work; listed so you don't "discover" them and so you know the disarm path if one ever bites.

1. **`maxStamina !== undefined` as the "is this the Player" check.** Clever, cheap, but an implicit contract: a future `Entity` subclass that happens to define `maxStamina` would silently inherit player-only logic. **Latent bug, not active.** *Disarm path (cheap, additive, ~1 hr if ever needed):* add an explicit `this.isPlayer = true` in the `Player` constructor, batch-replace the checks, retire the old test last. Do this only if you add a colliding subclass — you control that.
2. **`openShopInterface` button-config wall.** ~300 lines of imperative `if (btn) {...}` per shop item. It's readable but it's the one place "just add an entry" breaks down — Phase B's gating needed nine hand-touched blocks. *This is the #1 refactor candidate IF it ever earns it* (see §6).
3. **State spread across `Game` / `player` / `saveData` + repeated co-op `p1/p2` branching.** Verbose but legible. **Do NOT crusade on this** — full state decomposition is high-risk, low-payoff for how this code gets worked on. If it ever annoys you, absorb it *opportunistically* with a `forEachActivePlayer(fn)` helper as you pass through, never as a dedicated pass.

**Meta-guidance:** Refactor things that cause *silent failures* (#1) or *repeated hand-editing* (#2). Leave things that are merely verbose-but-clear (#3). The refactor risk must be less than the ongoing cost, or it's not worth it.

---

## 6. The shop, and the one refactor worth knowing about

The Armory (`ARMORY_UPGRADES`) is fully data-driven; the inter-wave shop is not — it's the imperative wall in `openShopInterface`. That asymmetry is the tell.

**If** a future feature makes you hand-edit shop items ~3+ times (e.g. several new gating dimensions), the earned move is to make the shop a `SHOP_ITEMS` registry mirroring `ARMORY_UPGRADES`: each entry declares `{ id, cost, category, maxCheck(p), label(p), unlockKey?, apply(p) }`, consumed by one render loop and one buy dispatch. That collapses the wall, makes gating a one-field change, and erases a chunk of the co-op duplication.

**Until that trigger fires, leave it.** The pattern is already proven by the Armory, so this is *propagating* an existing success, not inventing architecture — which is exactly why it's low-conceptual-risk when the time comes. It still needs golden-path testing (buy every item pre/post, diff the effects) because the regression surface is "every purchasable behaves identically."

---

## 7. Regression-sensitive zones (handle with tongs)

Before editing anything near these, know that changes ripple:

* **The `dt` scaler** (time dilation / Enraged trait / Adrenaline). Everything time-based keys off `dt`; scaling it touches physics, animation, cooldowns, reload — all at once. Great for uniform speed changes, dangerous for anything assuming real-time.
* **`Entity.takeDamage()`** — the single damage choke point. The player-damage hook here drives the RunLedger, objective interrupts, clean-wave tracking, and (Phase A) the Blood Wager fail. Adding damage-reactive behavior goes here, but it's crowded.
* **`RunLedger.addIntel()`** — the single Intel write path. Route *all* rewards through it (honors eligibility/taint). Never poke `saveData.intel` directly for a reward.
* **The gamepad dispatch** (`pollGamepad` / `handle*MenuNavigation`) — one dispatcher fans out to per-screen handlers, gated by state flags and `dpadCooldown`. New overlays need a handler *and* a dispatch entry, and must respect the cooldown/`focused-btn` conventions. Sub-modal overlays (Chaos Draft) are checked *before* the pause/state branches.
* **`draw()` early-returns in `start` state** — the world canvas isn't live on the menu. Menu-time visual effects must be DOM/CSS (see Phase D prestige FX), not world-space particles.
* **`startNewGame()`** — miss a reset here and state leaks across runs.
* **The per-wall draw loop in `MapGen.draw()`** — hot path, with a real perf history (per-wall `shadowBlur` gating, cached lineage shadows, batched cross-hatch). It sets `fillStyle` once *outside* itself deliberately. The wall-depth passes (§9) bracket it rather than touch it — any future per-wall visual change should follow that pattern, not add per-wall state back into the loop.
* **`MathUtils.viewSeesPoint`** — the single predicate behind enemy visibility/opacity, and the intended reuse point for Tasks 6–7. Its three-case structure is load-bearing: the aim gate must stay unreachable when no `seeThrough` wall is on the segment, or non-window visibility silently regresses. Change it with a test, not by eye.
* **`GEN_VERSION`** — bump it when an *existing* template's wall output changes (new stamp added to a role, a hand-authored `case N` gains/loses geometry), not just for new templates. A new template id never needs a bump (old challenge links can't reference an id that didn't exist). Currently **4** — see §9's Simulated Second Floor entry for what the last bump covered.

---

## 8. Save data & migration discipline (strict)

* `saveData` persists to `localStorage`. Schema is versioned via `SAVE_MIGRATIONS`, an ordered array of `{ to, up(sd) }` steps run in sequence.
* **Rule: additive only. Add a new `{ to: N }` step; NEVER edit an existing one.** Each step defaults new keys; unknown/legacy fields survive the JSON round-trip untouched. The whole pass is guarded — a save that still explodes resets to factory rather than hard-crashing the menu.
* There's also a belt-and-suspenders default block after the migrations (mirrors the latest keys with `=== undefined` guards). Add your new default there too.
* Current head: **v14**. Recent steps: **v14** (`customMaps` — Task 10 saved-map snapshots), v13 (`manipulatorPaint` / `wallColor` / `touchStickScale`), v12 (`unlockBarrierEngineer`), v11 (`greedyHands` / `armoryTutorial` / `touchFireHint`), v9–v10 (`debugStartWave`), v8 (Phase D — `prestigeLevel`), v7 (shop-unlock keys), v6 (operator paint), v5 (kits/presets), v4 (escalations/mags/attachments), v3 (missions), v2 (careerStats). Grep `const SAVE_MIGRATIONS = [` for the authoritative list; the code is the source of truth if this note drifts (it has: this file long said v11/v8 while the code marched on).

---

## 9. Feature-area quick reference (where things live)

* **Chaos Draft + Black Market (Phase A):** `openChaosDraftInterface` → `_advanceChaosDraftQueue` → `_renderChaosDraftForPlayer` (cards) + `_renderBlackMarket` (gold sinks). State in `this.chaosDraftState` (reset in `startNewGame`). Gamepad: `handleChaosDraftMenuNavigation` (2-row nav, `chaosDraftRowIndex`). Blood Wager fail-hook lives in `Entity.takeDamage`; resolution in the wave-clear branch of `openShopInterface`.
* **Armory shop gating (Phase B):** `ARMORY_UPGRADES` unlock keys + `_armoryGate(btn, key, minLevel, label)` helper inside `openShopInterface`, plus silent guards in `buyItem`/`buyOverclock`. **Operator mode is exempt** from gating by design.
* **In-game Guide (Phase C):** static HTML in `#tab-guide`. Scroll-only under gamepad (`guide: []` nav row).
* **Prestige (Phase D):** `isArmoryMaxed()` (gate), `renderPrestigeButton()` (in `renderArmoryTab`), `doPrestige()` (action), `prestigeCelebration()` (DOM/CSS FX + audio reuse), `applyPrestigeCosmetics()` (`--dark-bg` + badge, called at load + after prestige), `_buildPrestigeBadgeSVG()`, `devResetPrestige()` (dev tool). Palette: `PRESTIGE_THEMES`.
* **Main-menu gamepad nav:** `getMainMenuTabRows()` defines the nav grid per tab as arrays of element-id rows; `handleMainMenuNavigation` + `refreshMainMenuHighlight` consume it. Div-based chips (kits, escalations, missions) need `.mission-card.focused-btn` styling and inclusion in the clear-query.
* **Modes:** `normal`, `now` (Action Now / horde — `NOW_MODE`), `operator` (FPV bunker — `OP_TUNING`), `chaos_draft`, `extraction`, `sandbox`. Mode flags on `Game` (`chaosDraftMode`, `operatorMode`, `nowMode`, `extractionMode`, `isTestingMode`).
* **Custom Maps (Task 10 — save a built/exploded map, then SELECT it like any built-in map):** a saved map is base identity (`mapId`+`mapSeed`+`genVersion`, the *same* determinism a challenge link uses) plus a raw snapshot of the **mutable wall layer** — every non-skeleton wall (base destructible walls in their current carved/exploded state + player-built walls) as compact geometry with palette-compressed colors. `saveCurrentMapAsCustom()` (pause-menu `btn-pause-savemap`) snapshots via `_snapshotCustomWallLayer()` and auto-names via `_makeCustomMapName()`. **Selection, not immediate load:** clicking a saved map calls `selectCustomMap()`, which *stages* it (`setMap(mapId)` for the base template + `pendingMapSeed`/`_pendingCustomMap` for the forced seed + wall payload) exactly like picking a built-in map, then routes to the run wizard's MODE step. The player then chooses mode/roster/options freely and deploys — so a map built solo-peaceful can be replayed 2P Action Now, Chaos Draft, whatever. `startNewGame()` consumes the staging **regardless of mode**: after players/kit setup (so the spawn-nudge sees real players) and before barrels/objectives place, `_injectCustomWalls()` **strips the freshly-regenerated pristine base's destructible layer and stamps the snapshot back down** as fresh full-health walls (hp recomputed from `_destructibleHpFor` — the anti-zombie invariant — re-filed via `_insertWallIntoGrid`; player walls → `_playerWalls`; nav rebuilt; spawn-stuck players nudged via Task 2's `_findSafeSpawnNear`). Staging is cleared by `setMap()` when a *different* map is picked and by `applyChallengeLink()` when a challenge is armed (they're alternative map sources); `buildRunConfig()` falls back to the staged seed if `pendingMapSeed` was cleared. **Snapshot semantics by design:** no forward damage persistence — a reload is a clean starting point, so full-health-on-load is correct, *and* because geometry is stored explicitly a future `GEN_VERSION` bump can't corrupt a saved fort (blocks reload exact; only the untouched backdrop may shift, surfaced as a soft note). UI: a collapsible `CUSTOM MAPS` drop-down (`btn-custom-maps-toggle` / `custom-maps-list`, rendered by `renderCustomMapsList()`, staged row shown with `active-mode`+✓) pinned to the top of the Maps tab; `getMainMenuTabRows().maps` prepends its nav rows dynamically. Save schema: v14 `customMaps` (capped at 20, oldest dropped).
* **Matter Manipulator (context-sensitive F: mine ↔ build):** tuning in `const MATTER_MANIPULATOR`. The existing F-drill block in `Player.update` gained a harvest (banks the exact `wall.hp` delta from `damageWallPoint` into `player.wallMaterial`) and a build branch (grows `buildTargetSide` after `ARM_DELAY`). Commit/preview/validation are `Game.placePlayerWall` / `computeWallBuildFootprint` / `_wallBuildValid` / `drawWallBuildPreview`. **Load-bearing invariant:** a built wall is priced with `_destructibleHpFor(side,side,'crumbling')` and set to full health (`hp===maxHp===cost`) so the lazily-built damage-cell grid can't disagree with `wall.hp` — an arbitrary hp would leave an un-carvable "zombie" wall. Built walls are real `map.walls` entries (path/LOS/carve for free), soft-capped via `MapGen._playerWalls`. Bank is run-scoped (resets because `Player` is reconstructed in `startNewGame`). Note this reuses the drill choke and touches `damageWallPoint` — a §7 tongs zone.
* **Simulated Second Floor (raised platforms / "mesas"):** elevation is a pure function of *position*, not entity state — `MapGen.floorAt(x,y)` / `floorSeparated(...)` are the whole model, and no entity carries a z/floor field. A platform is a walkable region (`MapGen.platforms`) whose footprint is unreachable except through its stair regions; because the two elevations never overlap in walkable space, every existing system (items, corpses, turrets, player-built walls) gets correct elevation for free from its own `x`/`y`. **Placement:** procedural maps get a platform via `MAP_STAMPS.platform_keep/bastion/tower` (built by the shared `buildKeep()` factory) listed in a `PROCGEN_RULES` role's `stamps`; hand-authored templates call `MapGen.addPlatform(x, y, w, h, opts)` directly (`opts.stairSides`/`windowSides` pin down what procgen would otherwise roll — this is what makes 2-Fort's mirrored RED/BLU battlements reproducible). Both paths converge on one placer, `_placeStampDef` (`_placeStamp` is now a thin lookup wrapper over it). **Combat rules, one line each:** `Game.blastOccluded` gates all explosion sites on `floorSeparated` (grenades don't cross floors); the window bullet rule lives in `Bullet.update`'s wall-collision branch next to the existing `perkGhost` check (outbound-from-deck always clears, inbound rolls `SECOND_FLOOR.WINDOW_UP_PASS`); loot magnetism and the collect-touch test in `Item.update` / the pickup loop both floor-guard. **Visibility vs. combat LOS are deliberately split:** `MathUtils.lineBlocksSight` (window-transparent) drives the enemy-opacity/fade system only; combat targeting (turrets, dogs, enemy aim) still uses plain `lineIntersectAABB` and is opaque at windows — turrets/dogs go blind on a deck by design (phase-1 tradeoff, flagged as a follow-up candidate). **Rendering** is the 2.5D language the rest of the wall/floor depth pass (below) now shares: `MapGen.drawPlatformBase` (shadow/ramp/cliff/deck, runs between the floor and wall passes) and `drawPlatformParapets(..., sills)` (windows drawn *below* entities so aiming reads as over-the-sill, not under-the-wall; solid parapets drawn *above*). Per-platform palettes in `SECOND_FLOOR.PALETTES` (`id: 'blu'/'red'` reserved for 2-Fort). **Nav grid:** stairs are sized (220px) to guarantee connectivity on the fixed 100px lattice, and `_linkPlatformStairs()` (runs once after `buildNavGrid()`) repairs the rare cases where the lattice fell badly against a hand-placed platform — this exists because it was a *real*, seed-reproducible failure on the classic maps, not preemptive. `_clearPlatformSurrounds()` strips any wall that drifted into a keep or its ramps (runs before `_procgenValidate` in both assemblers, and once more after `generate()` for authored maps). `addPlatform` refuses to place over another platform rather than silently corrupting geometry. **`GEN_VERSION` is 4** — existing templates changed wall output when platforms were added to them.
* **Wall/floor depth pass (2.5D lighting):** applies the platform 2.5D language — dark extruded body, LIT top face, rim catch-light, cast shadow — to ordinary ground walls and the floor, so the whole world reads as one coherent depth hierarchy (`WALL_DEPTH` constants: window 9px → wall 13px → cliff 20px → parapet 26px). **The lit cap is the entire effect** — a dark side face on a near-black wall changes nothing; contrast only exists once the top face is bright. Two new batched passes bracket the existing per-wall loop *without modifying it* (that loop is hot path with a real perf history — per-wall `shadowBlur` gating, cached lineage shadows): `_drawWallDepth` (side faces, before the loop) and `_drawWallCaps`+`_drawWallRims` (lit tops + rim, after it). Cap tinting reuses/extends the loop's own `_diagRgbGroups` colour-batching via the new `_wallRgb()`/`_ensureWallRgbGroups()` helpers (also deduplicates the `splitTheme` branch that used to be copy-pasted three times). Floor: `MapGen.backdropColor()` is the single source of truth for the ground fill colour (biome-tinted, was a hardcoded `#01050e` duplicated in two places that had to be kept in sync by comment — now both read the method), plus a cached, viewport-keyed radial vignette in `draw()`.

---

## §9.5 Mesa polish pass (Tasks 1–5 landed; 6–7 still open)

The follow-ups filed here after the platform/depth-pass work shipped have now been worked. Kept as a record of *what the fix was and why*, because several of them were one root cause wearing two hats.

**Landed:**

* **Barrier draw order (Task 1).** Barriers still draw before `map.draw()` so wall geometry occludes their embedded ends — but that pass is now split by elevation via `Game.drawBarriers(cam, deckOnly)`, mirroring the `deckOnly` convention `drawPermanentMarks` already established for gore. Ground barriers are unchanged (being occluded by the platform's mass is correct for them); deck barriers are re-drawn after `drawPlatformBase`, between the deck-gore pass and the sill pass. Wired into all three viewports (main, drone PiP, operator base cam).
* **Enemy window fire (Task 2).** Diagnosis confirmed: `Bullet.update`'s roll was already symmetric; the failure was upstream in the AI never deciding it had a shot. Fixed with a *separate* `cachedWindowLOS` flag rather than by relaxing `hasLOS` — `hasLOS` stays opaque at windows because it is load-bearing for movement, target selection, detection and mortars, and that opacity is what keeps enemies routing to the stairs. `cachedWindowLOS` is true only when combat LOS is blocked, sight-class LOS is clear (so the only blockers were windows), *and* the two points are `floorSeparated`. It is consumed by the direct-fire gate and nothing else. Because firing along the pathfinding angle would spray sideways, facing was split out into `cachedAimAngle` — identical to `cachedMoveAngle` in every case but this one, so steering is untouched and the read is "suppressing fire on the way to the stairs," not a new camping behaviour. Tuning: `SECOND_FLOOR.ENEMY_WINDOW_FIRE_MULT`.
* **Gun/laser at windows (Task 3).** Both reports were the same raycast. `Game.getLaserEndPoint` now skips `seeThrough` walls. It is a *sight-class* raycast (all three consumers — laser beam, Spot Robot beam, gun-retraction reach-check in `Player.update` — are visual reads of where the gun points), so it follows `lineBlocksSight`'s precedent rather than `lineIntersectAABB`'s. Pass-through odds are untouched: the gun reaches over the sill, the round may still clip it.
* **Aim-gated window visibility (Task 4).** `MathUtils.lineBlocksSight` is retained as the shared primitive, but the enemy-opacity system now consumes `MathUtils.viewSeesPoint(view, tx, ty, walls)`, which resolves three cases: solid wall on the segment → not visible (unchanged); nothing on the segment → visible (unchanged); *only* window segments on the segment → visible **only if the viewer is aimed within `SECOND_FLOOR.WINDOW_VIEW_CONE`**. Cases 1 and 2 are unchanged by construction — if no `seeThrough` wall lies on the segment the aim test is never reached — which is what protects the stair-gap / same-deck / plain-2D visibility that must not regress. Verified against the old predicate on 20k randomized non-window segments (exact match) plus the case table. All 11 previously-inlined call sites in `Enemy.update` (5 sniper + 5 local + the close-range pop-in fast path) now route through it; the fast path **must** keep using the same predicate or it hands the passive reveal back inside 340px.
* **Floor vignette (Task 5).** Root cause as diagnosed, with one wrinkle worth recording: this pass *can't* just adopt the sibling `visibleW = viewportW / cam.zoom` convention, because a canvas gradient is baked in the units it was created in — building it at `visibleW` would rebuild it every frame the zoom spring moves. It stays cached in stable screen pixels and undoes the zoom locally with a **relative** `ctx.scale(1/cam.zoom, ...)`. Relative, not `setTransform(identity)`: identity would drop the P2 half-screen translate and the screen-shake offset.

**Still open — see `docs/mesa_polish_tasks_6_7_design.md`:** Task 6 (threat occlusion) and Task 7 (fog of war). These are *not* independent: both want a per-frame "is this cell visible to any player-aligned viewpoint" answer, and doing 6 naively (a raycast per bullet per viewpoint per frame) is roughly 30× the per-frame cost of the enemy visibility system, which pays the same price on a 30-frame stagger. They should share one memoized mechanism and get a measured pass together.

---

## 10. Dev terminal

10 rapid clicks on the "FROZEN SOLDAT" title unlocks it; `~`/`F1` opens the Dev Dashboard in a match (god mode, spawners from `BossTypes`, cash/intel, forced mutators, prestige reset). Dev-tainting a run flips the RunLedger to earn 0 Intel — intentional and irreversible for that run.

---

## 11. TL;DR for a fresh context

* Single ~35k-line file; **don't** read it whole. Use `CODE_MAP.md`'s cheat sheet to find the anchor, grep it, read locally.
* **Add content by adding a registry entry.** The Armory (`ARMORY_UPGRADES`) is the exemplar of the pattern.
* **Route rewards through `RunLedger.addIntel`; reset run state in `startNewGame`; migrate saves additively (v11 is head).**
* **Tongs zones:** `dt` scaler, `takeDamage`, `addIntel`, gamepad dispatch, `draw()`-skips-on-menu, `startNewGame`, the per-wall draw loop in `MapGen.draw()`, `viewSeesPoint`, `GEN_VERSION`.
* **Update the docs with the code.** Every change that adds/renames/moves a system → update `CODE_MAP.md`; every change to intent/patterns/phases → update this guide. See §0.5 and `AGENT_INSTRUCTIONS.md`.
* **Architecture is not the bottleneck.** Only refactor what's silently-failing (the discriminator) or repeatedly-hand-edited (the shop) — and only once it's actually earned. Everything else: leave it, and enjoy how cheap the next feature is.
