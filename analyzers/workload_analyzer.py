"""
workload_analyzer.py
--------------------
Analyze pod data from describe nodes to extract workload insights:
- Unique workloads vs replicas
- Namespace breakdown
- System vs application pods
- Resource request coverage
- Replica spread across nodes
"""

import re
from collections import defaultdict


SYSTEM_NAMESPACES = {
    'kube-system', 'kube-public', 'kube-node-lease',
    'calico-system', 'tigera-operator',
    'kubernetes-dashboard', 'ingress-nginx', 'cert-manager',
    'monitoring', 'logging', 'istio-system', 'metallb-system',
    'local-path-storage', 'rook-ceph', 'velero',
}

SYSTEM_PREFIXES = (
    'openshift-', 'kube-', 'calico-', 'tigera-',
    'istio-', 'knative-', 'tekton-', 'argocd-',
)


def _is_system_namespace(ns):
    """Check if namespace is a system/infrastructure namespace."""
    if ns in SYSTEM_NAMESPACES:
        return True
    for prefix in SYSTEM_PREFIXES:
        if ns.startswith(prefix):
            return True
    return False


def _infer_base_name(pod_name):
    """Infer the workload base name from a pod name by stripping hash suffixes."""
    # Deployment pattern: name-<replicaset-hash>-<pod-hash>
    m = re.match(r'^(.+)-[a-f0-9]{6,10}-[a-z0-9]{5}$', pod_name)
    if m:
        return m.group(1)
    # StatefulSet pattern: name-<ordinal>
    m = re.match(r'^(.+)-(\d+)$', pod_name)
    if m:
        return m.group(1)
    # DaemonSet pattern: name-<hash>
    m = re.match(r'^(.+)-[a-z0-9]{5}$', pod_name)
    if m:
        return m.group(1)
    return pod_name


def analyze_workloads(nodes, pods_top_data=None):
    """
    Analyze workload data from parsed nodes.

    Args:
        nodes: List of NodeData objects (with pods already parsed)
        pods_top_data: Optional dict from parse_top_pods — maps
                       (namespace, pod_name) to (cpu_millicores, memory_mib)

    Returns:
        Dictionary with workload analysis data
    """
    all_pods = []
    has_actual = pods_top_data is not None and len(pods_top_data) > 0
    
    for node in nodes:
        for pod in node.pods:
            # Look up actual usage from pods-top if available
            actual = pods_top_data.get((pod.namespace, pod.name)) if pods_top_data else None
            all_pods.append({
                'node': node.name,
                'namespace': pod.namespace,
                'pod_name': pod.name,
                'base_name': _infer_base_name(pod.name),
                'cpu_requests': pod.cpu_requests,
                'cpu_limits': pod.cpu_limits,
                'memory_requests': pod.memory_requests,
                'memory_limits': pod.memory_limits,
                'is_system': _is_system_namespace(pod.namespace),
                'actual_cpu': actual[0] if actual else 0.0,
                'actual_mem': actual[1] if actual else 0.0,
                'has_actual': actual is not None,
            })

    if not all_pods:
        return {'has_workload_data': False}

    # Group by workload (namespace + base_name)
    workloads = defaultdict(list)
    for p in all_pods:
        workloads[(p['namespace'], p['base_name'])].append(p)

    # Build workload list
    workload_list = []
    for (ns, name), pod_list in sorted(workloads.items()):
        nodes_set = sorted(set(p['node'] for p in pod_list))
        has_cpu_req = any(p['cpu_requests'] > 0 for p in pod_list)
        has_mem_req = any(p['memory_requests'] > 0 for p in pod_list)
        total_cpu_req = sum(p['cpu_requests'] for p in pod_list)
        total_mem_req = sum(p['memory_requests'] for p in pod_list)
        total_actual_cpu = sum(p['actual_cpu'] for p in pod_list)
        total_actual_mem = sum(p['actual_mem'] for p in pod_list)
        has_actual_data = any(p['has_actual'] for p in pod_list)
        is_system = pod_list[0]['is_system']

        workload_list.append({
            'namespace': ns,
            'name': name,
            'replicas': len(pod_list),
            'nodes': nodes_set,
            'node_count': len(nodes_set),
            'is_system': is_system,
            'has_cpu_requests': has_cpu_req,
            'has_mem_requests': has_mem_req,
            'total_cpu_requests_mcpu': round(total_cpu_req),
            'total_mem_requests_mb': round(total_mem_req),
            'total_actual_cpu_mcpu': round(total_actual_cpu),
            'total_actual_mem_mb': round(total_actual_mem),
            'has_actual': has_actual_data,
        })

    # Stats
    total_pods = len(all_pods)
    sys_pods = [p for p in all_pods if p['is_system']]
    app_pods = [p for p in all_pods if not p['is_system']]
    sys_workloads = [w for w in workload_list if w['is_system']]
    app_workloads = [w for w in workload_list if not w['is_system']]
    single_replica = [w for w in workload_list if w['replicas'] == 1]
    multi_replica = [w for w in workload_list if w['replicas'] > 1]

    pods_with_cpu_req = sum(1 for p in all_pods if p['cpu_requests'] > 0)
    pods_with_mem_req = sum(1 for p in all_pods if p['memory_requests'] > 0)
    app_with_cpu_req = sum(1 for p in app_pods if p['cpu_requests'] > 0)
    app_with_mem_req = sum(1 for p in app_pods if p['memory_requests'] > 0)

    # Namespace breakdown
    ns_stats = defaultdict(lambda: {'pods': 0, 'workloads': set(), 'is_system': False})
    for p in all_pods:
        ns_stats[p['namespace']]['pods'] += 1
        ns_stats[p['namespace']]['workloads'].add(p['base_name'])
        ns_stats[p['namespace']]['is_system'] = p['is_system']

    namespace_list = []
    for ns in sorted(ns_stats):
        s = ns_stats[ns]
        namespace_list.append({
            'namespace': ns,
            'pod_count': s['pods'],
            'workload_count': len(s['workloads']),
            'is_system': s['is_system'],
        })

    # Actual usage stats (from pods-top)
    total_actual_cpu = sum(p['actual_cpu'] for p in all_pods)
    total_actual_mem = sum(p['actual_mem'] for p in all_pods)
    app_actual_cpu = sum(p['actual_cpu'] for p in app_pods)
    app_actual_mem = sum(p['actual_mem'] for p in app_pods)
    sys_actual_cpu = sum(p['actual_cpu'] for p in sys_pods)
    sys_actual_mem = sum(p['actual_mem'] for p in sys_pods)
    matched_pods = sum(1 for p in all_pods if p['has_actual'])

    return {
        'has_workload_data': True,
        'has_actual_usage': has_actual,
        'stats': {
            'total_pods': total_pods,
            'total_workloads': len(workload_list),
            'system_pods': len(sys_pods),
            'app_pods': len(app_pods),
            'system_workloads': len(sys_workloads),
            'app_workloads': len(app_workloads),
            'single_replica': len(single_replica),
            'multi_replica': len(multi_replica),
            'namespaces': len(ns_stats),
            'cpu_req_coverage_pct': round(pods_with_cpu_req / total_pods * 100) if total_pods else 0,
            'mem_req_coverage_pct': round(pods_with_mem_req / total_pods * 100) if total_pods else 0,
            'app_cpu_req_coverage_pct': round(app_with_cpu_req / len(app_pods) * 100) if app_pods else 0,
            'app_mem_req_coverage_pct': round(app_with_mem_req / len(app_pods) * 100) if app_pods else 0,
            'total_actual_cpu_mcpu': round(total_actual_cpu),
            'total_actual_mem_mb': round(total_actual_mem),
            'app_actual_cpu_mcpu': round(app_actual_cpu),
            'app_actual_mem_mb': round(app_actual_mem),
            'sys_actual_cpu_mcpu': round(sys_actual_cpu),
            'sys_actual_mem_mb': round(sys_actual_mem),
            'matched_pods': matched_pods,
        },
        'workload_list': workload_list,
        'namespace_list': namespace_list,
    }
