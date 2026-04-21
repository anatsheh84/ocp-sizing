# -*- coding: utf-8 -*-
"""
efficiency.py
-------------
Efficiency Analysis tab for the OCP Sizing HTML report.

Shows CPU/Memory request-accuracy and capacity-utilization cards, per-node
efficiency charts, and a Per-Node Efficiency table with dynamic sum row.
Compares requested resources against actual utilization.

Extracted from html_reporter.py in Phase 5f of the refactor.
"""

from reporters.report_context import ReportContext
from reporters.components import role_filter_bar


def build(ctx: ReportContext) -> str:
    """Render the Efficiency Analysis tab (including its <div class=tab-content> wrapper)."""
    summary = ctx.summary
    nodes = ctx.nodes
    nodes_json = ctx.nodes_json
    role_summaries = ctx.role_summaries
    return f'''        <!-- Efficiency Tab -->
        <div class="tab-content" id="efficiency">
            <div class="section-header">
                <h2 class="section-title">Efficiency Analysis</h2>
                <p class="section-subtitle">Compare requested resources against actual utilization to identify optimization opportunities</p>
            </div>
            
{role_filter_bar(ctx, 'efficiencyTable')}
            
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
        </div>'''
