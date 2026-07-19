# Frozen Soldat — Agent Operating Instructions

> **You are working on a single-file HTML5 game (~35k lines) plus two companion docs.**
> This file tells you *how to behave* on any task. It is the standing operating manual, not
> architecture. The user will typically hand you three files and then just describe what they
> want. Your job is to do it well **and** keep the docs true.
>
> The three files:
> * `<game>.html` — the entire codebase (engine, rendering, AI, UI, audio — all inline). **The source of truth.**
> * `codebase_bootstrap_guide.md` — *intent*: architecture, patterns, choke points. Read for *why/how*.
> * `CODE_MAP.md` — *location*: ~600 grep-able anchors → what's there. Read for *where*.
>
> **Trust order when they disagree: code → map → guide.** The code is reality; the map was
> written reading the code; the guide is the oldest, most abstract layer. Drift is normal —
> flag it, fix it, keep moving.

---

## 1. The read protocol (do this before touching anything)

**Never ingest the whole `.html`.** It will bury your context and teach you nothing local
reading wouldn't. Instead:

1. Read this file (§1–§4).
2. Skim the guide's §0, §0.5, §1, §9. That's the architecture in ~2 minutes.
3. Open `CODE_MAP.md`; read **only** its cheat sheet + table of contents.
4. Translate the user's request into anchors. Grep each anchor in the `.html`
   (`grep -n 'anchor' <game>.html`) and read ~150–400 lines around each hit.
5. If an anchor doesn't match (the code moved since the map was built): grep a **shorter
   substring** of it, or a unique token from its description, or the parent class. Then
   **fix the stale anchor in `CODE_MAP.md`** as part of your change — you just found a drift.

Only read more of the file when the local read genuinely doesn't answer the question. Widen
deliberately, not by default.

---

## 2. Golden rules of this codebase (inherit from the guide, restated so you can't miss them)

* **Add content by adding a registry entry, not new imperative systems.** Weapons, bosses,
  perks, Armory upgrades, kits, missions, escalations, overclocks, prestige themes are all
  data-driven. Grep the registry (see the guide §1a / §3), add one entry, and the UI / buy
  logic / save / reset wire up "for free." `ARMORY_UPGRADES` is the exemplar — copy it.
* **Route every Intel reward through `RunLedger.addIntel(`.** Never write `saveData.intel`
  directly. The ledger owns eligibility and taint.
* **Reset run-scoped state in `startNewGame(`.** Miss it and state leaks across runs.
* **Migrate saves additively.** Add a new `{ to: N }` step to `SAVE_MIGRATIONS`; never edit
  an existing one. Add the new key to the default block too. (Head is v11.)
* **Match the existing pattern rather than inventing one.** Consistency beats cleverness here.
* **Only abstract what's earned** (hand-edited the same spot ~3+ times). Otherwise you're
  adding decoration and risk.

### Regression-sensitive zones — handle with tongs, re-read widely before editing

`dt` scaler (time dilation / Enraged / Adrenaline) · `takeDamage(` (single damage choke
point) · `addIntel(` (single Intel path) · gamepad dispatch (`pollGamepad` →
`handle*MenuNavigation`) · `draw()` early-returns in `start` state (no world canvas on the
menu — menu FX must be DOM/CSS) · `startNewGame(` (reset choke point) · the
`maxStamina !== undefined` "is-Player" discriminator (implicit contract; a new `Entity`
subclass defining `maxStamina` would silently inherit player logic).

---

## 3. The living-docs contract (the part that makes "just send three files" work)

**On every change, ask: does this alter something the map or guide describes?** If yes, update
that doc *in the same turn*, as part of the deliverable. This is not optional and not a
"you might also want to." A change that isn't reflected in the docs has silently made them
lie to the next reader.

Decision table:

| What you did | Update `CODE_MAP.md`? | Update the guide? |
| --- | --- | --- |
| Added a class / method / function / registry / screen | **Yes** — new anchor entry | Only if it's a new *pattern* or feature area (→ guide §9) |
| Renamed / moved something the map indexes | **Yes** — fix the anchor so it greps | No |
| Added a registry *entry* to an existing registry | Usually no (the registry entry already documents the pattern) — add one only if it's a headline system | No |
| Introduced a new choke point, tradeoff, or phase | Add anchor if there's new code | **Yes** — that's intent |
| Changed the save schema | Note in the map's migration summary | **Yes** — bump the head-version note in §8 |
| Pure bug fix, no signature/structure change | No | No |
| Fixed a stale anchor you found while reading | **Yes** — that *is* the update | No |

### How to apply and report doc updates

**If you have file-write access (the normal case — you're an agent that can edit files):**
1. Make the code change as **surgical, in-place edits** to the `.html`. Do **not** regenerate
   the whole file or dump 4k+ lines; edit only the relevant spans.
2. Make the corresponding **in-place edits** to `CODE_MAP.md` / the guide.
3. Then **report** everything you changed using the diff-report format below, so the user has
   a reviewable trail without opening the files.

**If you do *not* have file-write access (weaker tool, or user is pasting by hand):**
Emit the same diff-report as the *deliverable* — code blocks the user can paste in. Same
format, same content; the only difference is you're handing over patches instead of applying
them.

### Diff-report format (use this every time docs or code change)

```
## Changes

### Code (<game>.html)
- <anchor or location>: <one line on what changed and why>
- ...

### CODE_MAP.md
- ADD under section "<section name>", after `<preceding anchor>`:
    ### `<new literal anchor — must appear verbatim in the .html>`
    - What: <one line>
    - Does: <one line>
    - Refs: <called/related anchors, if obvious>
- EDIT anchor `<old>` → `<new>` (renamed/moved)
- (no change) — if nothing in the map is affected, say so explicitly

### codebase_bootstrap_guide.md
- <section>: <what you added/changed>, or "(no change)"
```

Rules for map entries you write:
* The anchor **must be a string that literally appears in your new code.** Prefer a class
  signature, method definition, `const NAME = {`, or a distinctive comment. Verify it greps.
* One-line *What*, one-line *Does*. Terse beats detailed — the map is an index, not a spec.
* Never put line numbers in the map or the guide.
* Append/patch only; don't reorganize the whole map to insert one entry.

---

## 4. Task-type playbooks

The read protocol (§1) and living-docs contract (§3) apply to **all** of these. The
differences are in emphasis.

**Add a subsystem / feature.** First question: *is there a registry for this category?* If
yes, add an entry — that's usually the whole job. If no, and you're about to write a big
`if/else` that mirrors an existing registry, that's the smell the thing wants to be
data-driven (see guide §6, the shop). Match the nearest existing sibling's shape. New code →
new map anchor. New pattern/feature area → guide §9 line.

**Bug fix.** Reproduce via the anchor, read locally, make the smallest change that fixes it.
Prefer fixing at the choke point over scattering patches. If the fix touches a tongs zone,
say so in your report and re-validate. Usually **no doc change** — unless you renamed
something or the map's description was itself wrong (then fix the map).

**Optimization pass.** Measure/reason about the hot path first (game loop, `update`, `draw`,
collision, pathfinding, audio voice pool). Preserve behavior — optimizations must be
observationally identical. Watch the `dt` scaler and pooling code especially. Doc change only
if you moved/renamed things.

**Refactor / code-health review.** Apply the guide's meta-guidance ruthlessly: **only refactor
what silently fails (the `maxStamina` discriminator) or gets repeatedly hand-edited (the shop
button wall).** Leave merely-verbose-but-clear code alone (§5 of the guide). If you touch the
shop or the discriminator, it's a big regression surface — test the golden path (buy every
item pre/post, or spawn every entity type) and report it. Refactors that rename things →
**update every affected map anchor**; that's the bulk of the doc work.

**Deep dive / "explain how X works".** Pure reading task. Answer from the code, cite anchors
so the user can follow. If you discover the map or guide is *wrong or missing* something
important during the dive, offer the correction as a diff-report even though the user didn't
ask for a code change — a dive that finds drift should fix it.

**Save-schema change.** Additive only: new `{ to: N }` step, new default in the default
block, never edit an old step. Update guide §8 head-version note and the map's migration
summary.

---

## 5. Before you finish — the checklist

- [ ] Code change is surgical and matches the nearest existing pattern.
- [ ] If JS changed: it would pass `node --check` on the extracted `<script>` (no stray brace).
- [ ] Tongs zones touched? Called out in the report + reasoned about regression.
- [ ] Every reward path goes through `addIntel`; every run-scoped add is reset in `startNewGame`.
- [ ] Docs updated per the §3 table, applied in-place (or emitted as patches if no write access).
- [ ] Every new/edited map anchor is a string that **literally appears** in the `.html`.
- [ ] Diff-report included so the user can review without opening files.
- [ ] No line numbers introduced into either doc.

---

## 6. Keeping the map honest (verification)

`CODE_MAP.md` is only trustworthy if its anchors still grep. After a batch of changes — or any
time you suspect drift — run the verification script (`verify_code_map.py`, shipped alongside
these docs; also reproduced in the map's own appendix). It prints any anchor that no longer
matches the `.html`. Zero broken = the map is sound. Nonzero = the code moved under those
anchors; relocate each (grep a shorter substring) and fix its entry.

If you can run a shell, run it and report the count. If you can't, spot-check your *own* new
anchors by confirming each appears verbatim in the file you just edited — that's where fresh
breakage comes from.

> **One-liner for the user to paste after any session:**
> `python3 verify_code_map.py <game>.html CODE_MAP.md`
