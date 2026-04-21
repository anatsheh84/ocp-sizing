# -*- coding: utf-8 -*-
"""
html_reporter.py
---------------
HTML Report Generation for OCP Sizing Calculator.

Generates interactive Red Hat-branded HTML dashboard with:
- Architecture diagrams
- Resource utilization charts
- Node inventory tables  
- Efficiency analysis
- OCP migration recommendations
"""

import json
from datetime import datetime
from typing import List, Dict
from models import NodeData, ClusterSummary, PersistentVolume


from analyzers.cluster_analyzer import ClusterAnalyzer
from reporters.styles import STYLES
from reporters.scripts import build_script_body
from reporters.report_context import build_context
from reporters.layout import build_layout
from reporters.tabs import workload_inventory
from reporters.tabs import storage
from reporters.tabs import overview
from reporters.tabs import workloads as workloads_tab
from reporters.tabs import nodes as nodes_tab
from reporters.tabs import efficiency
from reporters.tabs import recommendations as recommendations_tab
from reporters.tabs import checklist


def generate_html_report(nodes: List[NodeData], summary: ClusterSummary, 
                        recommendations: Dict, pvs: List[PersistentVolume],
                        include_recommendations: bool = True,
                        workloads: Dict = None) -> str:
    """Generate interactive HTML dashboard"""
    
    # Build typed view-model (Phase 3: ReportContext).
    # The main f-string below still references the old local names;
    # Phase 5 will migrate those to ctx.X as each tab module is extracted.
    ctx = build_context(nodes, summary, recommendations, pvs,
                        include_recommendations=include_recommendations,
                        workloads=workloads)
    nodes_json = ctx.nodes_json
    namespace_pods = ctx.namespace_pods
    sorted_ns = ctx.sorted_ns
    pvs_json = ctx.pvs_json
    nodes_by_role = ctx.nodes_by_role
    role_summaries = ctx.role_summaries
    workload_inventory_html = workload_inventory.build(ctx)
    storage_html = storage.build(ctx)
    overview_html = overview.build(ctx)
    workloads_html = workloads_tab.build(ctx)
    nodes_html = nodes_tab.build(ctx)
    efficiency_html = efficiency.build(ctx)
    recommendations_html = recommendations_tab.build(ctx)
    checklist_html = checklist.build(ctx)
    script_body_html = ctx.script_body_html
    
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
    html = build_layout(ctx, tabs_content_html, script_body_html)
    
    return html


# =============================================================================
# Main Function
# =============================================================================

