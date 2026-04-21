# -*- coding: utf-8 -*-
"""
nodes.py
--------
Node Inventory tab for the OCP Sizing HTML report.

Detailed per-node table with CPU/memory capacity, requested, actual,
pods, and status. Includes role filter buttons and dynamic sum row.

Extracted from html_reporter.py in Phase 5e of the refactor.
"""

from reporters.report_context import ReportContext


def build(ctx: ReportContext) -> str:
    """Render the Node Inventory tab (including its <div class=tab-content> wrapper)."""
    nodes = ctx.nodes
    nodes_json = ctx.nodes_json
    role_summaries = ctx.role_summaries
    return f'''        <!-- Nodes Tab -->
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
        </div>'''
