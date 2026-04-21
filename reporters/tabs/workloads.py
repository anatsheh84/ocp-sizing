# -*- coding: utf-8 -*-
"""
workloads.py
------------
Workload Distribution tab for the OCP Sizing HTML report.

Shows pod distribution by namespace and per-node, with role filter and
sum-row-aware tables/charts.

Extracted from html_reporter.py in Phase 5d of the refactor.
"""

from reporters.report_context import ReportContext
from reporters.components import role_filter_bar


def build(ctx: ReportContext) -> str:
    """Render the Workload Distribution tab (including its <div class=tab-content> wrapper)."""
    nodes = ctx.nodes
    nodes_json = ctx.nodes_json
    sorted_ns = ctx.sorted_ns
    role_summaries = ctx.role_summaries
    return f'''        <!-- Workloads Tab -->
        <div class="tab-content" id="workloads">
            <div class="section-header">
                <h2 class="section-title">Workload Distribution</h2>
                <p class="section-subtitle">Analysis of pod distribution across namespaces and nodes</p>
            </div>
            
{role_filter_bar(ctx, 'workloadTable')}
            
            <div class="charts-grid" id="workloadCharts">
                <div class="chart-card">
                    <h3 class="chart-title" id="namespaceChartTitle">Pods by Namespace (All {len(sorted_ns)} namespaces)</h3>
                    <div class="chart-container scrollable" id="namespaceChartContainer">
                        <canvas id="namespaceChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title" id="podsPerNodeChartTitle">Pods per Node</h3>
                    <div class="chart-container">
                        <canvas id="podsPerNodeChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-container" style="margin-top: 1.5rem;">
                <div class="table-header">
                    <h3 class="table-title">Pods per Node (<span id="workloadTableCount">{len(nodes)}</span>)</h3>
                </div>
                <div class="table-scroll">
                    <table id="workloadTable">
                        <thead>
                            <tr>
                                <th>Node</th>
                                <th>Role</th>
                                <th>Pod Count</th>
                                <th>Pod Capacity</th>
                                <th>Utilization</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name'].split('.')[0]}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['pod_count']}</td>
                                <td>{n['pod_capacity']}</td>
                                <td>
                                    <div>{round(n['pod_count']/max(n['pod_capacity'],1)*100, 1)}%</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['pod_count']/max(n['pod_capacity'],1)*100, 100)}%"></div>
                                    </div>
                                </td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                        <tfoot id="workloadTableFoot">
                            <tr>
                                <td><strong>&Sigma; Total (Filtered)</strong></td>
                                <td id="sumWlNodeCount">{len(nodes)} nodes</td>
                                <td id="sumWlPodCount">{sum(n['pod_count'] for n in nodes_json)}</td>
                                <td id="sumWlPodCapacity">{sum(n['pod_capacity'] for n in nodes_json)}</td>
                                <td>-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>'''
