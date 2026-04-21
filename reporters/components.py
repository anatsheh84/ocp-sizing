# -*- coding: utf-8 -*-
"""
components.py
-------------
Reusable HTML fragments shared across multiple tab modules.

Phase 6 of the html_reporter.py refactor extracted these helpers after
the individual tabs (Phase 5) surfaced which markup was truly duplicated
versus superficially similar. Current helpers:

- role_filter_bar(ctx, table_id) — the "Filter by Role" button row, used
  by the Node Inventory, Efficiency, and Workload Distribution tabs.

Helpers are kept minimal: a fragment is only extracted when it appears
in ≥2 tabs with identical markup (byte-for-byte apart from one or two
attribute values). Single-use or visually-similar-but-structurally-
different fragments stay inline in their tab modules.

Byte-identity is a hard invariant: helpers must return exactly the same
text (including whitespace and indentation) that was previously inline.
"""

from reporters.report_context import ReportContext


def role_filter_bar(ctx: ReportContext, table_id: str) -> str:
    """Build the "Filter by Role" button row for a data table.

    Args:
        ctx: report context (provides ctx.nodes and ctx.role_summaries)
        table_id: HTML id of the target table (e.g. 'nodesTable',
                  'efficiencyTable', 'workloadTable')

    Returns:
        A 13-line HTML fragment, pre-indented to match its original
        inline position (12-space leading indent on the first line).
    """
    nodes = ctx.nodes
    role_summaries = ctx.role_summaries
    return f'''            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="{table_id}">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="' + table_id + '">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="' + table_id + '">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="' + table_id + '">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="' + table_id + '">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>'''
