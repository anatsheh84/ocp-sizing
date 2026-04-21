# `html_reporter.py` Refactor Plan

**Status:** Planning (not started)
**Created:** April 2026
**Owner:** Ziko

## Purpose

Break `reporters/html_reporter.py` (currently 3,001 lines, one giant f-string) into
a set of focused modules so that:

- Each report tab lives in its own file and can be edited in isolation
- CSS and JS are ordinary strings (no `{{` / `}}` f-string escape noise)
- Adding a new tab is one new file + one line in an orchestrator
- The fragility around f-string emoji parsing (the reason we're pinned to
  `python:3.12-slim`) is mostly neutralized
- Data shaping is testable without touching HTML

**Non-goals for this refactor:**
- No change to rendered output (visually/functionally identical HTML)
- No new dependencies (no Jinja2, no template engine)
- No UI/UX changes, no new features, no backlog items
- No changes to the data models in `models/` or the parsers/analyzers

## Target end-state architecture

```
reporters/
  html_reporter.py          # Thin orchestrator, ~80-100 lines
  report_context.py         # ReportContext dataclass + builders
  layout.py                 # Outer shell (DOCTYPE, header, nav, footer)
  styles.py                 # CSS as a string constant
  scripts.py                # JS as a string constant + data prelude builder
  components.py             # Shared: filter_bar(), no_data(), sum_row_tfoot(), etc.
  tabs/
    __init__.py
    overview.py
    nodes.py
    efficiency.py
    workloads.py
    workload_inventory.py   # move existing _generate_workload_inventory_tab here
    recommendations.py
    checklist.py
    storage.py
  pdf_exporter.py           # unchanged
```


## Cross-cutting conventions

### Branch naming
One feature branch per phase:
- `refactor/html-reporter-phase-1-styles`
- `refactor/html-reporter-phase-2-scripts`
- …etc.

Standard flow: `git checkout -b refactor/...` → develop → commit → merge to `main` →
`git push origin main` → `git branch -d refactor/...`

### Commit message format
```
refactor(html_reporter): <what> [phase N]

- bullet 1
- bullet 2

Validates against OpenShift + Naba-Apr2026 golden files.
```

### Per-phase validation loop
Every phase must end with the report rendering **byte-identical** to the
pre-refactor goldens after timestamp normalization. Since `html_reporter.py`
embeds `Generated: YYYY-MM-DD HH:MM` at line ~1485, the regression harness
strips that line before hashing/diffing. The acceptance bar is therefore:

    normalized sha256(post) == normalized sha256(pre)

which is stronger than "whitespace-only diff" and catches any semantic change,
including single-character typos, reordered attributes, or silently dropped
content.

The loop is:

1. `python3 -c "import py_compile; py_compile.compile('reporters/html_reporter.py', doraise=True)"`
2. `/Users/aelnatsh/Lab/refactor-goldens/compare.sh -w` — must print `IDENTICAL ✓` twice
3. Optionally `compare.sh --checksum` to confirm normalized SHAs match
4. Open both generated HTMLs in a browser, click every tab, verify filters and sum rows
5. Only then: `git commit`

Both datasets (OpenShift 4-file + Naba-Apr2026 3-file) are covered by a single
`compare.sh` run, so the full-feature and optional-file code paths both gate
the commit.

### Rollback
Each phase is a single branch. If validation fails and the fix isn't obvious:
`git checkout main && git branch -D refactor/html-reporter-phase-N` and reassess.


---

## Phase 0 — Prep: generate golden files

**Status: COMPLETE (April 2026)**

**Goal:** capture known-good report output for regression comparison.

**What was built:**

Location: `/Users/aelnatsh/Lab/refactor-goldens/` (outside the repo, intentionally
not version-controlled — these are large HTML artifacts regenerated on demand).

1. **`generate_golden.py`** — standalone harness that replicates `app.py`'s
   pipeline exactly. Not using the repo CLI `generate_report.py` because it is
   stale: it neither accepts `--pods-top` nor passes `workloads` to
   `generate_html_report`, which would omit the entire Workload Inventory tab
   from the golden and lose regression coverage for ~195 lines of code. The
   harness imports from the live repo, so it tracks whatever HEAD is checked out.

2. **`openshift-pre.html`** (240 KB, 3177 lines)
   - Source: `/Users/aelnatsh/Downloads/Data/OpenShift/` (all 4 files)
   - 5 nodes, 255 pods, 14 PVs, 255 pods-top entries (100% match rate)
   - Exercises every tab including recommendations, checklist, storage

3. **`naba-pre.html`** (169 KB, 3384 lines)
   - Source: `/Users/aelnatsh/Downloads/Data/Naba-Apr2026/` (3 files, no PV)
   - 11 nodes, 100 pods, 100 pods-top entries
   - Exercises the "no PV data" empty state on the Storage tab
   - Exercises the high OS-overhead scenario (80% overhead on this cluster)

4. **`compare.sh`** — regression harness. Regenerates `*-post.html` from the
   current repo HEAD, then diffs against `*-pre.html` with the `Generated:`
   timestamp line normalized out. Acceptance bar: `IDENTICAL ✓` on both.
   Flags: `-w` (whitespace-insensitive, primary check), `--checksum` (print
   raw + normalized sha256).

5. **`goldens-checksums-pre.txt`** — raw sha256 of both pre files, for
   tamper detection.

**Key finding during Phase 0:** the HTML output is **fully deterministic**
apart from the minute-precision timestamp. After normalization the sha256
is byte-stable across regenerations, which means the acceptance criterion
for every subsequent phase is the strongest possible:

    normalized sha256(post) == normalized sha256(pre)

This was verified by generating pre files at 18:38, regenerating post files
at 18:43 (different minute), confirming raw SHAs differ and normalized SHAs
match exactly.

**Cross-minute verification (recorded here for future reference):**
- `openshift` normalized SHA: `e8f8cd58b9aff74ebea860b80a5c88e420410396e787c5142e647a06ab67b250`
- `naba` normalized SHA: `d85ca1b35ca775b8bcf03719ce8e83ff3155f65f7e3919824364781c090fa237`

After each future phase, these normalized SHAs must still match.

**Usage (for every subsequent phase):**
```bash
# Fast regression check
/Users/aelnatsh/Lab/refactor-goldens/compare.sh -w

# Checksum audit
/Users/aelnatsh/Lab/refactor-goldens/compare.sh --checksum
```

**Deliverable:** Phase 0 artifacts listed above. Branch `refactoring` created
and tracking this plan doc. Ready to start Phase 1.


---

## Phase 1 — Extract CSS to `styles.py`

**Goal:** move the 1,145 static CSS lines out of the f-string into a plain Python
string constant.

**Branch:** `refactor/html-reporter-phase-1-styles`

**Risk:** Low. Confirmed during assessment: CSS block (lines 323–1468) has **zero**
data interpolation. Every brace in there is an f-string escape.

**Files created:**
- `reporters/styles.py` — module exporting `STYLES: str`

**Files modified:**
- `reporters/html_reporter.py` — CSS block replaced with `{STYLES}` injection

**Steps:**
1. Read lines 323–1468 of current `html_reporter.py` into a temp file.
2. Globally replace `{{` → `{` and `}}` → `}` in the extracted content.
   (Verify: `grep -c '{{' /tmp/css-extracted.txt` should return 0 afterward.)
3. Create `reporters/styles.py`:
   ```python
   # Auto-extracted from html_reporter.py Phase 1 refactor.
   # Do NOT reintroduce f-string escaping — this is a plain triple-string.
   STYLES = """
       <…extracted CSS here, unescaped…>
   """
   ```
   Keep the leading/trailing `<style>` / `</style>` tags **inside** the constant
   so the injection site stays a one-liner.
4. In `html_reporter.py`:
   - Add `from reporters.styles import STYLES` at the top
   - Replace the entire `<style>…</style>` block (including the tags) with `{STYLES}`
5. Reconstruct `html_reporter.py` using the `head` + new content + `tail` pattern
   per the established workflow (reliable for files this size).
6. `py_compile` validation.
7. Regenerate both goldens and whitespace-diff against the Phase 0 originals.

**Validation acceptance criteria:**
- `py_compile` passes
- Both new reports diff against goldens with whitespace-only differences
- All tabs render and behave identically in browser

**Gotchas:**
- The CSS contains a few `@media` blocks and `@keyframes fadeIn` — these still use
  nested `{` `}` as CSS syntax, not f-string escapes. Double-check the global
  replace doesn't over-match. A clean regex: `s/\{\{/\{/g; s/\}\}/\}/g` applied
  only to the extracted block.
- Keep the exact indentation — HTML source-view diff readability matters for
  Ziko's ongoing review workflow.

**LOC impact:**
- `html_reporter.py`: 3,001 → ~1,856 (−1,145)
- `styles.py`: new, ~1,145 lines

**Effort:** ~1 session.


---

## Phase 2 — Extract JS to `scripts.py`

**Goal:** move the ~575-line JS block out of the f-string.

**Branch:** `refactor/html-reporter-phase-2-scripts`

**Risk:** Low-Medium. JS has 5 interpolation points (confirmed during assessment):
- `const nodesData = {json.dumps(nodes_json)};`
- `const namespaceData = {json.dumps(dict(sorted_ns))};`
- `const roleData = {json.dumps(dict(summary.nodes_by_role))};`
- Two chart `data: [{round(…)},{round(…)},{round(…)}]` arrays with summary totals

**Strategy:** move all the static JS into a `SCRIPT_BODY` constant. Keep a small
`build_data_prelude(ctx)` function that emits the 5 dynamic `const`/array
injections as a `<script>` block. The orchestrator renders them in order:
`<script>{data_prelude}</script>` immediately followed by `<script>{SCRIPT_BODY}</script>`.

**Files created:**
- `reporters/scripts.py` — exports `SCRIPT_BODY: str` and `build_data_prelude(ctx) -> str`

**Files modified:**
- `reporters/html_reporter.py` — JS block replaced with two `<script>` injections

**Steps:**
1. Identify the 5 interpolation points precisely (`grep -n "{json.dumps\|{round" reporters/html_reporter.py` limited to the JS range).
2. Refactor the two chart `data:` arrays to read from the existing `roleData` /
   new constants instead of inline interpolation, OR keep them in the prelude.
   The former is cleaner.
3. Copy the JS body (post-interpolation lines through `</script>`) into
   `scripts.py` as `SCRIPT_BODY = """…"""`.
4. Global `{{` → `{` and `}}` → `}` on the extracted content.
5. Define `build_data_prelude(nodes_json, sorted_ns, role_data, summary)` in
   `scripts.py` returning the small `const x = …; const y = …;` string.
6. In `html_reporter.py`, replace the JS block with:
   ```
   <script>{build_data_prelude(...)}</script>
   <script>{SCRIPT_BODY}</script>
   ```
7. `py_compile`, regenerate goldens, diff, browser-test (especially: tab
   switching, filter buttons, sum-row recomputation, CSV download).

**Validation acceptance criteria:**
- `py_compile` passes
- Both reports diff whitespace-only
- Click every tab, every filter button, every CSV export — must all still work
- Chart.js renders correctly on every chart

**Gotchas:**
- JS uses `{` and `}` for object literals, function bodies, and template
  literals (backticks). The global unescape is safe because currently
  **every** brace in the JS range is escaped, but verify with:
  `grep -E '[^{]\{[^{]' <extracted-js.txt> | head` — any hit is either
  f-string interp (already handled) or a bug.
- Template literals `` `${var}` `` inside the JS remain unchanged (they're
  string contents, not Python f-string syntax).

**LOC impact:**
- `html_reporter.py`: ~1,856 → ~1,280 (−576)
- `scripts.py`: new, ~580 lines

**Effort:** ~1 session.


---

## Phase 3 — `ReportContext` dataclass

**Goal:** isolate data shaping from HTML rendering. After this phase, each future
tab module takes a single `ctx: ReportContext` argument.

**Branch:** `refactor/html-reporter-phase-3-context`

**Risk:** Low. Pure Python refactor; no HTML touched.

**Files created:**
- `reporters/report_context.py` — `ReportContext` dataclass + `build_context(...)` factory

**Files modified:**
- `reporters/html_reporter.py` — data-prep block (current lines 222–320) replaced
  with `ctx = build_context(nodes, summary, recommendations, pvs, workloads)`
  and the rest of the function references `ctx.nodes_json` etc.

**Proposed shape:**
```python
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass(frozen=True)
class ReportContext:
    nodes: List['NodeData']
    summary: 'ClusterSummary'
    recommendations: Dict
    pvs: List['PersistentVolume']
    workloads: Dict
    include_recommendations: bool

    # Pre-computed view models
    nodes_json: List[Dict[str, Any]]
    pvs_json: List[Dict[str, Any]]
    role_summaries: Dict[str, Dict[str, Any]]
    namespace_pods: Dict[str, int]
    sorted_ns: List[tuple]

def build_context(nodes, summary, recommendations, pvs,
                  include_recommendations=True, workloads=None) -> ReportContext:
    # existing lines 222–320 logic, lifted verbatim
    ...
```

**Steps:**
1. Create `reporters/report_context.py` with the dataclass and factory.
2. Copy the data-prep logic (current lines ~230–315) verbatim into `build_context`.
3. In `html_reporter.py`, replace the data-prep block with a single
   `ctx = build_context(...)` call.
4. Update all variable references inside the f-string:
   `nodes_json` → `ctx.nodes_json`, `role_summaries` → `ctx.role_summaries`, etc.
   (Do this via `edit_block` for each distinct variable name, not a global regex.)
5. `py_compile`, regenerate goldens, diff.

**Validation acceptance criteria:**
- `py_compile` passes
- Both reports diff whitespace-only (should be byte-identical since this is a
  pure extraction of data-flow with no formatting change)

**Gotchas:**
- The `summary` object itself has methods used inside the f-string (e.g.
  `summary.total_actual.cpu`). Keep `summary` on the context as-is — don't
  try to flatten everything.
- `sorted_ns` is currently a local `list` derived from `namespace_pods`.
  Keep both on the context; it's used twice in JS prelude + Workloads tab.

**LOC impact:**
- `html_reporter.py`: ~1,280 → ~1,200 (−80, but primarily structural)
- `report_context.py`: new, ~110 lines

**Effort:** ~1 session.


---

## Phase 4 — Extract layout shell to `layout.py`

**Goal:** move the outer HTML frame (DOCTYPE, head, header bar, nav-tabs, main
wrapper, footer, closing tags) into a separate layout module, so the main
orchestrator becomes a pure assembly of `shell + tabs`.

**Branch:** `refactor/html-reporter-phase-4-layout`

**Risk:** Medium. The nav-tabs list and tab-content blocks both reference the
same `include_recommendations` conditional. Care needed to keep them in sync.

**Files created:**
- `reporters/layout.py` — `build_layout(ctx, styles, data_prelude, script_body, tabs_html) -> str`

**Files modified:**
- `reporters/html_reporter.py` — becomes an assembler that calls `build_layout(...)`

**Steps:**
1. Identify the shell boundaries:
   - Shell HEAD: `<!DOCTYPE html>` through the end of `<nav class="nav-tabs">` block
   - Shell MIDDLE: `<main class="main-content">` open
   - `{tabs_html}` injection point
   - Shell TAIL: `</main>`, `<footer>`, scripts, `</body></html>`
2. Design the nav-tabs as a **data-driven** list in the context:
   ```python
   @dataclass
   class TabDef:
       id: str
       label: str
       always_visible: bool = True

   TABS = [
       TabDef('overview', 'Overview'),
       TabDef('nodes', 'Node Inventory'),
       TabDef('efficiency', 'Efficiency Analysis'),
       TabDef('workloads', 'Workload Distribution'),
       TabDef('workload-inventory', 'Workload Inventory'),
       TabDef('recommendations', 'OCP Recommendations', always_visible=False),
       TabDef('checklist', 'Migration Checklist', always_visible=False),
       TabDef('storage', 'Persistent Volumes'),
   ]
   ```
   Filter based on `include_recommendations` and pv presence.
3. Create `reporters/layout.py` exporting `build_layout(...)`.
4. The layout function builds the nav by iterating the active tabs list,
   injects `{tabs_html}` between `<main>` tags, injects styles/scripts.
5. `html_reporter.py` becomes: build context → render each tab into a dict
   keyed by tab id → join into `tabs_html` → call `build_layout`.

**Validation acceptance criteria:**
- `py_compile` passes
- Both reports diff whitespace-only
- Conditional tabs (recommendations/checklist) correctly absent when flag is off
- Storage tab correctly shows "no data" state when pvs missing

**Gotchas:**
- **This phase eliminates the `<!--` hack on current line 2028** as a bonus.
  Once tab assembly is data-driven, you just skip disabled tabs entirely
  rather than wrapping their content in an HTML comment.
- Footer text is currently inside the f-string. Move it into the layout too.

**LOC impact:**
- `html_reporter.py`: ~1,200 → ~1,050 (tab bodies still inline)
- `layout.py`: new, ~90 lines

**Effort:** ~1 session.


---

## Phase 5 — Split tabs into `reporters/tabs/*.py`

**Goal:** one file per tab. Each exports `build(ctx: ReportContext) -> str`.

**Branch strategy:** each tab gets its own sub-branch to keep commits small
and reviewable. Merge each to `main` before starting the next:
- `refactor/html-reporter-phase-5a-overview`
- `refactor/html-reporter-phase-5b-nodes`
- `refactor/html-reporter-phase-5c-efficiency`
- `refactor/html-reporter-phase-5d-workloads`
- `refactor/html-reporter-phase-5e-workload-inventory` (just moving the existing func)
- `refactor/html-reporter-phase-5f-recommendations`
- `refactor/html-reporter-phase-5g-checklist`
- `refactor/html-reporter-phase-5h-storage`

**Risk per sub-phase:** Low-Medium each. Same pattern repeated 7 times + 1 move.

**Common pattern for each tab module:**
```python
# reporters/tabs/overview.py
from reporters.report_context import ReportContext

def build(ctx: ReportContext) -> str:
    return f'''
    <div class="tab-content active" id="overview">
        … existing tab HTML, unchanged, referencing ctx.* …
    </div>
    '''
```

**Steps per sub-phase (same recipe):**
1. Identify the tab's line range in current `html_reporter.py` (nav-tab div + tab-content div).
2. Create `reporters/tabs/<name>.py` with a `build(ctx)` function.
3. Copy the tab's HTML into the function body as an f-string.
4. Replace variable references: bare `nodes_json` → `ctx.nodes_json`, etc.
   (If Phase 3 was done properly, this is already done.)
5. In `html_reporter.py`, replace the tab's HTML block with a call:
   `overview_html = tabs.overview.build(ctx)`
6. Inject `overview_html` into the layout via the tabs dict built in Phase 4.
7. `py_compile`, regenerate goldens, diff — per sub-phase.

**Order matters — easiest first:**
1. **5e — workload-inventory first** (pure move of existing `_generate_workload_inventory_tab`, trivial)
2. **5h — storage** (simple, already behind a conditional)
3. **5a — overview** (no filters, no charts of complex state)
4. **5d — workloads** (has filters, charts)
5. **5b — nodes** (has filters, complex table)
6. **5c — efficiency** (has filters, cards, per-node chart)
7. **5f — recommendations** (conditional tab)
8. **5g — checklist** (conditional tab)

**Validation per sub-phase:**
- `py_compile` passes
- Golden diff whitespace-only
- The specific tab and its interactions work in the browser
- No other tab regresses (Chart.js initialization order matters)

**Gotchas:**
- If a tab defines a Chart.js chart, the `new Chart(...)` call currently lives
  in the JS block (already extracted in Phase 2). Leave the chart initialization
  in `scripts.py`; tab modules only produce the `<canvas>` element with a
  stable `id`. The JS looks up canvas IDs at runtime.
- Filter buttons in tabs use `data-table="<id>"` to wire up to the correct
  table. These IDs must remain unique across all tabs — grep for collisions.
- The `sorted_ns` data is used by Workloads tab AND the JS prelude. Make sure
  it's on the context from Phase 3 (not recomputed).

**LOC impact (cumulative after all sub-phases):**
- `html_reporter.py`: ~1,050 → ~120 (orchestrator only)
- 8 tab files: ~80-200 lines each

**Effort:** ~3-4 sessions (grouping 2-3 tabs per session).


---

## Phase 6 — Extract common UI components

**Goal:** eliminate the duplication that Phase 5 will have surfaced.

**Branch:** `refactor/html-reporter-phase-6-components`

**Risk:** Low. Pure DRY refactor once tabs exist.

**Files created:**
- `reporters/components.py` — helper functions

**Helpers to extract** (based on current duplication):
1. **`filter_bar(table_id, role_summaries, total_count)`** — builds the role
   filter button row. Used 3+ times in current code (Nodes, Efficiency, Workloads).
2. **`no_data(icon, title, message, command=None)`** — the empty-state block
   shown when PVs / pods-top are missing.
3. **`summary_card(title, icon, value, subtitle, detail, advice, card_class)`**
   — the stat cards on Overview, Efficiency, Workload Inventory tabs.
4. **`sum_row_tfoot(columns)`** — generates the `<tfoot>` markup for the
   dynamic-sum-row tables. (Backbone is in JS, but HTML scaffolding repeats.)
5. **`role_badge(role)`** — the colored role badge, repeated in every table.

**Steps:**
1. After Phase 5, survey tabs for repeated fragments. Pick the 3-5 with
   the highest duplication.
2. Create `reporters/components.py`. Each helper: small, self-contained,
   returns a string.
3. For each tab that uses a helper, replace the inline markup with a call.
   One tab at a time, commit each.
4. `py_compile`, regenerate goldens, diff per helper extracted.

**Validation acceptance criteria:**
- Byte-identical output (helpers must produce exactly the same HTML)
- `py_compile` passes
- No visual regression

**Gotchas:**
- Don't over-abstract. A helper is only worth it if used ≥2 places. Keep
  single-use markup inline in the tab module.
- Whitespace is load-bearing for byte-identical diffs. Use triple-strings
  with exact indentation matching the originals.

**LOC impact:**
- Each tab file shrinks by 10-30 lines
- `components.py`: new, ~150 lines

**Effort:** ~1 session.

---

## Phase 7 — Cleanup pass

**Goal:** final tidying, now that the structure is clear.

**Branch:** `refactor/html-reporter-phase-7-cleanup`

**Items:**
- Remove the `<!--` conditional-comment hack if Phase 4 didn't already.
- Delete any unreachable code left in `html_reporter.py`.
- Add module docstrings to every new file explaining its role.
- Update `documentation/documentation.md` with the new architecture diagram.
- Run the backlog item #20 file-upload validation once, to confirm the new
  structure makes new-feature work easier (sanity check of the refactor's
  stated goal).

**Effort:** ~0.5 session.


---

## Session budget & progress tracker

| Phase | Description | Est. sessions | Status | Branch merged |
|---|---|---|---|---|
| 0 | Golden file capture | 0.25 | ✅ done | n/a (artifacts in `/Users/aelnatsh/Lab/refactor-goldens/`) |
| 1 | CSS → `styles.py` | 1 | ✅ done | `refactor/html-reporter-phase-1-styles` → `refactoring` |
| 2 | JS → `scripts.py` | 1 | ☐ | |
| 3 | `ReportContext` dataclass | 1 | ☐ | |
| 4 | Layout shell | 1 | ☐ | |
| 5a | Tab: workload-inventory (move) | 0.25 | ☐ | |
| 5b | Tab: storage | 0.25 | ☐ | |
| 5c | Tab: overview | 0.5 | ☐ | |
| 5d | Tab: workloads | 0.5 | ☐ | |
| 5e | Tab: nodes | 0.5 | ☐ | |
| 5f | Tab: efficiency | 0.5 | ☐ | |
| 5g | Tab: recommendations | 0.5 | ☐ | |
| 5h | Tab: checklist | 0.5 | ☐ | |
| 6 | Common components | 1 | ☐ | |
| 7 | Cleanup + docs | 0.5 | ☐ | |

**Total: ~9–10 focused sessions.**

---

## After the refactor: cheatsheet for future tab additions

Adding a new tab (e.g. "Security Posture") becomes:

1. Create `reporters/tabs/security_posture.py` with a `build(ctx) -> str` function.
2. If the tab needs new pre-computed data, add a field to `ReportContext` and
   populate it in `build_context()`.
3. Add one entry to the `TABS` list in `layout.py` (id + label + visibility rule).
4. If the tab needs JS, append a function to `scripts.py` — it'll find the tab's
   canvas/table by id at runtime.
5. Add `<style>` rules specific to the tab to `styles.py` if needed.
6. Regenerate test report, verify, commit.

No touching `html_reporter.py` for a typical new tab.

---

## Key principles to honor during this refactor

- **Assess before implement** — each phase starts with an assessment reply,
  waits for Ziko's explicit go-ahead, then executes.
- **One phase per session** — no skipping ahead, no combining phases.
- **Golden-file validation** — every phase ends with a whitespace-only diff.
- **Desktop Commander for everything** — file ops, terminal, process execution.
- **No output changes** — if you find a bug during refactor, file it separately
  and fix it AFTER the phase lands. Never mix refactor and fix in the same commit.
