# `components/` Refactor Plan (Tier 1)

**Status:** Planning (not started)
**Created:** April 2026
**Owner:** Ziko
**Scope:** RHV/VMware migration tool side only — `components/scripts.py` and `components/styles.py`

## Why this refactor

The just-completed OCP refactor modularized the `reporters/` side from a 3,001-line monolith to 14 focused modules. The RHV side (`components/`) has a partial modularization — tabs are already split (`tab_*.py`), but two monoliths remain:

- `components/scripts.py` — 1,237 lines (1,162 of actual JS body + 7 interpolation points)
- `components/styles.py` — 956 lines (938 of CSS body, already plain string, no brace escaping)

Leaving these means the codebase has **two reporting subsystems at different maturity levels**. New contributors working on the RHV side will still encounter a multi-hundred-line scroll to find a chart config or a CSS rule. The goal is symmetry: make both sides navigable at the same level.

**Explicitly out of scope for Tier 1:**
- `app.py` route splitting (Tier 2 — 680 lines, already well-factored into named routes)
- `sources/base_processor.py` mixin split (Tier 3 — leave alone, it's a coherent base class)
- Any behavior change, UI tweak, or feature addition — pure refactor

## Current state inventory

```
components/
  __init__.py              (exports styles, scripts, tab builders)
  base.py          174 LOC (HTML shell — analogous to our new reporters/layout.py)
  styles.py        956 LOC ← MONOLITH, plain triple-string
  scripts.py     1,237 LOC ← MONOLITH, f-string with 7 data interpolations
  tab_overview.py  236 LOC (already per-tab — not touched)
  tab_inventory.py 161 LOC
  tab_sizing.py    184 LOC
  tab_migration.py 231 LOC
  tab_trends.py    224 LOC
  tab_forecast.py  374 LOC
  tab_hosts.py     331 LOC
```

Consumption:
- `generate_dashboard.py` → imports `generate_scripts`, `collect_chart_configs`, and the `get_styles()` via `components/__init__.py`
- `components/base.py` → calls `get_styles()` and splices result via `{get_styles()}` inside its own f-string
- Flask app: `/generate-migration` route calls `generate_dashboard.create_dashboard(...)` (via the handler in `app.py`)

Key findings from reconnaissance:
- **`styles.py` is already a plain string**, not an f-string — so `{` and `}` in the CSS are naked (no `{{`/`}}` escaping needed). Extraction is trivial: rename the function to a module-level constant.
- **`scripts.py` has 7 interpolation points**, all at the top of the JS body, all injecting pre-rendered chart config blobs. The rest of the ~1,155 lines is pure static JS. Same pattern as OCP `scripts.py` before Phase 2 (which had 5 interps in a 571-line block).
- **CSS has 19 explicit `/* ====== SECTION ====== */` dividers** — if we wanted to split CSS into multiple files later, the boundaries are already marked.

## Cross-cutting conventions

Same as the OCP refactor:

- One feature branch per phase: `refactor/components-phase-N-<name>`
- Standard flow: `git checkout -b refactor/... → develop → commit → merge to main → push → delete`
- Commit message format: `refactor(components): <what> [phase N]`
- Per-phase validation loop:
  1. `py_compile` on all modified files
  2. Run `compare.sh --checksum` against RHV goldens (built in Phase 0)
  3. Normalized SHA must match pre-refactor baseline
  4. Open the RHV report in browser, click through tabs, verify charts and filters
  5. Only then: commit
- Rollback: single-branch-per-phase, `git branch -D` if validation fails

## Regression harness (Phase 0 — ✅ COMPLETE)

**Outputs (all outside the repo, at `/Users/aelnatsh/Lab/refactor-goldens/`):**

- `generate_rhv_golden.py` — wraps `generate_dashboard(...)` from the repo so the
  same pipeline the Flask `/generate-migration` route uses can be invoked
  deterministically against the two production XLSX exports.
- `rhv-pre.html` — 1,031 KB, 14,576 lines, generated from:
  - `/Users/aelnatsh/Downloads/RHV-Prod-ENV.xlsx` (593 VMs)
  - `/Users/aelnatsh/Downloads/rhv_hosts-Prod-ENV.xlsx` (62 hosts)
- `compare.sh` — extended to cover three datasets (OpenShift, Naba, RHV) with
  a normalize() that strips both the OCP-side `Generated: YYYY-MM-DD HH:MM`
  line and the RHV-side `<div class="value">YYYY-MM-DD HH:MM:SS</div>`
  inside the header.

**Key finding:** the RHV dashboard is fully deterministic apart from a single
`generated_at` timestamp at line 959 (set in `sources/base_processor.py:466`
via `datetime.now().strftime('%Y-%m-%d %H:%M:%S')`). Second-precision, one
occurrence, exact DOM surround — easy to normalize without false positives.

**Normalized SHA-256 baselines (must match after every subsequent phase):**
- OpenShift: `e8f8cd58b9aff74ebea860b80a5c88e420410396e787c5142e647a06ab67b250` (unchanged from OCP refactor Phase 0)
- Naba:      `d85ca1b35ca775b8bcf03719ce8e83ff3155f65f7e3919824364781c090fa237` (unchanged)
- **RHV:**   `e831ccb1542069897208d68b0b76d70671ce9a842607f58e1aaef8dfaefa47e8`

**Usage for every subsequent phase:**
```bash
/Users/aelnatsh/Lab/refactor-goldens/compare.sh -w         # fast check
/Users/aelnatsh/Lab/refactor-goldens/compare.sh --checksum # SHA audit
```
Both must report IDENTICAL ✓ on all three datasets before a phase commits.

## Phases

### Phase 1 — `components/styles.py` → `STYLES` constant

**Goal:** Replace the `def get_styles(): return '''...'''` wrapper with a module-level `STYLES: str` constant. Remove the function call overhead and make the pattern match `reporters/styles.py`.

**Why safe:** The CSS body is already a plain triple-string with zero interpolation. No `{{`/`}}` escaping to undo. The only caller is `components/base.py` which currently does `{get_styles()}`; change that to `{STYLES}` and import the constant.

**Changes:**
- `components/styles.py`: function body becomes `STYLES = """..."""` at module level; keep a thin `def get_styles(): return STYLES` wrapper for any third-party caller (grep says nothing external calls it, but belt-and-suspenders)
- `components/base.py`: swap `from .styles import get_styles` + `{get_styles()}` → `from .styles import STYLES` + `{STYLES}`
- `components/__init__.py`: re-export `STYLES` alongside `get_styles`

**LOC impact:** styles.py: 956 → ~955 (negligible — it's a renaming, not extraction). Pattern impact: makes the RHV side consistent with the new OCP side.

**Risk:** Very low. Single function-call swap.

**Effort:** ~0.5 session.

**Open question for review:** Do we want to go further and split the CSS into multiple files by section (`styles/base.py`, `styles/charts.py`, `styles/tables.py`, …)? The 19 section markers make this easy. **My recommendation: no** — 938 lines of well-commented CSS in one file is fine; the section markers act as an in-file navigation index. Splitting would spread the concern across 10+ files for marginal benefit. We can revisit if the CSS grows another 40%.

### Phase 2 — `components/scripts.py` → `SCRIPT_BODY` constant + `build_data_prelude()`

**Goal:** Same shape as the OCP Phase 2. The ~1,155 lines of static JS become a module-level `SCRIPT_BODY` constant. The 7 data interpolations become a small `build_data_prelude(data, chart_configs)` function that emits `const` declarations. Output concatenated: `<script>{data_prelude}\n{SCRIPT_BODY}</script>`.

**Why safe:** Identical pattern to OCP Phase 2, which landed byte-identical in one try. 7 interpolation points is few.

**Changes:**
- `components/scripts.py`: split into three pieces
  - `SCRIPT_BODY = r"""..."""` — the 1,155 lines of static JS (raw string to preserve any `\n` etc. literally)
  - `build_data_prelude(data, chart_configs) -> str` — emits the 7 `const X = {...};` lines
  - `generate_scripts(data, chart_configs) -> str` — thin wrapper that returns `<script>\n{prelude}\n{SCRIPT_BODY}\n</script>` or equivalent, preserving the exact text the existing callers get
- Callers (`generate_dashboard.py`, Flask handler) unchanged — same public API

**LOC impact:** scripts.py: 1,237 → probably 3 files or one file with 3 clearly-separated sections, same total size but now mechanically obvious where each piece lives.

**Risk:** Low. Identified and fixed subtly-different cases on OCP Phase 2 (trailing newline) — will apply the same discipline here.

**Effort:** ~1 session.

**Open question for review:** After extracting SCRIPT_BODY, do we go one step further and split the JS into per-feature files (`scripts/tabs.js`, `scripts/filters.js`, `scripts/charts_overview.js`, `scripts/charts_sizing.js`, `scripts/charts_hosts.js`, `scripts/charts_migration.js`, `scripts/charts_forecast.js`, `scripts/charts_trends.js`)? **My recommendation: assess after Phase 2 lands.** Natural section markers exist in the file (`initOverviewCharts`, `initSizingCharts`, etc.), so if the `SCRIPT_BODY` constant still feels unwieldy, Phase 3 can split it. Don't pre-commit to Phase 3 in advance.

### Phase 3 (optional, decide after Phase 2) — Further JS split by feature

**Trigger:** only if Phase 2's `SCRIPT_BODY` constant is still hard to navigate at 1,155 lines.

**Goal:** Split static JS into a `components/scripts_js/` subpackage by functional area, reassembled in `generate_scripts()`.

**Candidate split (based on grep output from recon):**
```
components/scripts_js/
  __init__.py
  tabs.py              # switchTab()
  filters.py           # applyFilters(), resetFilters()
  inventory.py         # updateInventoryTable(), updateStatCards()
  charts_overview.py   # initOverviewCharts()
  charts_sizing.py     # initSizingCharts()
  charts_hosts.py      # initHostResourceTable(), renderHostTable(), etc.
  charts_migration.py  # initMigrationCharts()
  charts_forecast.py   # (forecast math + chart)
  charts_trends.py     # (growth trends chart)
```

Each exports a string constant. `components/scripts.py` concatenates them in order.

**Risk:** Medium-low. Order of definitions matters for JS (functions must be defined before they're called). Need to preserve the existing order.

**Effort:** ~1 session if pursued.

## Phase summary & session budget

| Phase | Description | Est. sessions | Status |
|---|---|---:|---|
| 0 | RHV golden harness (`generate_rhv_golden.py` + extended `compare.sh`) | 0.5 | ✅ done |
| 1 | `styles.py` → `STYLES` constant | 0.5 | ✅ done |
| 2 | `scripts.py` → `SCRIPT_BODY` + `build_data_prelude()` | 1 | ✅ done |
| 3 | JS split into `scripts_js/` subpackage (optional) | 1 | ☐ (decide after 2) |

**Total minimum (phases 0-2): ~2 sessions.**
**With optional Phase 3: ~3 sessions.**

For comparison: the OCP `reporters/` refactor took 9-10 sessions across 8 phases. The RHV `components/` refactor is much smaller scope because:
- Tabs are already split (no Phase 5 equivalent)
- There's no ReportContext equivalent to introduce (data flows through `chart_configs` dict already)
- There's no outer shell to extract (base.py already is the layout)
- There's no per-tab orchestrator to simplify (generate_dashboard.py already does this role)

So we're doing only the bits that the OCP Phase 1 + Phase 2 did — not the full stack.

## What this does NOT fix

- `generate_dashboard.py` (220 lines) — the CLI orchestrator. Stays as-is; it's already well-factored.
- `app.py` (680 lines) — Tier 2 work, a separate decision about Flask blueprints.
- Data-side concerns (`sources/base_processor.py`, `sources/rhv_processor.py`, etc.) — Tier 3, leave alone.
- The actual UI: zero visual or functional change. Byte-identical output after timestamp normalization.

## Key principles (inherited from OCP refactor)

- **Assess before implement** — each phase starts with an assessment reply, waits for explicit approval, then executes.
- **One phase per session** — no combining phases unless a session clearly has time.
- **Golden-file validation** — every phase ends with `compare.sh --checksum` returning matching normalized SHAs.
- **Always use `--checksum`, never just `-w`** — lesson from OCP Phase 6: whitespace-only drift passes `-w` but fails `--checksum`.
- **No output changes** — if a bug is found during refactor, file it separately, fix it AFTER the phase lands.

## Decision points for Ziko's review

1. **Go / no-go on Phase 1 at all.** `components/styles.py` is already a plain string with section markers. It's a bigger file than ideal but not actively harmful. Worth the 0.5 session, or skip?
2. **Phase 2 scope — `SCRIPT_BODY` only, or pre-commit to per-feature split?** Recommend the lighter version first, decide on Phase 3 after seeing the result.
3. **RHV golden data selection.** Is the production XLSX pair (`RHV-Prod-ENV.xlsx` + `rhv_hosts-Prod-ENV.xlsx`) the right regression baseline? Any concerns about including sensitive/production data in a golden file stored locally?
4. **Merge strategy.** Same `--no-ff` merge commit per phase on a feature branch, merge feature branch into `main`? Or go straight to `main` for low-risk phases?
