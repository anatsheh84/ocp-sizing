# -*- coding: utf-8 -*-
"""
html_reporter.py
----------------
Orchestrator for the OCP Sizing HTML report.

Since the refactor (phases 1-7, April 2026) this module does nothing but
glue: it calls build_context() to shape cluster data, invokes build()
on each of 8 tab modules, joins the per-tab HTML with a bit of
scaffolding, and hands the result to build_layout() which wraps it in
the outer HTML shell.

Module layout after the refactor:

    reporters/
      html_reporter.py       this file -- orchestration only
      report_context.py      ReportContext dataclass + build_context()
      layout.py              outer HTML shell (doctype, head, nav, footer)
      styles.py              static CSS
      scripts.py             static JS + build_script_body()
      components.py          shared UI fragments (role_filter_bar)
      pdf_exporter.py        optional PDF export (unchanged)
      tabs/
        overview.py, nodes.py, efficiency.py, workloads.py,
        workload_inventory.py, recommendations.py, checklist.py,
        storage.py          -- each exports build(ctx) -> str

Adding a new tab in this architecture is a 4-line change here plus one
new file in tabs/. See documentation/html-reporter-refactor-plan.md
for the full history of how we got here.
"""

from typing import Dict, List

from models import ClusterSummary, NodeData, PersistentVolume

from reporters.layout import build_layout
from reporters.report_context import build_context
from reporters.tabs import checklist
from reporters.tabs import efficiency
from reporters.tabs import nodes as nodes_tab
from reporters.tabs import overview
from reporters.tabs import recommendations as recommendations_tab
from reporters.tabs import storage
from reporters.tabs import workload_inventory
from reporters.tabs import workloads as workloads_tab


def generate_html_report(nodes: List[NodeData], summary: ClusterSummary,
                         recommendations: Dict, pvs: List[PersistentVolume],
                         include_recommendations: bool = True,
                         workloads: Dict = None) -> str:
    """Render the full OCP Sizing HTML report as a single string.

    Args match the historical call site in app.py; the additional
    conditional tabs (recommendations, checklist) are rendered but
    wrapped in HTML comments when include_recommendations is False
    so the output stays visually identical to the pre-refactor version.
    """
    ctx = build_context(nodes, summary, recommendations, pvs,
                        include_recommendations=include_recommendations,
                        workloads=workloads)

    overview_html = overview.build(ctx)
    nodes_html = nodes_tab.build(ctx)
    efficiency_html = efficiency.build(ctx)
    workloads_html = workloads_tab.build(ctx)
    workload_inventory_html = workload_inventory.build(ctx)
    recommendations_html = recommendations_tab.build(ctx)
    checklist_html = checklist.build(ctx)
    storage_html = storage.build(ctx)

    tabs_content_html = f'''{overview_html}
        
{nodes_html}
        
{efficiency_html}
        
{workloads_html}
        
        <!-- Workload Inventory Tab -->
        <div class="tab-content" id="workload-inventory">
{workload_inventory_html}
        </div>
        
{recommendations_html}
        
{checklist_html}
        
{storage_html}'''

    return build_layout(ctx, tabs_content_html, ctx.script_body_html)
