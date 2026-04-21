# -*- coding: utf-8 -*-
"""
report_context.py
-----------------
Typed view-model for the OCP Sizing HTML report.

Phase 3 of the html_reporter.py refactor lifted all data shaping out of
generate_html_report() into a pure function build_context() that returns
a frozen ReportContext dataclass. From Phase 5 onwards, each tab module
will accept ctx: ReportContext as its single argument.

Raw inputs (nodes, summary, recommendations, pvs, workloads,
include_recommendations) are preserved on the context alongside the
derived view-models (nodes_json, sorted_ns, pvs_json, role_summaries,
etc.) so tab modules don't need to reach around the context for anything.

The pre-rendered HTML fragment (script_body_html) also lives on the
context. Phase 5a moved the workload-inventory tab's pre-render OUT of
the context: it is now computed by html_reporter.py via
tabs.workload_inventory.build(ctx) alongside the other tab builders.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from models import ClusterSummary, NodeData, PersistentVolume
from analyzers.cluster_analyzer import ClusterAnalyzer


@dataclass(frozen=True)
class ReportContext:
    """Everything a tab module or the layout shell needs to render the report."""

    # Raw inputs (kept on the context so tab modules have a single argument).
    nodes: List[NodeData]
    summary: ClusterSummary
    recommendations: Dict
    pvs: List[PersistentVolume]
    workloads: Dict
    include_recommendations: bool

    # Derived view-models.
    nodes_json: List[Dict[str, Any]]
    namespace_pods: Dict[str, int]
    sorted_ns: List[Tuple[str, int]]
    pvs_json: List[Dict[str, Any]]
    nodes_by_role: Dict[str, List[Dict[str, Any]]]
    role_summaries: Dict[str, Dict[str, Any]]

    # Pre-rendered HTML fragments (tabs or script body that must be
    # computed outside the main f-string, since you can't call a function
    # inside an f-string that's being concatenated at render time).
    script_body_html: str


def build_context(nodes: List[NodeData],
                  summary: ClusterSummary,
                  recommendations: Dict,
                  pvs: List[PersistentVolume],
                  include_recommendations: bool = True,
                  workloads: Dict = None) -> ReportContext:
    """Assemble a ReportContext from the raw cluster data.

    Pure function: given the same inputs, always produces an equivalent
    context. No side effects, no global state. The pre-rendered HTML
    fragments come from the same helpers that html_reporter.py used
    previously, so swapping this in is byte-identical.
    """
    # Import here to avoid a circular import at module load time.
    # (Phase 5a removed the _generate_workload_inventory_tab lazy import
    # when that function moved to reporters.tabs.workload_inventory.)
    from reporters.scripts import build_script_body

    # --- nodes_json: per-node dict used by JS and the Nodes tab table ---
    nodes_json: List[Dict[str, Any]] = []
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
            'pods': [{'namespace': p.namespace, 'name': p.name} for p in node.pods],
        })

    # --- namespace pod distribution (all namespaces) ---
    namespace_pods: Dict[str, int] = {}
    for node in nodes:
        for pod in node.pods:
            ns = pod.namespace
            namespace_pods[ns] = namespace_pods.get(ns, 0) + 1
    sorted_ns = sorted(namespace_pods.items(), key=lambda x: x[1], reverse=True)

    # --- pvs_json: per-PV dict for the Storage tab ---
    pvs_json: List[Dict[str, Any]] = []
    for pv in pvs:
        pvs_json.append({
            'name': pv.name,
            'capacity': round(pv.capacity, 2),
            'access_modes': pv.access_modes,
            'reclaim_policy': pv.reclaim_policy,
            'status': pv.status,
            'claim': pv.claim or '-',
            'storage_class': pv.storage_class or '-',
        })

    # --- nodes_by_role: architecture diagram grouping ---
    nodes_by_role: Dict[str, List[Dict[str, Any]]] = {}
    for node in nodes:
        role = ClusterAnalyzer.categorize_node_role(node)
        nodes_by_role.setdefault(role, []).append({
            'name': node.name.split('.')[0],
            'cpu': round(node.capacity.cpu / 1000, 0),
            'memory': round(node.capacity.memory / 1024, 0),
        })

    # --- role_summaries: used by the architecture diagram and filter bars ---
    role_summaries: Dict[str, Dict[str, Any]] = {}
    for role, role_nodes in nodes_by_role.items():
        if role_nodes:
            role_summaries[role] = {
                'count': len(role_nodes),
                'cpu': role_nodes[0]['cpu'],   # assumed uniform within role
                'memory': role_nodes[0]['memory'],
                'nodes': role_nodes,
            }

    # --- pre-rendered HTML fragments ---
    script_body_html = build_script_body(nodes_json, sorted_ns, summary)

    return ReportContext(
        nodes=nodes,
        summary=summary,
        recommendations=recommendations,
        pvs=pvs,
        workloads=workloads or {},
        include_recommendations=include_recommendations,
        nodes_json=nodes_json,
        namespace_pods=namespace_pods,
        sorted_ns=sorted_ns,
        pvs_json=pvs_json,
        nodes_by_role=nodes_by_role,
        role_summaries=role_summaries,
        script_body_html=script_body_html,
    )
