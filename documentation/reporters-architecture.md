# OCP Sizing Reporter — Architecture

Present-tense reference for the `reporters/` module layout. For the
phase-by-phase history of how the code got here, see
[`html-reporter-refactor-plan.md`](./html-reporter-refactor-plan.md).

## Module overview

```
reporters/
  html_reporter.py       orchestrator (≈90 lines)
  report_context.py      ReportContext dataclass + build_context()
  layout.py              outer HTML shell (DOCTYPE, head, nav, footer)
  styles.py              static CSS
  scripts.py             static JS + build_script_body()
  components.py          shared UI fragments (role_filter_bar)
  pdf_exporter.py        optional PDF export (unchanged by refactor)
  tabs/
    overview.py
    nodes.py
    efficiency.py
    workloads.py
    workload_inventory.py
    recommendations.py
    checklist.py
    storage.py
```

## Call graph

```
app.py / generate_report.py
        │
        ▼
generate_html_report(nodes, summary, recommendations, pvs, …)
        │   in reporters/html_reporter.py
        │
        ├─▶ build_context(...) ──▶ ReportContext
        │       in reporters/report_context.py
        │       pre-computes nodes_json, sorted_ns, pvs_json,
        │       role_summaries, script_body_html, etc.
        │
        ├─▶ overview.build(ctx)              \
        ├─▶ nodes_tab.build(ctx)              \
        ├─▶ efficiency.build(ctx)              \ eight tab
        ├─▶ workloads_tab.build(ctx)           / modules, each
        ├─▶ workload_inventory.build(ctx)      / returning a
        ├─▶ recommendations_tab.build(ctx)    /  self-contained
        ├─▶ checklist.build(ctx)             /   HTML fragment
        ├─▶ storage.build(ctx)              /
        │
        │     each may call role_filter_bar(ctx, table_id)
        │     from reporters/components.py
        │
        ▼
tabs_content_html  (the 8 fragments, glued with blank separators)
        │
        ▼
build_layout(ctx, tabs_content_html, ctx.script_body_html)
        │   in reporters/layout.py
        │   injects STYLES, renders the <head>, header bar, nav-tabs,
        │   wraps tabs_content inside <main>, adds footer, appends
        │   ctx.script_body_html before </body>
        ▼
final HTML string
```

## Conventions

**Tab contract.** Every tab module under `reporters/tabs/` exports a
single public function:

```python
def build(ctx: ReportContext) -> str: ...
```

The function returns a complete tab-content block: either a
`<div class="tab-content" id="…">…</div>` for standard tabs, or (for
the conditional recommendations/checklist tabs) a conditional that
wraps the content in `<!-- … -->` when disabled to preserve the
pre-refactor byte-identical output.

*Exception:* `tabs/workload_inventory.py` still returns the inner
content without its own wrapping `<div class="tab-content">`; the
orchestrator provides the wrapper. Candidate for future cleanup.

**Import aliases.** Three tab modules share a name with a parameter
of `generate_html_report(nodes, …, recommendations, …, workloads)`,
so they must be aliased when imported to avoid shadowing:

```python
from reporters.tabs import nodes as nodes_tab
from reporters.tabs import workloads as workloads_tab
from reporters.tabs import recommendations as recommendations_tab
```

The other five (`overview`, `efficiency`, `workload_inventory`,
`checklist`, `storage`) import under their natural names.

**Pre-rendered HTML fragments.** Because Python f-strings cannot
call methods that produce side effects during construction, any tab
content that needs non-trivial computation is rendered into a local
`_html` variable first, then referenced with `{…_html}` inside the
parent f-string. This pattern is uniform across the orchestrator.

**Byte-identity invariant.** Every refactor phase was validated by
regenerating two golden HTML files (an OpenShift cluster with all
four input files, and a Kubernetes cluster with three inputs and no
PVs) and confirming the SHA-256 matched the pre-refactor baseline
after normalizing the `Generated: YYYY-MM-DD HH:MM` timestamp line.
Any future contribution to `reporters/` should run
`/Users/aelnatsh/Lab/refactor-goldens/compare.sh --checksum` before
committing.

## Adding a new tab

1. Create `reporters/tabs/<name>.py` exporting `build(ctx) -> str`.
2. If the tab needs pre-computed data, add a field to
   `ReportContext` in `report_context.py` and populate it inside
   `build_context()`.
3. If the tab should appear in the nav bar, add its nav-tab entry
   in `layout.py` (the nav-tabs HTML still lives inline there; a
   future refactor may data-drive this via a `TABS = [TabDef(...)]`
   list as noted in the refactor plan).
4. In `html_reporter.py`: add the import, call `build(ctx)` into a
   local `_html` variable, and splice it into `tabs_content_html`.

Steps 2 and 3 are optional for most new tabs — step 4 is the minimum.

## Shared UI fragments (`components.py`)

Helpers live here only when the same markup appears in ≥2 tab
modules with byte-identical output. Present list:

- `role_filter_bar(ctx, table_id)` — the "Filter by Role" button row
  used by `nodes`, `efficiency`, and `workloads`.

Candidates considered but not extracted during Phase 6:

- `no-data` empty-state block — only used in `storage`
- `summary-card` — same structure but each card has unique content
- `role-badge` — one-liner, too small to benefit from a helper
- `workload_inventory` filter bar — System/App filter pattern is
  structurally different from the role filter; not shareable

## Data shape (`ReportContext`)

See `reporters/report_context.py` for the authoritative dataclass
definition. Summary of fields:

**Raw (pass-through from the caller):**
`nodes`, `summary`, `recommendations`, `pvs`, `workloads`,
`include_recommendations`.

**Derived view-models (computed once in `build_context`):**
`nodes_json`, `namespace_pods`, `sorted_ns`, `pvs_json`,
`nodes_by_role`, `role_summaries`.

**Pre-rendered HTML fragment:** `script_body_html` (the
`<script>…</script>` block produced by
`reporters.scripts.build_script_body`).
