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


def _generate_workload_inventory_tab(workloads):
    """Generate the Workload Inventory tab HTML with filters and dynamic cards."""
    if not workloads or not workloads.get('has_workload_data'):
        return '''
            <div class="section-header">
                <h2 class="section-title">Workload Inventory</h2>
                <p class="section-subtitle">No pod data available</p>
            </div>'''
    
    import json as _json
    stats = workloads['stats']
    wl_list = workloads['workload_list']
    ns_list = workloads['namespace_list']
    has_actual = workloads.get('has_actual_usage', False)
    
    wl_json = _json.dumps([{
        'namespace': w['namespace'], 'name': w['name'],
        'replicas': w['replicas'], 'node_count': w['node_count'],
        'nodes': [n.split('.')[0] for n in w['nodes'][:4]] + (['...'] if len(w['nodes']) > 4 else []),
        'is_system': w['is_system'],
        'has_cpu_requests': w['has_cpu_requests'], 'has_mem_requests': w['has_mem_requests'],
        'total_cpu_requests_mcpu': w['total_cpu_requests_mcpu'],
        'total_mem_requests_mb': w['total_mem_requests_mb'],
        'total_actual_cpu_mcpu': w.get('total_actual_cpu_mcpu', 0),
        'total_actual_mem_mb': w.get('total_actual_mem_mb', 0),
        'has_actual': w.get('has_actual', False),
    } for w in wl_list])
    ns_json = _json.dumps(ns_list)
    has_actual_js = 'true' if has_actual else 'false'
    
    ns_options = '<option value="all">All Namespaces</option>'
    for ns in ns_list:
        ns_options += f'<option value="{ns["namespace"]}">{ns["namespace"]}</option>'
    
    # Actual usage card values
    act_cpu_display = '%.1f' % (stats.get('total_actual_cpu_mcpu', 0) / 1000) if has_actual else 'N/A'
    act_mem_display = '%.1f' % (stats.get('total_actual_mem_mb', 0) / 1024) if has_actual else 'N/A'
    act_cpu_detail = '%.2f app &middot; %.2f sys' % (
        stats.get('app_actual_cpu_mcpu', 0) / 1000,
        stats.get('sys_actual_cpu_mcpu', 0) / 1000) if has_actual else 'Upload pods-top.txt'
    act_mem_detail = '%.1f app &middot; %.1f sys' % (
        stats.get('app_actual_mem_mb', 0) / 1024,
        stats.get('sys_actual_mem_mb', 0) / 1024) if has_actual else 'Upload pods-top.txt'
    
    # Extra columns for actual usage
    actual_th = '<th>Actual CPU</th><th>Actual Memory</th>' if has_actual else ''

    html = f'''
            <div class="section-header">
                <h2 class="section-title">Workload Inventory</h2>
                <p class="section-subtitle">Unique workloads, replica analysis, and resource request coverage</p>
            </div>
            <div class="filter-bar">
                <span class="filter-label">Filter:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterWorkloads(this, \'all\')">All <span class="filter-count">{stats['total_workloads']}</span></button>
                    <button class="filter-btn worker" onclick="filterWorkloads(this, \'app\')">App <span class="filter-count">{stats['app_workloads']}</span></button>
                    <button class="filter-btn control-plane" onclick="filterWorkloads(this, \'system\')">System <span class="filter-count">{stats['system_workloads']}</span></button>
                </div>
                <select id="wl-ns-filter" onchange="filterWorkloads(null, null)" style="margin-left:auto; padding:6px 10px; border-radius:6px; border:1px solid var(--rh-gray-600); background:var(--rh-gray-800); color:var(--rh-white); font-size:0.82rem;">
                    {ns_options}
                </select>
            </div>
            <div class="stat-cards-grid" id="wl-stat-cards">
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-pods">{stats['total_pods']}</div><div class="stat-mini-label">Total Pods</div><div class="stat-mini-detail" id="wl-card-pods-detail">{stats['app_pods']} app &middot; {stats['system_pods']} system</div></div>
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-workloads">{stats['total_workloads']}</div><div class="stat-mini-label">Unique Workloads</div><div class="stat-mini-detail" id="wl-card-wl-detail">{stats['app_workloads']} app &middot; {stats['system_workloads']} system</div></div>
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-multi">{stats['multi_replica']}</div><div class="stat-mini-label">Multi-Replica</div><div class="stat-mini-detail" id="wl-card-single">{stats['single_replica']} single-replica</div></div>
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-ns">{stats['namespaces']}</div><div class="stat-mini-label">Namespaces</div><div class="stat-mini-detail">Across all nodes</div></div>
                <div class="stat-card-mini" id="wl-card-cpu-wrap"><div class="stat-mini-value" id="wl-card-cpu">{stats['app_cpu_req_coverage_pct']}%</div><div class="stat-mini-label">CPU Requests Set</div><div class="stat-mini-detail" id="wl-card-cpu-detail">{stats['cpu_req_coverage_pct']}% overall</div></div>
                <div class="stat-card-mini" id="wl-card-mem-wrap"><div class="stat-mini-value" id="wl-card-mem">{stats['app_mem_req_coverage_pct']}%</div><div class="stat-mini-label">Mem Requests Set</div><div class="stat-mini-detail" id="wl-card-mem-detail">{stats['mem_req_coverage_pct']}% overall</div></div>
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-act-cpu">{act_cpu_display}</div><div class="stat-mini-label">Actual CPU (cores)</div><div class="stat-mini-detail" id="wl-card-act-cpu-detail">{act_cpu_detail}</div></div>
                <div class="stat-card-mini"><div class="stat-mini-value" id="wl-card-act-mem">{act_mem_display}</div><div class="stat-mini-label">Actual Memory (GiB)</div><div class="stat-mini-detail" id="wl-card-act-mem-detail">{act_mem_detail}</div></div>
            </div>
            <div class="table-container" style="margin-top:1.5rem;"><div class="table-header"><h3 class="table-title">Workloads (<span id="wl-table-count">{len(wl_list)}</span> unique)</h3></div>
                <div class="table-scroll"><table><thead><tr><th>Namespace</th><th>Workload</th><th>Type</th><th style="text-align:center">Replicas</th><th>Spread</th><th>CPU Requests</th><th>Mem Requests</th>{actual_th}<th>Nodes</th></tr></thead><tbody id="wl-table-body"></tbody><tfoot id="wl-table-foot"></tfoot></table></div></div>
            <div class="table-container" style="margin-top:1.5rem;"><div class="table-header"><h3 class="table-title">Namespace Summary (<span id="wl-ns-count">{len(ns_list)}</span>)</h3></div>
                <div class="table-scroll"><table><thead><tr><th>Namespace</th><th>Type</th><th style="text-align:center">Pods</th><th style="text-align:center">Unique Workloads</th></tr></thead><tbody id="wl-ns-body"></tbody><tfoot id="wl-ns-foot"></tfoot></table></div></div>
'''

    html += '''<script>
var _wlData = ''' + wl_json + ''';
var _nsData = ''' + ns_json + ''';
var _hasActual = ''' + has_actual_js + ''';
var _wlTypeFilter = 'all';
function filterWorkloads(btn, typeF) {
    if (typeF !== null) _wlTypeFilter = typeF;
    var tf = _wlTypeFilter;
    var nsF = document.getElementById('wl-ns-filter').value;
    if (btn) {
        document.querySelectorAll('#workload-inventory .filter-btn').forEach(function(b){ b.classList.remove('active'); });
        btn.classList.add('active');
    }
    var f = _wlData.filter(function(w) {
        if (tf === 'app' && w.is_system) return false;
        if (tf === 'system' && !w.is_system) return false;
        if (nsF !== 'all' && w.namespace !== nsF) return false;
        return true;
    });
    var fNs = _nsData.filter(function(ns) {
        if (tf === 'app' && ns.is_system) return false;
        if (tf === 'system' && !ns.is_system) return false;
        if (nsF !== 'all' && ns.namespace !== nsF) return false;
        return true;
    });
    // Stats
    var tp=f.reduce(function(s,w){return s+w.replicas;},0);
    var aw=f.filter(function(w){return !w.is_system;});
    var sw=f.filter(function(w){return w.is_system;});
    var ap=aw.reduce(function(s,w){return s+w.replicas;},0);
    var sp=sw.reduce(function(s,w){return s+w.replicas;},0);
    var mr=f.filter(function(w){return w.replicas>1;}).length;
    var sr=f.filter(function(w){return w.replicas===1;}).length;
    var wc=f.filter(function(w){return w.has_cpu_requests;}).length;
    var wm=f.filter(function(w){return w.has_mem_requests;}).length;
    var cpPct=f.length>0?Math.round(wc/f.length*100):0;
    var mpPct=f.length>0?Math.round(wm/f.length*100):0;
    // Actual usage sums
    var actCpu=f.reduce(function(s,w){return s+w.total_actual_cpu_mcpu;},0);
    var actMem=f.reduce(function(s,w){return s+w.total_actual_mem_mb;},0);
    var appActCpu=aw.reduce(function(s,w){return s+w.total_actual_cpu_mcpu;},0);
    var appActMem=aw.reduce(function(s,w){return s+w.total_actual_mem_mb;},0);
    var sysActCpu=sw.reduce(function(s,w){return s+w.total_actual_cpu_mcpu;},0);
    var sysActMem=sw.reduce(function(s,w){return s+w.total_actual_mem_mb;},0);
    // Update cards
    document.getElementById('wl-card-pods').textContent=tp;
    document.getElementById('wl-card-pods-detail').textContent=ap+' app \\u00b7 '+sp+' system';
    document.getElementById('wl-card-workloads').textContent=f.length;
    document.getElementById('wl-card-wl-detail').textContent=aw.length+' app \\u00b7 '+sw.length+' system';
    document.getElementById('wl-card-multi').textContent=mr;
    document.getElementById('wl-card-single').textContent=sr+' single-replica';
    document.getElementById('wl-card-ns').textContent=fNs.length;
    document.getElementById('wl-card-cpu').textContent=cpPct+'%';
    document.getElementById('wl-card-mem').textContent=mpPct+'%';
    document.getElementById('wl-card-cpu-wrap').className='stat-card-mini'+(cpPct<50?' warn-card':'');
    document.getElementById('wl-card-mem-wrap').className='stat-card-mini'+(mpPct<50?' warn-card':'');
    if (_hasActual) {
        document.getElementById('wl-card-act-cpu').textContent=(actCpu/1000).toFixed(1);
        document.getElementById('wl-card-act-cpu-detail').textContent=(appActCpu/1000).toFixed(2)+' app \\u00b7 '+(sysActCpu/1000).toFixed(2)+' sys';
        document.getElementById('wl-card-act-mem').textContent=(actMem/1024).toFixed(1);
        document.getElementById('wl-card-act-mem-detail').textContent=(appActMem/1024).toFixed(1)+' app \\u00b7 '+(sysActMem/1024).toFixed(1)+' sys';
    }
    // Render workload table
    var sumReqCpu=0, sumReqMem=0, sumActCpu=0, sumActMem=0, sumPods=0;
    var tb=document.getElementById('wl-table-body'); tb.innerHTML='';
    f.forEach(function(w){
        var bg=w.is_system?'role-badge role-control-plane':'role-badge role-worker';
        var tl=w.is_system?'System':'App';
        var cd=w.total_cpu_requests_mcpu>0?(w.total_cpu_requests_mcpu/1000).toFixed(2)+' cores':'\\u26a0 Not set';
        var md=w.total_mem_requests_mb>0?(w.total_mem_requests_mb/1024).toFixed(1)+' GB':'\\u26a0 Not set';
        var cc=w.has_cpu_requests?'':' class="text-warning"';
        var mc=w.has_mem_requests?'':' class="text-warning"';
        var sp2=w.node_count>1?w.node_count+' nodes':'1 node';
        sumReqCpu+=w.total_cpu_requests_mcpu;
        sumReqMem+=w.total_mem_requests_mb;
        sumActCpu+=w.total_actual_cpu_mcpu;
        sumActMem+=w.total_actual_mem_mb;
        sumPods+=w.replicas;
        var actCols='';
        if (_hasActual) {
            var acD=w.has_actual?(w.total_actual_cpu_mcpu/1000).toFixed(2)+' cores':'-';
            var amD=w.has_actual?(w.total_actual_mem_mb/1024).toFixed(1)+' GB':'-';
            actCols='<td style="text-align:center">'+acD+'</td><td style="text-align:center">'+amD+'</td>';
        }
        var tr=document.createElement('tr');
        tr.innerHTML='<td>'+w.namespace+'</td><td><strong>'+w.name+'</strong></td><td><span class="'+bg+'">'+tl+'</span></td><td style="text-align:center"><strong>'+w.replicas+'</strong></td><td>'+sp2+'</td><td'+cc+'>'+cd+'</td><td'+mc+'>'+md+'</td>'+actCols+'<td style="font-size:0.78em;color:#888">'+w.nodes.join(', ')+'</td>';
        tb.appendChild(tr);
    });
    document.getElementById('wl-table-count').textContent=f.length;
    // Sum row
    var ft=document.getElementById('wl-table-foot'); ft.innerHTML='';
    var ftr=document.createElement('tr');
    var actFoot=_hasActual?'<td style="text-align:center"><strong>'+(sumActCpu/1000).toFixed(2)+' cores</strong></td><td style="text-align:center"><strong>'+(sumActMem/1024).toFixed(1)+' GB</strong></td>':'';
    ftr.innerHTML='<td><strong>\\u03a3 Total (Filtered)</strong></td><td>'+f.length+' workloads</td><td>-</td><td style="text-align:center"><strong>'+sumPods+'</strong></td><td>-</td><td><strong>'+(sumReqCpu/1000).toFixed(2)+' cores</strong></td><td><strong>'+(sumReqMem/1024).toFixed(1)+' GB</strong></td>'+actFoot+'<td>-</td>';
    ft.appendChild(ftr);
    // Render namespace table
    var nb=document.getElementById('wl-ns-body'); nb.innerHTML='';
    var nsPods=0, nsWl=0;
    fNs.forEach(function(ns){
        var bg=ns.is_system?'role-badge role-control-plane':'role-badge role-worker';
        var tl=ns.is_system?'System':'App';
        var tr=document.createElement('tr');
        tr.innerHTML='<td><strong>'+ns.namespace+'</strong></td><td><span class="'+bg+'">'+tl+'</span></td><td style="text-align:center">'+ns.pod_count+'</td><td style="text-align:center">'+ns.workload_count+'</td>';
        nb.appendChild(tr);
        nsPods+=ns.pod_count; nsWl+=ns.workload_count;
    });
    document.getElementById('wl-ns-count').textContent=fNs.length;
    var nsft=document.getElementById('wl-ns-foot'); nsft.innerHTML='';
    var nsftr=document.createElement('tr');
    nsftr.innerHTML='<td><strong>\\u03a3 Total (Filtered)</strong></td><td>'+fNs.length+' namespaces</td><td style="text-align:center"><strong>'+nsPods+'</strong></td><td style="text-align:center"><strong>'+nsWl+'</strong></td>';
    nsft.appendChild(nsftr);
}
document.addEventListener('DOMContentLoaded',function(){filterWorkloads(document.querySelector('#workload-inventory .filter-btn'),'all');});
</script>'''
    
    return html



def generate_html_report(nodes: List[NodeData], summary: ClusterSummary, 
                        recommendations: Dict, pvs: List[PersistentVolume],
                        include_recommendations: bool = True,
                        workloads: Dict = None) -> str:
    """Generate interactive HTML dashboard"""
    
    # Prepare data for charts
    nodes_json = []
    for node in nodes:
        role = ClusterAnalyzer.categorize_node_role(node)
        cpu_req_pct = (node.allocated_requests.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_req_pct = (node.allocated_requests.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        cpu_actual_pct = (node.actual_usage.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_actual_pct = (node.actual_usage.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        
        nodes_json.append({
            'name': node.name,
            'role': role,
            'roles': ', '.join(node.roles),
            'cpu_capacity': round(node.capacity.cpu / 1000, 1),
            'cpu_allocatable': round(node.allocatable.cpu / 1000, 1),
            'cpu_requested': round(node.allocated_requests.cpu / 1000, 2),
            'cpu_actual': round(node.actual_usage.cpu / 1000, 2),
            'cpu_req_pct': round(cpu_req_pct, 1),
            'cpu_actual_pct': round(cpu_actual_pct, 1),
            'mem_capacity': round(node.capacity.memory / 1024, 1),
            'mem_allocatable': round(node.allocatable.memory / 1024, 1),
            'mem_requested': round(node.allocated_requests.memory / 1024, 1),
            'mem_actual': round(node.actual_usage.memory / 1024, 1),
            'mem_req_pct': round(mem_req_pct, 1),
            'mem_actual_pct': round(mem_actual_pct, 1),
            'pod_count': node.pod_count,
            'pod_capacity': node.capacity.pods,
            'is_ready': node.is_ready,
            'is_schedulable': node.is_schedulable,
            'taints': ', '.join(node.taints) if node.taints else 'None',
            'instance_type': node.instance_type or 'N/A',
            'ip_address': node.ip_address,
            'kubelet_version': node.system_info.kubelet_version,
            'os_image': node.system_info.os_image,
            'container_runtime': node.system_info.container_runtime,
            'pods': [{'namespace': p.namespace, 'name': p.name} for p in node.pods]
        })
    
    # Namespace pod distribution - ALL namespaces
    namespace_pods = {}
    for node in nodes:
        for pod in node.pods:
            ns = pod.namespace
            namespace_pods[ns] = namespace_pods.get(ns, 0) + 1
    
    # Sort by count (all namespaces)
    sorted_ns = sorted(namespace_pods.items(), key=lambda x: x[1], reverse=True)
    
    # PV data
    pvs_json = []
    for pv in pvs:
        pvs_json.append({
            'name': pv.name,
            'capacity': round(pv.capacity, 2),
            'access_modes': pv.access_modes,
            'reclaim_policy': pv.reclaim_policy,
            'status': pv.status,
            'claim': pv.claim or '-',
            'storage_class': pv.storage_class or '-'
        })
    
    # Group nodes by role for architecture diagram
    nodes_by_role = {}
    for node in nodes:
        role = ClusterAnalyzer.categorize_node_role(node)
        if role not in nodes_by_role:
            nodes_by_role[role] = []
        nodes_by_role[role].append({
            'name': node.name.split('.')[0],
            'cpu': round(node.capacity.cpu / 1000, 0),
            'memory': round(node.capacity.memory / 1024, 0)
        })
    
    # Calculate role summaries for architecture diagram
    role_summaries = {}
    for role, role_nodes in nodes_by_role.items():
        if role_nodes:
            role_summaries[role] = {
                'count': len(role_nodes),
                'cpu': role_nodes[0]['cpu'],  # Assuming same specs
                'memory': role_nodes[0]['memory'],
                'nodes': role_nodes
            }
    
    # Pre-compute workload inventory tab HTML (can't call functions inside f-string)
    workload_inventory_html = _generate_workload_inventory_tab(workloads or {})
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCP Sizing Calculator - Assessment Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&family=Red+Hat+Mono&display=swap" rel="stylesheet">
{STYLES}
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div class="title-section">
                    <h1>OCP Sizing Calculator</h1>
                    <p>Kubernetes to OpenShift Migration Assessment</p>
                </div>
            </div>
            <div class="header-meta">
                <div>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                <div>{summary.total_nodes} nodes analyzed</div>
            </div>
        </div>
    </header>
    
    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <div class="nav-tab active" data-tab="overview">Overview</div>
            <div class="nav-tab" data-tab="nodes">Node Inventory</div>
            <div class="nav-tab" data-tab="efficiency">Efficiency Analysis</div>
            <div class="nav-tab" data-tab="workloads">Workload Distribution</div>
            <div class="nav-tab" data-tab="workload-inventory">Workload Inventory</div>
            {'<div class="nav-tab" data-tab="recommendations">OCP Recommendations</div>' if include_recommendations else ''}
            {'<div class="nav-tab" data-tab="checklist">Migration Checklist</div>' if include_recommendations else ''}
            <div class="nav-tab" data-tab="storage">Persistent Volumes</div>
        </div>
    </nav>
    
    <main class="main-content">
        <!-- Overview Tab -->
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
        </div>
        
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
        
        <!-- Workloads Tab -->
        <div class="tab-content" id="workloads">
            <div class="section-header">
                <h2 class="section-title">Workload Distribution</h2>
                <p class="section-subtitle">Analysis of pod distribution across namespaces and nodes</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="workloadTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="workloadTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="workloadTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="workloadTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="workloadTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
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
        </div>
        
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
        
        <!-- Storage Tab (Always visible, shows "No Data" if no PVs) -->
        <div class="tab-content" id="storage">
            <div class="section-header">
                <h2 class="section-title">Persistent Volumes</h2>
                <p class="section-subtitle">Storage analysis and migration considerations</p>
            </div>
            
            {f'''
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total PVs</span>
                        <div class="card-icon storage">💾</div>
                    </div>
                    <div class="card-value">{summary.total_pv_count}</div>
                    <div class="card-subtitle">persistent volumes</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total Capacity</span>
                        <div class="card-icon storage">📊</div>
                    </div>
                    <div class="card-value">{summary.total_pv_capacity:.1f}</div>
                    <div class="card-subtitle">GiB provisioned</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Storage Classes</span>
                        <div class="card-icon storage">🏷️</div>
                    </div>
                    <div class="card-value">{len(summary.storage_classes)}</div>
                    <div class="card-subtitle">{", ".join(list(summary.storage_classes)[:3]) if summary.storage_classes else "N/A"}</div>
                </div>
            </div>
            
            <div class="table-container">
                <div class="table-header">
                    <h3 class="table-title">Persistent Volume Details</h3>
                </div>
                <div class="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Capacity</th>
                                <th>Access Modes</th>
                                <th>Reclaim Policy</th>
                                <th>Status</th>
                                <th>Claim</th>
                                <th>Storage Class</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f"""
                            <tr>
                                <td><strong>{pv['name']}</strong></td>
                                <td>{pv['capacity']:.1f} GiB</td>
                                <td>{pv['access_modes']}</td>
                                <td>{pv['reclaim_policy']}</td>
                                <td><span class="badge {'badge-success' if pv['status'] == 'Bound' else 'badge-warning'}">{pv['status']}</span></td>
                                <td>{pv['claim']}</td>
                                <td>{pv['storage_class']}</td>
                            </tr>
                            """ for pv in pvs_json])}
                        </tbody>
                    </table>
                </div>
            </div>
            ''' if pvs else '''
            <div class="no-data">
                <div class="no-data-icon">💾</div>
                <h3 class="no-data-title">No Persistent Volume Data Available</h3>
                <p class="no-data-text">PV information was not provided. To include storage analysis, run:</p>
                <p class="no-data-text" style="margin-top: 1rem; font-family: monospace; background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px; display: inline-block;">
                    kubectl get pv -o wide &gt; cluster-pv.txt
                </p>
                <p class="no-data-text" style="margin-top: 1rem;">Then re-run the tool with the -p flag to include PV analysis.</p>
            </div>
            '''}
        </div>
    </main>
    
    <footer class="footer">
        <p>OCP Sizing Calculator v1.1 | Generated by Red Hat Solution Architecture</p>
        <p>This assessment is based on point-in-time data. Actual requirements may vary based on workload patterns.</p>
    </footer>
    
    <script>
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab).classList.add('active');
            }});
        }});
        
        // Filter functionality - Enhanced with sum row and chart updates
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const tableId = btn.dataset.table;
                const filter = btn.dataset.filter;
                
                // Update active state for this filter group
                btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Filter table rows
                const table = document.getElementById(tableId);
                if (table) {{
                    const rows = table.querySelectorAll('tbody tr');
                    let visibleCount = 0;
                    
                    rows.forEach(row => {{
                        if (filter === 'all' || row.dataset.role === filter) {{
                            row.classList.remove('filtered-out');
                            visibleCount++;
                        }} else {{
                            row.classList.add('filtered-out');
                        }}
                    }});
                    
                    // Update count display
                    const countEl = document.getElementById(tableId + 'Count');
                    if (countEl) {{
                        countEl.textContent = visibleCount;
                    }}
                    
                    // Update sum row for nodesTable
                    if (tableId === 'nodesTable') {{
                        updateNodesTableSumRow(filter);
                    }}
                    
                    // Update efficiency tab cards and charts
                    if (tableId === 'efficiencyTable') {{
                        updateEfficiencyTabForFilter(filter);
                        updateEfficiencyTableSumRow(filter);
                    }}
                    
                    // Update workloads tab charts
                    if (tableId === 'workloadTable') {{
                        updateWorkloadsTabForFilter(filter);
                        updateWorkloadTableSumRow(filter);
                    }}
                }}
            }});
        }});
        
        // Function to update the nodes table sum row
        function updateNodesTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const count = filteredNodes.length;
            const cpuCores = filteredNodes.reduce((sum, n) => sum + n.cpu_capacity, 0);
            const cpuRequested = filteredNodes.reduce((sum, n) => sum + n.cpu_requested, 0);
            const cpuActual = filteredNodes.reduce((sum, n) => sum + n.cpu_actual, 0);
            const memCapacity = filteredNodes.reduce((sum, n) => sum + n.mem_capacity, 0);
            const memRequested = filteredNodes.reduce((sum, n) => sum + n.mem_requested, 0);
            const memActual = filteredNodes.reduce((sum, n) => sum + n.mem_actual, 0);
            const pods = filteredNodes.reduce((sum, n) => sum + n.pod_count, 0);
            
            document.getElementById('sumNodeCount').textContent = count + ' nodes';
            document.getElementById('sumCpuCores').textContent = cpuCores.toFixed(1);
            document.getElementById('sumCpuRequested').textContent = cpuRequested.toFixed(2);
            document.getElementById('sumCpuActual').textContent = cpuActual.toFixed(2);
            document.getElementById('sumMemCapacity').textContent = memCapacity.toFixed(1);
            document.getElementById('sumMemRequested').textContent = memRequested.toFixed(1);
            document.getElementById('sumMemActual').textContent = memActual.toFixed(1);
            document.getElementById('sumPods').textContent = pods;
        }}
        
        // Function to update Pods per Node sum row (#11)
        function updateWorkloadTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const podCount = filteredNodes.reduce((s, n) => s + n.pod_count, 0);
            const podCap = filteredNodes.reduce((s, n) => s + (n.pod_capacity || 0), 0);
            document.getElementById('sumWlNodeCount').textContent = filteredNodes.length + ' nodes';
            document.getElementById('sumWlPodCount').textContent = podCount;
            document.getElementById('sumWlPodCapacity').textContent = podCap;
        }}
        
        // Function to update Efficiency table sum row (#12)
        function updateEfficiencyTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const cpuReq = filteredNodes.reduce((s, n) => s + n.cpu_requested, 0);
            const cpuAct = filteredNodes.reduce((s, n) => s + n.cpu_actual, 0);
            const memReq = filteredNodes.reduce((s, n) => s + n.mem_requested, 0);
            const memAct = filteredNodes.reduce((s, n) => s + n.mem_actual, 0);
            document.getElementById('sumEffNodeCount').textContent = filteredNodes.length + ' nodes';
            document.getElementById('sumEffCpuReq').textContent = cpuReq.toFixed(2) + ' cores';
            document.getElementById('sumEffCpuActual').textContent = cpuAct.toFixed(2) + ' cores';
            document.getElementById('sumEffMemReq').textContent = memReq.toFixed(1) + ' GiB';
            document.getElementById('sumEffMemActual').textContent = memAct.toFixed(1) + ' GiB';
        }}
        
        // Function to update efficiency tab when filter changes
        function updateEfficiencyTabForFilter(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const filterLabel = filter === 'all' ? '' : ' (' + filter + ')';
            
            // Calculate totals for filtered nodes
            const totalCpuCapacity = filteredNodes.reduce((sum, n) => sum + n.cpu_capacity, 0);
            const totalCpuRequested = filteredNodes.reduce((sum, n) => sum + n.cpu_requested, 0);
            const totalCpuActual = filteredNodes.reduce((sum, n) => sum + n.cpu_actual, 0);
            const totalMemCapacity = filteredNodes.reduce((sum, n) => sum + n.mem_capacity, 0);
            const totalMemRequested = filteredNodes.reduce((sum, n) => sum + n.mem_requested, 0);
            const totalMemActual = filteredNodes.reduce((sum, n) => sum + n.mem_actual, 0);
            
            // CPU Request Accuracy Card
            const cpuReqAccuracy = totalCpuRequested > 0 ? Math.round(totalCpuActual / totalCpuRequested * 100) : 0;
            const cpuReqValueEl = document.getElementById('cpuRequestAccuracyValue');
            cpuReqValueEl.textContent = cpuReqAccuracy + '%';
            cpuReqValueEl.className = 'card-value ' + (cpuReqAccuracy <= 100 ? 'text-success' : 'text-danger');
            document.getElementById('cpuRequestAccuracySubtitle').textContent = cpuReqAccuracy <= 100 ? 'of requested CPU is being used' : 'of requested CPU is being used (over limit!)';
            document.getElementById('cpuRequestAccuracyDetail').textContent = totalCpuRequested.toFixed(1) + ' cores requested, ' + totalCpuActual.toFixed(1) + ' actually used';
            const cpuReqAdviceEl = document.getElementById('cpuRequestAccuracyAdvice');
            cpuReqAdviceEl.textContent = cpuReqAccuracy <= 100 ? '💡 Requests well-sized or over-provisioned' : '⚠️ Usage exceeds requests - set proper limits!';
            cpuReqAdviceEl.className = 'card-advice ' + (cpuReqAccuracy <= 100 ? 'advice-success' : 'advice-danger');
            
            // Memory Request Accuracy Card
            const memReqAccuracy = totalMemRequested > 0 ? Math.round(totalMemActual / totalMemRequested * 100) : 0;
            const memReqValueEl = document.getElementById('memRequestAccuracyValue');
            memReqValueEl.textContent = memReqAccuracy + '%';
            memReqValueEl.className = 'card-value ' + (memReqAccuracy <= 100 ? 'text-success' : 'text-danger');
            document.getElementById('memRequestAccuracySubtitle').textContent = memReqAccuracy <= 100 ? 'of requested memory is being used' : 'of requested memory is being used (over limit!)';
            document.getElementById('memRequestAccuracyDetail').textContent = totalMemRequested.toFixed(1) + ' GiB requested, ' + totalMemActual.toFixed(1) + ' GiB actually used';
            const memReqAdviceEl = document.getElementById('memRequestAccuracyAdvice');
            memReqAdviceEl.textContent = memReqAccuracy <= 100 ? '💡 Requests well-sized or over-provisioned' : '⚠️ Usage exceeds requests - set proper limits!';
            memReqAdviceEl.className = 'card-advice ' + (memReqAccuracy <= 100 ? 'advice-success' : 'advice-danger');
            
            // CPU Capacity Utilization Card
            const cpuCapUtil = totalCpuCapacity > 0 ? Math.round(totalCpuActual / totalCpuCapacity * 100) : 0;
            document.getElementById('cpuCapacityValue').textContent = cpuCapUtil + '%';
            document.getElementById('cpuCapacityDetail').textContent = totalCpuCapacity.toFixed(0) + ' cores capacity, ' + totalCpuActual.toFixed(1) + ' actually used';
            const cpuCapAdviceEl = document.getElementById('cpuCapacityAdvice');
            if (cpuCapUtil < 50) {{
                cpuCapAdviceEl.textContent = 'ℹ️ Low utilization - room to grow';
                cpuCapAdviceEl.className = 'card-advice advice-info';
            }} else if (cpuCapUtil < 80) {{
                cpuCapAdviceEl.textContent = '⚡ Moderate utilization';
                cpuCapAdviceEl.className = 'card-advice advice-warning';
            }} else {{
                cpuCapAdviceEl.textContent = '🔥 High utilization - consider scaling';
                cpuCapAdviceEl.className = 'card-advice advice-danger';
            }}
            
            // Memory Capacity Utilization Card
            const memCapUtil = totalMemCapacity > 0 ? Math.round(totalMemActual / totalMemCapacity * 100) : 0;
            document.getElementById('memCapacityValue').textContent = memCapUtil + '%';
            document.getElementById('memCapacityDetail').textContent = totalMemCapacity.toFixed(0) + ' GiB capacity, ' + totalMemActual.toFixed(1) + ' GiB actually used';
            const memCapAdviceEl = document.getElementById('memCapacityAdvice');
            if (memCapUtil < 50) {{
                memCapAdviceEl.textContent = 'ℹ️ Low utilization - room to grow';
                memCapAdviceEl.className = 'card-advice advice-info';
            }} else if (memCapUtil < 80) {{
                memCapAdviceEl.textContent = '⚡ Moderate utilization';
                memCapAdviceEl.className = 'card-advice advice-warning';
            }} else {{
                memCapAdviceEl.textContent = '🔥 High utilization - consider scaling';
                memCapAdviceEl.className = 'card-advice advice-danger';
            }}
            
            // Update filter indicators for all 4 cards
            const filterIndicatorIds = ['cpuRequestAccuracyFilter', 'memRequestAccuracyFilter', 'cpuCapacityFilter', 'memCapacityFilter'];
            filterIndicatorIds.forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    if (filter === 'all') {{
                        el.classList.add('hidden');
                    }} else {{
                        el.classList.remove('hidden');
                        el.innerHTML = 'Filtered: ' + filter + ' <span class="clear-filter" onclick="clearEfficiencyFilter()">✕</span>';
                    }}
                }}
            }});
            
            // Update chart titles
            document.getElementById('cpuChartTitle').textContent = 'CPU: Requested vs Actual per Node' + filterLabel;
            document.getElementById('memChartTitle').textContent = 'Memory: Requested vs Actual per Node' + filterLabel;
            
            // Update CPU Efficiency Chart
            cpuEfficiencyChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            cpuEfficiencyChart.data.datasets[0].data = filteredNodes.map(n => n.cpu_requested);
            cpuEfficiencyChart.data.datasets[1].data = filteredNodes.map(n => n.cpu_actual);
            cpuEfficiencyChart.update();
            
            // Update Memory Efficiency Chart
            memoryEfficiencyChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            memoryEfficiencyChart.data.datasets[0].data = filteredNodes.map(n => n.mem_requested);
            memoryEfficiencyChart.data.datasets[1].data = filteredNodes.map(n => n.mem_actual);
            memoryEfficiencyChart.update();
        }}
        
        // Function to clear efficiency filter
        function clearEfficiencyFilter() {{
            const allBtn = document.querySelector('#efficiency .filter-btn[data-filter="all"]');
            if (allBtn) allBtn.click();
        }}
        
        // Function to update workloads tab when filter changes
        function updateWorkloadsTabForFilter(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const filterLabel = filter === 'all' ? '' : ' (' + filter + ')';
            
            // Calculate namespace data for filtered nodes only
            const filteredNsData = {{}};
            filteredNodes.forEach(node => {{
                // Find full node data to get pods
                const fullNode = nodesData.find(n => n.name === node.name);
                if (fullNode && fullNode.pods) {{
                    fullNode.pods.forEach(pod => {{
                        filteredNsData[pod.namespace] = (filteredNsData[pod.namespace] || 0) + 1;
                    }});
                }}
            }});
            
            // If we don't have pod details, use the pod_count as estimate
            if (Object.keys(filteredNsData).length === 0) {{
                // Fallback: just update the pods per node chart
            }}
            
            // Update Pods per Node chart
            document.getElementById('podsPerNodeChartTitle').textContent = 'Pods per Node' + filterLabel;
            podsPerNodeChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            podsPerNodeChart.data.datasets[0].data = filteredNodes.map(n => n.pod_count);
            podsPerNodeChart.update();
            
            // Update namespace chart title
            const nsCount = filter === 'all' ? Object.keys(namespaceData).length : Object.keys(filteredNsData).length;
            document.getElementById('namespaceChartTitle').textContent = 'Pods by Namespace (' + nsCount + ' namespaces)' + filterLabel;
            
            // For namespace chart, we need the full pod data which isn't in nodesData
            // So we'll show a message or keep the full data with a note
            if (filter !== 'all') {{
                // Update with filtered namespace data if available
                if (Object.keys(filteredNsData).length > 0) {{
                    const sortedFiltered = Object.entries(filteredNsData).sort((a, b) => b[1] - a[1]);
                    namespaceChart.data.labels = sortedFiltered.map(([k, v]) => k);
                    namespaceChart.data.datasets[0].data = sortedFiltered.map(([k, v]) => v);
                    namespaceChart.update();
                }}
            }} else {{
                // Reset to full namespace data
                namespaceChart.data.labels = Object.keys(namespaceData);
                namespaceChart.data.datasets[0].data = Object.values(namespaceData);
                namespaceChart.update();
            }}
        }}
        
        // Chart data
        const nodesData = {json.dumps(nodes_json)};
        const namespaceData = {json.dumps(dict(sorted_ns))};
        
        // Chart colors
        const colors = {{
            red: '#EE0000',
            blue: '#0066CC',
            green: '#3E8635',
            purple: '#6753AC',
            orange: '#F0AB00',
            cyan: '#009596',
            gray: '#6A6E73'
        }};
        
        // CPU Overview Chart (Capacity vs Requested vs Actual)
        new Chart(document.getElementById('cpuOverviewChart'), {{
            type: 'bar',
            data: {{
                labels: ['Capacity', 'Requested', 'Actual'],
                datasets: [{{
                    label: 'CPU (cores)',
                    data: [{round(summary.total_capacity.cpu / 1000, 1)}, {round(summary.total_requested.cpu / 1000, 1)}, {round(summary.total_actual.cpu / 1000, 1)}],
                    backgroundColor: [colors.gray, colors.blue, colors.green]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'Cores', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Memory Overview Chart (Capacity vs Requested vs Actual)
        new Chart(document.getElementById('memoryOverviewChart'), {{
            type: 'bar',
            data: {{
                labels: ['Capacity', 'Requested', 'Actual'],
                datasets: [{{
                    label: 'Memory (GiB)',
                    data: [{round(summary.total_capacity.memory / 1024, 1)}, {round(summary.total_requested.memory / 1024, 1)}, {round(summary.total_actual.memory / 1024, 1)}],
                    backgroundColor: [colors.gray, colors.blue, colors.green]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'GiB', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Nodes by Role Chart
        const roleData = {json.dumps(dict(summary.nodes_by_role))};
        new Chart(document.getElementById('nodesByRoleChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(roleData),
                datasets: [{{
                    data: Object.values(roleData),
                    backgroundColor: [colors.blue, colors.purple, colors.cyan, colors.orange, colors.gray]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // CPU Efficiency Chart - store as variable for updates
        const cpuEfficiencyChart = new Chart(document.getElementById('cpuEfficiencyChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [
                    {{
                        label: 'CPU Requested',
                        data: nodesData.map(n => n.cpu_requested),
                        backgroundColor: colors.blue
                    }},
                    {{
                        label: 'CPU Actual',
                        data: nodesData.map(n => n.cpu_actual),
                        backgroundColor: colors.green
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'Cores', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Memory Efficiency Chart - store as variable for updates
        const memoryEfficiencyChart = new Chart(document.getElementById('memoryEfficiencyChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [
                    {{
                        label: 'Memory Requested',
                        data: nodesData.map(n => n.mem_requested),
                        backgroundColor: colors.purple
                    }},
                    {{
                        label: 'Memory Actual',
                        data: nodesData.map(n => n.mem_actual),
                        backgroundColor: colors.green
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'GiB', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Namespace Chart - Scrollable with ALL namespaces
        const nsLabels = Object.keys(namespaceData);
        const nsValues = Object.values(namespaceData);
        const chartHeight = Math.max(400, nsLabels.length * 25);
        
        const nsChartContainer = document.getElementById('namespaceChartContainer');
        const nsCanvas = document.getElementById('namespaceChart');
        nsCanvas.style.height = chartHeight + 'px';
        
        // Namespace Chart - store as variable for updates
        const namespaceChart = new Chart(nsCanvas, {{
            type: 'bar',
            data: {{
                labels: nsLabels,
                datasets: [{{
                    label: 'Pods',
                    data: nsValues,
                    backgroundColor: colors.cyan
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }}
                }}
            }}
        }});
        
        // Pods per Node Chart - store as variable for updates
        const podsPerNodeChart = new Chart(document.getElementById('podsPerNodeChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [{{
                    label: 'Running Pods',
                    data: nodesData.map(n => n.pod_count),
                    backgroundColor: colors.orange
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }}
                }}
            }}
        }});
        
        // Table functions
        function filterTable(tableId, searchText) {{
            const table = document.getElementById(tableId);
            const rows = table.getElementsByTagName('tr');
            searchText = searchText.toLowerCase();
            
            for (let i = 1; i < rows.length; i++) {{
                const cells = rows[i].getElementsByTagName('td');
                let found = false;
                for (let j = 0; j < cells.length; j++) {{
                    if (cells[j].textContent.toLowerCase().includes(searchText)) {{
                        found = true;
                        break;
                    }}
                }}
                rows[i].style.display = found ? '' : 'none';
            }}
        }}
        
        function sortTable(tableId, columnIndex) {{
            const table = document.getElementById(tableId);
            const rows = Array.from(table.rows).slice(1);
            const isNumeric = !isNaN(parseFloat(rows[0]?.cells[columnIndex]?.textContent));
            
            rows.sort((a, b) => {{
                let aVal = a.cells[columnIndex].textContent;
                let bVal = b.cells[columnIndex].textContent;
                
                if (isNumeric) {{
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                    return bVal - aVal;
                }}
                return aVal.localeCompare(bVal);
            }});
            
            rows.forEach(row => table.tBodies[0].appendChild(row));
        }}
        
        function exportTableToCSV(tableId, filename) {{
            const table = document.getElementById(tableId);
            let csv = [];
            
            for (let row of table.rows) {{
                let cols = [];
                for (let cell of row.cells) {{
                    cols.push('"' + cell.textContent.replace(/"/g, '""') + '"');
                }}
                csv.push(cols.join(','));
            }}
            
            const blob = new Blob([csv.join('\\n')], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
        }}
    </script>
</body>
</html>
'''
    
    return html


# =============================================================================
# Main Function
# =============================================================================

