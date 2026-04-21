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
    script_body_html = ctx.script_body_html
    
    tabs_content_html = f'''{overview_html}
        
        <!-- Nodes Tab -->
        <div class="tab-content" id="nodes">
            <div class="section-header">
                <h2 class="section-title">Node Inventory</h2>
                <p class="section-subtitle">Detailed view of all cluster nodes with resource allocation</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="nodesTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="nodesTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="nodesTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="nodesTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="nodesTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="export-buttons">
                <button class="btn btn-primary" onclick="exportTableToCSV('nodesTable', 'nodes_inventory.csv')">
                    📥 Export CSV
                </button>
            </div>
            
            <div class="table-container">
                <div class="table-header">
                    <input type="text" class="table-search" placeholder="Search nodes..." onkeyup="filterTable('nodesTable', this.value)">
                </div>
                <div class="table-scroll">
                    <table id="nodesTable">
                        <thead>
                            <tr>
                                <th onclick="sortTable('nodesTable', 0)">Node Name</th>
                                <th onclick="sortTable('nodesTable', 1)">Role</th>
                                <th onclick="sortTable('nodesTable', 2)">CPU Capacity (cores)</th>
                                <th onclick="sortTable('nodesTable', 3)">CPU Requested</th>
                                <th onclick="sortTable('nodesTable', 4)">CPU Used</th>
                                <th onclick="sortTable('nodesTable', 5)">Memory Capacity (GiB)</th>
                                <th onclick="sortTable('nodesTable', 6)">Mem Requested</th>
                                <th onclick="sortTable('nodesTable', 7)">Memory Used</th>
                                <th onclick="sortTable('nodesTable', 8)">Pods</th>
                                <th onclick="sortTable('nodesTable', 9)">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name']}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['cpu_capacity']}</td>
                                <td>
                                    <div>{n['cpu_requested']} ({n['cpu_req_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill {'progress-high' if n['cpu_req_pct'] > 80 else 'progress-medium' if n['cpu_req_pct'] > 50 else 'progress-low'}" style="width: {min(n['cpu_req_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>
                                    <div>{n['cpu_actual']} ({n['cpu_actual_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['cpu_actual_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>{n['mem_capacity']}</td>
                                <td>
                                    <div>{n['mem_requested']} ({n['mem_req_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill {'progress-high' if n['mem_req_pct'] > 80 else 'progress-medium' if n['mem_req_pct'] > 50 else 'progress-low'}" style="width: {min(n['mem_req_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>
                                    <div>{n['mem_actual']} ({n['mem_actual_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['mem_actual_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>{n['pod_count']}/{n['pod_capacity']}</td>
                                <td><span class="badge {'badge-success' if n['is_ready'] else 'badge-danger'}">{'Ready' if n['is_ready'] else 'Not Ready'}</span></td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                        <tfoot>
                            <tr id="nodesTableSumRow">
                                <td>Σ Total (Filtered)</td>
                                <td id="sumNodeCount">{len(nodes)} nodes</td>
                                <td id="sumCpuCores">{sum(n['cpu_capacity'] for n in nodes_json):.1f}</td>
                                <td id="sumCpuRequested">{sum(n['cpu_requested'] for n in nodes_json):.2f}</td>
                                <td id="sumCpuActual">{sum(n['cpu_actual'] for n in nodes_json):.2f}</td>
                                <td id="sumMemCapacity">{sum(n['mem_capacity'] for n in nodes_json):.1f}</td>
                                <td id="sumMemRequested">{sum(n['mem_requested'] for n in nodes_json):.1f}</td>
                                <td id="sumMemActual">{sum(n['mem_actual'] for n in nodes_json):.1f}</td>
                                <td id="sumPods">{sum(n['pod_count'] for n in nodes_json)}</td>
                                <td>-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Efficiency Tab -->
        <div class="tab-content" id="efficiency">
            <div class="section-header">
                <h2 class="section-title">Efficiency Analysis</h2>
                <p class="section-subtitle">Compare requested resources against actual utilization to identify optimization opportunities</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="efficiencyTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="efficiencyTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="efficiencyTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="efficiencyTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="efficiencyTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="summary-grid" id="efficiencyCards">
                <div class="summary-card" id="cpuRequestAccuracyCard">
                    <div class="card-header">
                        <span class="card-title">CPU Request Accuracy</span>
                        <div class="card-icon cpu">📊</div>
                    </div>
                    <div class="card-value {'text-success' if summary.total_actual.cpu <= summary.total_requested.cpu else 'text-danger'}" id="cpuRequestAccuracyValue">{round(summary.total_actual.cpu / max(summary.total_requested.cpu, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle" id="cpuRequestAccuracySubtitle">{'of requested CPU is being used' if summary.total_actual.cpu <= summary.total_requested.cpu else 'of requested CPU is being used (over limit!)'}</div>
                    <div class="card-detail" id="cpuRequestAccuracyDetail">
                        {round(summary.total_requested.cpu / 1000, 1)} cores requested, {round(summary.total_actual.cpu / 1000, 1)} actually used
                    </div>
                    <div class="card-advice {'advice-success' if summary.total_actual.cpu <= summary.total_requested.cpu else 'advice-danger'}" id="cpuRequestAccuracyAdvice">
                        {'💡 Requests well-sized or over-provisioned' if summary.total_actual.cpu <= summary.total_requested.cpu else '⚠️ Usage exceeds requests - set proper limits!'}
                    </div>
                    <div class="filter-indicator hidden" id="cpuRequestAccuracyFilter"></div>
                </div>
                
                <div class="summary-card" id="memRequestAccuracyCard">
                    <div class="card-header">
                        <span class="card-title">Memory Request Accuracy</span>
                        <div class="card-icon memory">📊</div>
                    </div>
                    <div class="card-value {'text-success' if summary.total_actual.memory <= summary.total_requested.memory else 'text-danger'}" id="memRequestAccuracyValue">{round(summary.total_actual.memory / max(summary.total_requested.memory, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle" id="memRequestAccuracySubtitle">{'of requested memory is being used' if summary.total_actual.memory <= summary.total_requested.memory else 'of requested memory is being used (over limit!)'}</div>
                    <div class="card-detail" id="memRequestAccuracyDetail">
                        {round(summary.total_requested.memory / 1024, 1)} GiB requested, {round(summary.total_actual.memory / 1024, 1)} GiB actually used
                    </div>
                    <div class="card-advice {'advice-success' if summary.total_actual.memory <= summary.total_requested.memory else 'advice-danger'}" id="memRequestAccuracyAdvice">
                        {'💡 Requests well-sized or over-provisioned' if summary.total_actual.memory <= summary.total_requested.memory else '⚠️ Usage exceeds requests - set proper limits!'}
                    </div>
                    <div class="filter-indicator hidden" id="memRequestAccuracyFilter"></div>
                </div>
                
                <div class="summary-card" id="cpuCapacityCard">
                    <div class="card-header">
                        <span class="card-title">CPU Capacity Utilization</span>
                        <div class="card-icon cpu">📈</div>
                    </div>
                    <div class="card-value" id="cpuCapacityValue">{round(summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of total CPU capacity is being used</div>
                    <div class="card-detail" id="cpuCapacityDetail">
                        {round(summary.total_capacity.cpu / 1000, 0)} cores capacity, {round(summary.total_actual.cpu / 1000, 1)} actually used
                    </div>
                    <div class="card-advice advice-info" id="cpuCapacityAdvice">
                        {'ℹ️ Low utilization - room to grow' if summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) < 0.5 else '⚡ Moderate utilization' if summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) < 0.8 else '🔥 High utilization - consider scaling'}
                    </div>
                    <div class="filter-indicator hidden" id="cpuCapacityFilter"></div>
                </div>
                
                <div class="summary-card" id="memCapacityCard">
                    <div class="card-header">
                        <span class="card-title">Memory Capacity Utilization</span>
                        <div class="card-icon memory">📈</div>
                    </div>
                    <div class="card-value" id="memCapacityValue">{round(summary.total_actual.memory / max(summary.total_capacity.memory, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of total memory capacity is being used</div>
                    <div class="card-detail" id="memCapacityDetail">
                        {round(summary.total_capacity.memory / 1024, 0)} GiB capacity, {round(summary.total_actual.memory / 1024, 1)} GiB actually used
                    </div>
                    <div class="card-advice advice-info" id="memCapacityAdvice">
                        {'ℹ️ Low utilization - room to grow' if summary.total_actual.memory / max(summary.total_capacity.memory, 1) < 0.5 else '⚡ Moderate utilization' if summary.total_actual.memory / max(summary.total_capacity.memory, 1) < 0.8 else '🔥 High utilization - consider scaling'}
                    </div>
                    <div class="filter-indicator hidden" id="memCapacityFilter"></div>
                </div>
            </div>
            
            <div class="charts-grid" id="efficiencyCharts">
                <div class="chart-card">
                    <h3 class="chart-title" id="cpuChartTitle">CPU: Requested vs Actual per Node</h3>
                    <div class="chart-container">
                        <canvas id="cpuEfficiencyChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title" id="memChartTitle">Memory: Requested vs Actual per Node</h3>
                    <div class="chart-container">
                        <canvas id="memoryEfficiencyChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-container" style="margin-top: 1.5rem;">
                <div class="table-header">
                    <h3 class="table-title">Per-Node Efficiency Details (<span id="efficiencyTableCount">{len(nodes)}</span>)</h3>
                </div>
                <div class="table-scroll">
                    <table id="efficiencyTable">
                        <thead>
                            <tr>
                                <th>Node</th>
                                <th>Role</th>
                                <th>CPU Requested</th>
                                <th>CPU Actual</th>
                                <th>CPU Efficiency</th>
                                <th>Memory Requested</th>
                                <th>Memory Actual</th>
                                <th>Memory Efficiency</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name'].split('.')[0]}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['cpu_requested']} cores</td>
                                <td>{n['cpu_actual']} cores</td>
                                <td>
                                    <span class="badge {'badge-danger' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 20 else 'badge-warning' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 50 else 'badge-success' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 <= 100 else 'badge-warning' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 <= 150 else 'badge-danger'}">
                                        {round(n['cpu_actual']/max(n['cpu_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                                <td>{n['mem_requested']} GiB</td>
                                <td>{n['mem_actual']} GiB</td>
                                <td>
                                    <span class="badge {'badge-danger' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 20 else 'badge-warning' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 50 else 'badge-success' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 <= 100 else 'badge-warning' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 <= 150 else 'badge-danger'}">
                                        {round(n['mem_actual']/max(n['mem_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                        <tfoot id="efficiencyTableFoot">
                            <tr>
                                <td><strong>&Sigma; Total (Filtered)</strong></td>
                                <td id="sumEffNodeCount">{len(nodes)} nodes</td>
                                <td id="sumEffCpuReq">{sum(n['cpu_requested'] for n in nodes_json):.2f} cores</td>
                                <td id="sumEffCpuActual">{sum(n['cpu_actual'] for n in nodes_json):.2f} cores</td>
                                <td>-</td>
                                <td id="sumEffMemReq">{sum(n['mem_requested'] for n in nodes_json):.1f} GiB</td>
                                <td id="sumEffMemActual">{sum(n['mem_actual'] for n in nodes_json):.1f} GiB</td>
                                <td>-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
        
{workloads_html}
        
        <!-- Workload Inventory Tab -->
        <div class="tab-content" id="workload-inventory">
{workload_inventory_html}
        </div>
        
        <!-- Recommendations Tab -->
        {'<div class="tab-content" id="recommendations">' if include_recommendations else '<!--'}
            <div class="section-header">
                <h2 class="section-title">OpenShift Sizing Recommendations</h2>
                <p class="section-subtitle">Recommended node configurations for OpenShift based on your current workload</p>
            </div>
            
            <div class="recommendations-grid">
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(0,102,204,0.2); color: var(--rh-blue);">🎛️</div>
                        <div>
                            <h3 class="rec-card-title">Control Plane</h3>
                            <span class="badge badge-info">master nodes</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['control_plane']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['control_plane']['current_cpu']:.0f} vCPU × {recommendations['control_plane']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['control_plane']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['control_plane']['recommended_cpu']} vCPU × {recommendations['control_plane']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["control_plane"]["notes"]]) + '</div>' if recommendations["control_plane"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(103,83,172,0.2); color: var(--rh-purple);">🔧</div>
                        <div>
                            <h3 class="rec-card-title">Infrastructure</h3>
                            <span class="badge badge-info">logging, monitoring, router</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['infra']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['infra']['current_cpu']:.0f} vCPU × {recommendations['infra']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['infra']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['infra']['recommended_cpu']} vCPU × {recommendations['infra']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["infra"]["notes"]]) + '</div>' if recommendations["infra"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(0,149,150,0.2); color: var(--rh-cyan);">💾</div>
                        <div>
                            <h3 class="rec-card-title">Storage (ODF)</h3>
                            <span class="badge badge-info">OpenShift Data Foundation</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['storage']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['storage']['current_cpu']:.0f} vCPU × {recommendations['storage']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['storage']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['storage']['recommended_cpu']} vCPU × {recommendations['storage']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["storage"]["notes"]]) + '</div>' if recommendations["storage"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(240,171,0,0.2); color: var(--rh-orange);">⚙️</div>
                        <div>
                            <h3 class="rec-card-title">Worker Nodes</h3>
                            <span class="badge badge-info">application workloads</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['worker']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['worker']['current_cpu']:.0f} vCPU total
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Optimized</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['worker']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['worker']['recommended_cpu']} vCPU × {recommendations['worker']['recommended_memory']/1024:.0f} GiB each
                            </div>
                        </div>
                    </div>
                    <div class="rec-notes">
                        <div class="rec-note">
                            <span class="rec-note-icon">📊</span>
                            Actual CPU used: {recommendations['worker']['actual_cpu_used']:.1f} cores | Memory used: {recommendations['worker']['actual_memory_used']/1024:.1f} GiB
                        </div>
                        {''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["worker"]["notes"]])}
                    </div>
                </div>
            </div>
            
            {f'''
            <div class="opportunities-section">
                <h3 class="opportunities-title">💡 Optimization Opportunities</h3>
                {"".join([f'<div class="opportunity-item"><span>✅</span><span>{opp}</span></div>' for opp in recommendations["overall"]["opportunities"]])}
            </div>
            ''' if recommendations["overall"]["opportunities"] else ''}
            
            {f'''
            <div class="warnings-section">
                <h3 class="warnings-title">⚠️ Warnings</h3>
                {"".join([f'<div class="warning-item"><span class="warning-icon">⚠️</span><span>{warn}</span></div>' for warn in recommendations["overall"]["warnings"]])}
            </div>
            ''' if recommendations["overall"]["warnings"] else ''}
        {'</div>' if include_recommendations else '-->'}
        
        {'<!-- Checklist Tab -->' if include_recommendations else '<!--'}
        {'<div class="tab-content" id="checklist">' if include_recommendations else ''}
            <div class="section-header">
                <h2 class="section-title">Migration Checklist</h2>
                <p class="section-subtitle">Pre-migration compatibility checks and considerations</p>
            </div>
            
            <div class="recommendations-grid">
                <div class="checklist">
                    <h3 class="checklist-title">Platform Compatibility</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else 'warn'}">
                            {'✓' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else '!'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Kubernetes Version</div>
                            <div class="check-detail">{summary.kubernetes_version} - {'Compatible with OCP 4.14+' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else 'Check OCP version compatibility'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if 'cri-o' in summary.container_runtime.lower() else 'info'}">
                            {'✓' if 'cri-o' in summary.container_runtime.lower() else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Container Runtime</div>
                            <div class="check-detail">{summary.container_runtime} - {'Already using CRI-O' if 'cri-o' in summary.container_runtime.lower() else 'OCP uses CRI-O, verify image compatibility'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon pass">✓</div>
                        <div class="check-text">
                            <div class="check-label">Infrastructure Provider</div>
                            <div class="check-detail">{summary.provider} - Supported platform for OpenShift</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else 'warn'}">
                            {'✓' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else '!'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Version Consistency</div>
                            <div class="check-detail">{'All nodes running same kubelet version' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else 'Mixed versions detected - standardize before migration'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Resource Considerations</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if recommendations['control_plane']['current_count'] >= 3 else 'warn' if recommendations['control_plane']['current_count'] > 0 else 'info'}">
                            {'✓' if recommendations['control_plane']['current_count'] >= 3 else '!' if recommendations['control_plane']['current_count'] > 0 else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Control Plane HA</div>
                            <div class="check-detail">{recommendations['control_plane']['current_count']} master nodes - {'HA configuration' if recommendations['control_plane']['current_count'] >= 3 else 'Single Node or compact cluster' if recommendations['control_plane']['current_count'] == 1 else 'Recommend 3 for HA'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if recommendations['infra']['current_count'] >= 3 else 'warn' if recommendations['infra']['current_count'] > 0 else 'info'}">
                            {'✓' if recommendations['infra']['current_count'] >= 3 else '!' if recommendations['infra']['current_count'] > 0 else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Infrastructure Nodes</div>
                            <div class="check-detail">{recommendations['infra']['current_count']} infra nodes - {'Good for OCP monitoring/logging' if recommendations['infra']['current_count'] >= 3 else 'Consider dedicated infra nodes for larger clusters' if recommendations['infra']['current_count'] == 0 else 'Consider adding more for HA'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'warn' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else 'pass'}">
                            {'!' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else '✓'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Resource Efficiency</div>
                            <div class="check-detail">{recommendations['overall']['efficiency_score']}% efficiency - {'Significant right-sizing opportunity' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else 'Good utilization'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Network Plugin</div>
                            <div class="check-detail">OCP uses OVN-Kubernetes by default - verify network policy compatibility</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Workload Analysis</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon pass">✓</div>
                        <div class="check-text">
                            <div class="check-label">Total Pods</div>
                            <div class="check-detail">{summary.total_pods} pods across {len(summary.namespaces)} namespaces</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Node Taints</div>
                            <div class="check-detail">{len([n for n in nodes_json if n['taints'] != 'None'])} nodes have taints - verify tolerations for OCP workloads</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Security Contexts</div>
                            <div class="check-detail">Review pod security policies - OCP uses Security Context Constraints (SCCs)</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Storage Classes</div>
                            <div class="check-detail">Map existing storage classes to OCP storage provisioners</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Pre-Migration Tasks</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Export YAML Manifests</div>
                            <div class="check-detail">Export deployments, services, configmaps, secrets for migration</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Image Registry</div>
                            <div class="check-detail">Plan container image migration strategy to OCP internal registry</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Persistent Data</div>
                            <div class="check-detail">Plan PV/PVC migration and data backup strategy</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">DNS/Ingress</div>
                            <div class="check-detail">Plan Route migration from Ingress resources</div>
                        </div>
                    </div>
                </div>
            </div>
        {'</div>' if include_recommendations else '-->'}
        
{storage_html}'''
    html = build_layout(ctx, tabs_content_html, script_body_html)
    
    return html


# =============================================================================
# Main Function
# =============================================================================

