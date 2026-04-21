# -*- coding: utf-8 -*-
"""
workload_inventory.py
---------------------
Workload Inventory tab for the OCP Sizing HTML report.

Shows pods, workloads, replicas and namespace-level counts (with actual
CPU/memory usage when a pods-top file is available). Renders a "No pod
data available" placeholder when the cluster_analyzer could not build
workload data (e.g. the input files lack resource requests entirely).

Extracted from html_reporter.py in Phase 5a of the refactor. The function
body is unchanged; only the signature and location moved.
"""

from reporters.report_context import ReportContext


def build(ctx: ReportContext) -> str:
    """Generate the Workload Inventory tab HTML with filters and dynamic cards."""
    workloads = ctx.workloads
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
