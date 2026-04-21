# -*- coding: utf-8 -*-
"""
overview.py
-----------
Overview tab for the OCP Sizing HTML report.

Shows the cluster architecture diagram (tiered view of control-plane,
platform-services, and worker roles), high-level summary cards, and
the three capacity-vs-requested-vs-actual charts (CPU, Memory, Nodes
by Role).

Extracted from html_reporter.py in Phase 5c of the refactor.
"""

from reporters.report_context import ReportContext


def build(ctx: ReportContext) -> str:
    """Render the Overview tab (including its <div class=tab-content> wrapper)."""
    summary = ctx.summary
    role_summaries = ctx.role_summaries
    return f'''        <!-- Overview Tab -->
        <div class="tab-content active" id="overview">
            <div class="section-header">
                <h2 class="section-title">Cluster Overview</h2>
                <p class="section-subtitle">Summary of your Kubernetes cluster resources and utilization</p>
            </div>
            
            <!-- Architecture Diagram -->
            <div class="architecture-diagram">
                <div class="architecture-title">
                    <h3>🏗️ Cluster Architecture</h3>
                    <p>Kubernetes Cluster • {summary.total_nodes} Nodes • {summary.provider or 'Unknown Platform'}</p>
                </div>
                
                <div class="architecture-container">
                    {'<!-- Control Plane Tier -->' if 'control-plane' in role_summaries else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Control Plane Tier</div>
                        <div class="arch-tier-nodes">
                            <div class="arch-node-group control-plane">
                                <div class="icon">🎛️</div>
                                <div class="role">Control Plane</div>
                                <div class="count">{role_summaries.get('control-plane', {'count': 0}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('control-plane', {'cpu': 0}).get('cpu', 0):.0f} vCPU × {role_summaries.get('control-plane', {'memory': 0}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">{', '.join([n['name'] for n in role_summaries.get('control-plane', {'nodes': []}).get('nodes', [])[:3]])}{' +more' if len(role_summaries.get('control-plane', {'nodes': []}).get('nodes', [])) > 3 else ''}</div>
                            </div>
                        </div>
                    </div>
                    ''' if 'control-plane' in role_summaries else ''}
                    
                    {f'<div class="arch-connector-h"></div>' if ('control-plane' in role_summaries and ('infra' in role_summaries or 'storage' in role_summaries)) else ''}
                    
                    {'<!-- Platform Services Tier -->' if ('infra' in role_summaries or 'storage' in role_summaries) else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Platform Services Tier</div>
                        <div class="arch-middle-tier">
                            {f"""
                            <div class="arch-node-group infra">
                                <div class="icon">🔧</div>
                                <div class="role">Infrastructure</div>
                                <div class="count">{role_summaries.get('infra', {}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('infra', {}).get('cpu', 0):.0f} vCPU × {role_summaries.get('infra', {}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">Logging, Monitoring, Router</div>
                            </div>
                            """ if 'infra' in role_summaries else ''}
                            
                            {f"""
                            <div class="arch-node-group storage">
                                <div class="icon">💾</div>
                                <div class="role">Storage (ODF)</div>
                                <div class="count">{role_summaries.get('storage', {}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('storage', {}).get('cpu', 0):.0f} vCPU × {role_summaries.get('storage', {}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">Ceph MON, MDS, OSD</div>
                            </div>
                            """ if 'storage' in role_summaries else ''}
                        </div>
                    </div>
                    ''' if ('infra' in role_summaries or 'storage' in role_summaries) else ''}
                    
                    {f'<div class="arch-connector-h"></div>' if 'worker' in role_summaries and ('infra' in role_summaries or 'storage' in role_summaries or 'control-plane' in role_summaries) else ''}
                    
                    {'<!-- Worker Tier -->' if 'worker' in role_summaries else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Application Workload Tier</div>
                        <div class="arch-tier-nodes">
                            <div class="arch-node-group worker">
                                <div class="icon">⚙️</div>
                                <div class="role">Workers</div>
                                <div class="count">{role_summaries.get('worker', {'count': 0}).get('count', 0)}</div>
                                <div class="specs">Application Workloads</div>
                                <div class="node-names">{', '.join([n['name'] for n in role_summaries.get('worker', {'nodes': []}).get('nodes', [])[:4]])}{f" +{len(role_summaries.get('worker', {'nodes': []}).get('nodes', [])) - 4} more" if len(role_summaries.get('worker', {'nodes': []}).get('nodes', [])) > 4 else ''}</div>
                            </div>
                        </div>
                    </div>
                    ''' if 'worker' in role_summaries else ''}
                </div>
                
                <div class="arch-legend">
                    {'<div class="arch-legend-item"><div class="arch-legend-color cp"></div><span>Control Plane (' + str(role_summaries.get("control-plane", {}).get("count", 0)) + ')</span></div>' if 'control-plane' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color infra"></div><span>Infrastructure (' + str(role_summaries.get("infra", {}).get("count", 0)) + ')</span></div>' if 'infra' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color storage"></div><span>Storage (' + str(role_summaries.get("storage", {}).get("count", 0)) + ')</span></div>' if 'storage' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color worker"></div><span>Workers (' + str(role_summaries.get("worker", {}).get("count", 0)) + ')</span></div>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total Nodes</span>
                        <div class="card-icon nodes">🖥️</div>
                    </div>
                    <div class="card-value">{summary.total_nodes}</div>
                    <div class="card-subtitle">
                        {', '.join([f"{v} {k}" for k, v in sorted(summary.nodes_by_role.items())])}
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">CPU Capacity</span>
                        <div class="card-icon cpu">⚡</div>
                    </div>
                    <div class="card-value">{round(summary.total_capacity.cpu / 1000, 0):.0f}</div>
                    <div class="card-subtitle">vCPU cores total</div>
                    <div class="card-detail">
                        {round(summary.total_allocatable.cpu / 1000, 0):.0f} allocatable
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Memory Capacity</span>
                        <div class="card-icon memory">🧠</div>
                    </div>
                    <div class="card-value">{round(summary.total_capacity.memory / 1024, 0):.0f}</div>
                    <div class="card-subtitle">GiB total</div>
                    <div class="card-detail">
                        {round(summary.total_allocatable.memory / 1024, 0):.0f} GiB allocatable
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Running Pods</span>
                        <div class="card-icon pods">📦</div>
                    </div>
                    <div class="card-value">{summary.total_pods}</div>
                    <div class="card-subtitle">across {len(summary.namespaces)} namespaces</div>
                    <div class="card-detail">
                        Capacity: {summary.total_capacity.pods} pods
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Platform</span>
                        <div class="card-icon storage">☁️</div>
                    </div>
                    <div class="card-value" style="font-size: 1.5rem;">{summary.provider or 'Unknown'}</div>
                    <div class="card-subtitle">{summary.kubernetes_version}</div>
                    <div class="card-detail">
                        {summary.container_runtime.split('://')[0] if summary.container_runtime else 'N/A'}
                    </div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">CPU: Capacity vs Requested vs Actual</h3>
                    <div class="chart-container">
                        <canvas id="cpuOverviewChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Memory: Capacity vs Requested vs Actual</h3>
                    <div class="chart-container">
                        <canvas id="memoryOverviewChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Nodes by Role</h3>
                    <div class="chart-container">
                        <canvas id="nodesByRoleChart"></canvas>
                    </div>
                </div>
            </div>
        </div>'''
