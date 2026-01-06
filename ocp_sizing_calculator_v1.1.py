#!/usr/bin/env python3
"""
OCP Sizing Calculator
=====================
Analyzes Kubernetes cluster data to generate OpenShift sizing recommendations.

Required Inputs:
  - kubectl describe nodes output
  - kubectl top nodes output

Optional Inputs:
  - kubectl get pv -o wide output

Author: Red Hat Solution Architecture
Version: 1.1.0
"""

import re
import sys
import json
import argparse
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ResourceSpec:
    """Resource specification (CPU, Memory, Storage)"""
    cpu: float = 0.0  # in millicores
    memory: float = 0.0  # in MiB
    storage: float = 0.0  # in GiB
    pods: int = 0

@dataclass
class PodInfo:
    """Pod information from describe nodes"""
    namespace: str = ""
    name: str = ""
    cpu_requests: float = 0.0
    cpu_limits: float = 0.0
    memory_requests: float = 0.0
    memory_limits: float = 0.0
    age: str = ""

@dataclass
class NodeCondition:
    """Node condition status"""
    type: str = ""
    status: str = ""
    reason: str = ""
    message: str = ""

@dataclass
class SystemInfo:
    """Node system information"""
    kernel_version: str = ""
    os_image: str = ""
    container_runtime: str = ""
    kubelet_version: str = ""
    architecture: str = ""

@dataclass
class NodeData:
    """Complete node data structure"""
    name: str = ""
    roles: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    taints: List[str] = field(default_factory=list)
    creation_timestamp: str = ""
    
    # Resources
    capacity: ResourceSpec = field(default_factory=ResourceSpec)
    allocatable: ResourceSpec = field(default_factory=ResourceSpec)
    allocated_requests: ResourceSpec = field(default_factory=ResourceSpec)
    allocated_limits: ResourceSpec = field(default_factory=ResourceSpec)
    
    # Actual usage (from top nodes)
    actual_usage: ResourceSpec = field(default_factory=ResourceSpec)
    
    # Pods running on this node
    pods: List[PodInfo] = field(default_factory=list)
    pod_count: int = 0
    
    # Status
    conditions: List[NodeCondition] = field(default_factory=list)
    is_ready: bool = True
    is_schedulable: bool = True
    
    # System info
    system_info: SystemInfo = field(default_factory=SystemInfo)
    provider_id: str = ""
    instance_type: str = ""
    ip_address: str = ""

@dataclass
class PersistentVolume:
    """Persistent Volume information"""
    name: str = ""
    capacity: float = 0.0  # in GiB
    access_modes: str = ""
    reclaim_policy: str = ""
    status: str = ""
    claim: str = ""
    storage_class: str = ""
    volume_mode: str = ""

@dataclass
class ClusterSummary:
    """Cluster-wide summary statistics"""
    total_nodes: int = 0
    nodes_by_role: Dict[str, int] = field(default_factory=dict)
    
    total_capacity: ResourceSpec = field(default_factory=ResourceSpec)
    total_allocatable: ResourceSpec = field(default_factory=ResourceSpec)
    total_requested: ResourceSpec = field(default_factory=ResourceSpec)
    total_actual: ResourceSpec = field(default_factory=ResourceSpec)
    
    total_pods: int = 0
    namespaces: set = field(default_factory=set)
    
    kubernetes_version: str = ""
    container_runtime: str = ""
    provider: str = ""
    
    # PV summary
    total_pv_count: int = 0
    total_pv_capacity: float = 0.0
    storage_classes: set = field(default_factory=set)


# =============================================================================
# Parsing Functions
# =============================================================================

def parse_cpu(value: str) -> float:
    """Parse CPU value to millicores"""
    if not value or value == "0":
        return 0.0
    value = value.strip()
    if value.endswith('m'):
        return float(value[:-1])
    elif value.endswith('n'):
        return float(value[:-1]) / 1_000_000
    else:
        return float(value) * 1000

def parse_memory(value: str) -> float:
    """Parse memory value to MiB"""
    if not value or value == "0":
        return 0.0
    value = value.strip()
    
    multipliers = {
        'Ki': 1/1024,
        'Mi': 1,
        'Gi': 1024,
        'Ti': 1024*1024,
        'K': 1/1024,
        'M': 1,
        'G': 1024,
        'T': 1024*1024,
        'k': 1/1024,
        'm': 1,
        'g': 1024,
        't': 1024*1024,
    }
    
    for suffix, mult in multipliers.items():
        if value.endswith(suffix):
            return float(value[:-len(suffix)]) * mult
    
    # Assume bytes
    try:
        return float(value) / (1024 * 1024)
    except:
        return 0.0

def parse_storage(value: str) -> float:
    """Parse storage value to GiB"""
    if not value or value == "0":
        return 0.0
    value = value.strip()
    
    multipliers = {
        'Ki': 1/(1024*1024),
        'Mi': 1/1024,
        'Gi': 1,
        'Ti': 1024,
        'Pi': 1024*1024,
    }
    
    for suffix, mult in multipliers.items():
        if value.endswith(suffix):
            return float(value[:-len(suffix)]) * mult
    
    try:
        return float(value) / (1024**3)
    except:
        return 0.0

def parse_percentage(value: str) -> float:
    """Parse percentage string to float"""
    if not value:
        return 0.0
    match = re.search(r'(\d+)%', value)
    if match:
        return float(match.group(1))
    return 0.0


def parse_describe_nodes(content: str) -> List[NodeData]:
    """Parse kubectl describe nodes output"""
    nodes = []
    
    # Split by node blocks (each starts with "Name:")
    node_blocks = re.split(r'\n(?=Name:\s+\S)', content)
    
    for block in node_blocks:
        if not block.strip() or not block.strip().startswith('Name:'):
            continue
        
        node = NodeData()
        lines = block.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Node name
            if line.startswith('Name:'):
                node.name = line.split(':', 1)[1].strip()
            
            # Roles
            elif line.startswith('Roles:'):
                roles_str = line.split(':', 1)[1].strip()
                node.roles = [r.strip() for r in roles_str.split(',') if r.strip()]
            
            # Labels section
            elif line.startswith('Labels:'):
                label_str = line.split(':', 1)[1].strip()
                if '=' in label_str:
                    key, val = label_str.split('=', 1)
                    node.labels[key.strip()] = val.strip()
                i += 1
                while i < len(lines) and lines[i].startswith(' ') and '=' in lines[i]:
                    label_line = lines[i].strip()
                    if '=' in label_line:
                        key, val = label_line.split('=', 1)
                        node.labels[key.strip()] = val.strip()
                    i += 1
                # Extract instance type
                for key in node.labels:
                    if 'instance-type' in key:
                        node.instance_type = node.labels[key]
                        break
                continue
            
            # Taints
            elif line.startswith('Taints:'):
                taint_str = line.split(':', 1)[1].strip()
                if taint_str and taint_str != '<none>':
                    node.taints.append(taint_str)
                i += 1
                while i < len(lines) and lines[i].startswith(' ') and not lines[i].strip().startswith(('Unschedulable', 'Lease')):
                    taint_line = lines[i].strip()
                    if taint_line and taint_line != '<none>':
                        node.taints.append(taint_line)
                    i += 1
                continue
            
            # Creation timestamp
            elif line.startswith('CreationTimestamp:'):
                node.creation_timestamp = line.split(':', 1)[1].strip()
            
            # Unschedulable
            elif line.startswith('Unschedulable:'):
                node.is_schedulable = line.split(':', 1)[1].strip().lower() != 'true'
            
            # Addresses - extract IP
            elif line.startswith('Addresses:'):
                i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    addr_line = lines[i].strip()
                    if addr_line.startswith('InternalIP:'):
                        node.ip_address = addr_line.split(':', 1)[1].strip()
                    i += 1
                continue
            
            # Capacity
            elif line.startswith('Capacity:'):
                i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    cap_line = lines[i].strip()
                    if cap_line.startswith('cpu:'):
                        node.capacity.cpu = parse_cpu(cap_line.split(':', 1)[1].strip())
                    elif cap_line.startswith('memory:'):
                        node.capacity.memory = parse_memory(cap_line.split(':', 1)[1].strip())
                    elif cap_line.startswith('ephemeral-storage:'):
                        node.capacity.storage = parse_storage(cap_line.split(':', 1)[1].strip())
                    elif cap_line.startswith('pods:'):
                        try:
                            node.capacity.pods = int(cap_line.split(':', 1)[1].strip())
                        except:
                            pass
                    i += 1
                continue
            
            # Allocatable
            elif line.startswith('Allocatable:'):
                i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    alloc_line = lines[i].strip()
                    if alloc_line.startswith('cpu:'):
                        node.allocatable.cpu = parse_cpu(alloc_line.split(':', 1)[1].strip())
                    elif alloc_line.startswith('memory:'):
                        node.allocatable.memory = parse_memory(alloc_line.split(':', 1)[1].strip())
                    elif alloc_line.startswith('ephemeral-storage:'):
                        node.allocatable.storage = parse_storage(alloc_line.split(':', 1)[1].strip())
                    elif alloc_line.startswith('pods:'):
                        try:
                            node.allocatable.pods = int(alloc_line.split(':', 1)[1].strip())
                        except:
                            pass
                    i += 1
                continue
            
            # System Info
            elif line.startswith('System Info:'):
                i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    info_line = lines[i].strip()
                    if info_line.startswith('Kernel Version:'):
                        node.system_info.kernel_version = info_line.split(':', 1)[1].strip()
                    elif info_line.startswith('OS Image:'):
                        node.system_info.os_image = info_line.split(':', 1)[1].strip()
                    elif info_line.startswith('Container Runtime Version:'):
                        node.system_info.container_runtime = info_line.split(':', 1)[1].strip()
                    elif info_line.startswith('Kubelet Version:'):
                        node.system_info.kubelet_version = info_line.split(':', 1)[1].strip()
                    elif info_line.startswith('Architecture:'):
                        node.system_info.architecture = info_line.split(':', 1)[1].strip()
                    i += 1
                continue
            
            # Provider ID
            elif line.startswith('ProviderID:'):
                node.provider_id = line.split(':', 1)[1].strip()
            
            # Non-terminated Pods
            elif line.startswith('Non-terminated Pods:'):
                match = re.search(r'\((\d+)\s+in total\)', line)
                if match:
                    node.pod_count = int(match.group(1))
                i += 1
                # Skip header lines
                while i < len(lines) and (lines[i].strip().startswith('Namespace') or lines[i].strip().startswith('---')):
                    i += 1
                # Parse pod lines
                while i < len(lines) and lines[i].startswith(' '):
                    pod_line = lines[i].strip()
                    if not pod_line or pod_line.startswith('Allocated'):
                        break
                    parts = pod_line.split()
                    if len(parts) >= 6:
                        pod = PodInfo()
                        pod.namespace = parts[0]
                        pod.name = parts[1]
                        pod.cpu_requests = parse_cpu(parts[2].split('(')[0])
                        pod.cpu_limits = parse_cpu(parts[3].split('(')[0])
                        pod.memory_requests = parse_memory(parts[4].split('(')[0])
                        pod.memory_limits = parse_memory(parts[5].split('(')[0])
                        if len(parts) >= 7:
                            pod.age = parts[6]
                        node.pods.append(pod)
                    i += 1
                continue
            
            # Allocated resources
            elif line.startswith('Allocated resources:'):
                i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    alloc_line = lines[i].strip()
                    if alloc_line.startswith('cpu'):
                        parts = alloc_line.split()
                        if len(parts) >= 2:
                            node.allocated_requests.cpu = parse_cpu(parts[1].split('(')[0])
                        if len(parts) >= 3:
                            node.allocated_limits.cpu = parse_cpu(parts[2].split('(')[0])
                    elif alloc_line.startswith('memory'):
                        parts = alloc_line.split()
                        if len(parts) >= 2:
                            node.allocated_requests.memory = parse_memory(parts[1].split('(')[0])
                        if len(parts) >= 3:
                            node.allocated_limits.memory = parse_memory(parts[2].split('(')[0])
                    i += 1
                continue
            
            # Conditions
            elif line.startswith('Conditions:'):
                i += 1
                # Skip header
                while i < len(lines) and (lines[i].strip().startswith('Type') or lines[i].strip().startswith('---')):
                    i += 1
                while i < len(lines) and lines[i].startswith(' '):
                    cond_line = lines[i].strip()
                    if not cond_line or cond_line.startswith('Addresses'):
                        break
                    parts = cond_line.split()
                    if len(parts) >= 2:
                        cond = NodeCondition()
                        cond.type = parts[0]
                        cond.status = parts[1]
                        if cond.type == 'Ready':
                            node.is_ready = cond.status == 'True'
                        node.conditions.append(cond)
                    i += 1
                continue
            
            i += 1
        
        if node.name:
            nodes.append(node)
    
    # Deduplicate nodes (file might have duplicates)
    seen = set()
    unique_nodes = []
    for node in nodes:
        if node.name not in seen:
            seen.add(node.name)
            unique_nodes.append(node)
    
    return unique_nodes


def parse_top_nodes(content: str) -> Dict[str, Tuple[float, float, float, float]]:
    """
    Parse kubectl top nodes output.
    Returns dict: node_name -> (cpu_cores, cpu_percent, memory_mib, memory_percent)
    """
    usage = {}
    lines = content.strip().split('\n')
    
    for line in lines:
        # Skip header
        if line.startswith('NAME') or not line.strip():
            continue
        
        parts = line.split()
        if len(parts) >= 5:
            name = parts[0]
            cpu_cores = parse_cpu(parts[1])
            cpu_pct = parse_percentage(parts[2])
            mem_mib = parse_memory(parts[3])
            mem_pct = parse_percentage(parts[4])
            usage[name] = (cpu_cores, cpu_pct, mem_mib, mem_pct)
    
    return usage


def parse_pvs(content: str) -> List[PersistentVolume]:
    """Parse kubectl get pv -o wide output"""
    pvs = []
    lines = content.strip().split('\n')
    
    for line in lines:
        if line.startswith('NAME') or not line.strip():
            continue
        
        parts = line.split()
        if len(parts) >= 6:
            pv = PersistentVolume()
            pv.name = parts[0]
            pv.capacity = parse_storage(parts[1])
            pv.access_modes = parts[2]
            pv.reclaim_policy = parts[3]
            pv.status = parts[4]
            if len(parts) >= 6 and parts[5] != '<none>':
                pv.claim = parts[5]
            if len(parts) >= 7:
                pv.storage_class = parts[6]
            if len(parts) >= 8:
                pv.volume_mode = parts[7]
            pvs.append(pv)
    
    return pvs


# =============================================================================
# Analysis Functions
# =============================================================================

def merge_top_data(nodes: List[NodeData], top_data: Dict[str, Tuple[float, float, float, float]]):
    """Merge top nodes data into node objects"""
    for node in nodes:
        if node.name in top_data:
            cpu, cpu_pct, mem, mem_pct = top_data[node.name]
            node.actual_usage.cpu = cpu
            node.actual_usage.memory = mem


def calculate_cluster_summary(nodes: List[NodeData], pvs: List[PersistentVolume]) -> ClusterSummary:
    """Calculate cluster-wide summary statistics"""
    summary = ClusterSummary()
    summary.total_nodes = len(nodes)
    
    for node in nodes:
        # Count by role
        role = categorize_node_role(node)
        summary.nodes_by_role[role] = summary.nodes_by_role.get(role, 0) + 1
        
        # Aggregate resources
        summary.total_capacity.cpu += node.capacity.cpu
        summary.total_capacity.memory += node.capacity.memory
        summary.total_capacity.storage += node.capacity.storage
        summary.total_capacity.pods += node.capacity.pods
        
        summary.total_allocatable.cpu += node.allocatable.cpu
        summary.total_allocatable.memory += node.allocatable.memory
        summary.total_allocatable.storage += node.allocatable.storage
        summary.total_allocatable.pods += node.allocatable.pods
        
        summary.total_requested.cpu += node.allocated_requests.cpu
        summary.total_requested.memory += node.allocated_requests.memory
        
        summary.total_actual.cpu += node.actual_usage.cpu
        summary.total_actual.memory += node.actual_usage.memory
        
        summary.total_pods += node.pod_count
        
        # Collect namespaces
        for pod in node.pods:
            summary.namespaces.add(pod.namespace)
        
        # Version info (from first node)
        if not summary.kubernetes_version and node.system_info.kubelet_version:
            summary.kubernetes_version = node.system_info.kubelet_version
        if not summary.container_runtime and node.system_info.container_runtime:
            summary.container_runtime = node.system_info.container_runtime
        if not summary.provider and node.provider_id:
            if 'vsphere' in node.provider_id.lower():
                summary.provider = 'VMware vSphere'
            elif 'aws' in node.provider_id.lower():
                summary.provider = 'AWS'
            elif 'azure' in node.provider_id.lower():
                summary.provider = 'Azure'
            elif 'gce' in node.provider_id.lower():
                summary.provider = 'Google Cloud'
            else:
                summary.provider = 'Unknown'
    
    # PV summary
    for pv in pvs:
        summary.total_pv_count += 1
        summary.total_pv_capacity += pv.capacity
        if pv.storage_class:
            summary.storage_classes.add(pv.storage_class)
    
    return summary


def categorize_node_role(node: NodeData) -> str:
    """Categorize node into primary role"""
    roles = [r.lower() for r in node.roles]
    
    if 'master' in roles or 'control-plane' in roles:
        return 'control-plane'
    elif 'infra' in roles:
        return 'infra'
    elif 'storage' in roles:
        return 'storage'
    else:
        return 'worker'


def generate_ocp_recommendations(nodes: List[NodeData], summary: ClusterSummary) -> Dict:
    """Generate OpenShift sizing recommendations"""
    recommendations = {
        'control_plane': {
            'current_count': 0,
            'current_cpu': 0,
            'current_memory': 0,
            'recommended_count': 3,
            'recommended_cpu': 8,
            'recommended_memory': 32768,  # 32 GiB in MiB
            'notes': []
        },
        'infra': {
            'current_count': 0,
            'current_cpu': 0,
            'current_memory': 0,
            'recommended_count': 3,
            'recommended_cpu': 16,
            'recommended_memory': 65536,  # 64 GiB in MiB
            'notes': []
        },
        'storage': {
            'current_count': 0,
            'current_cpu': 0,
            'current_memory': 0,
            'recommended_count': 3,
            'recommended_cpu': 16,
            'recommended_memory': 65536,  # 64 GiB in MiB
            'notes': []
        },
        'worker': {
            'current_count': 0,
            'current_cpu': 0,
            'current_memory': 0,
            'actual_cpu_used': 0,
            'actual_memory_used': 0,
            'recommended_count': 0,
            'recommended_cpu': 0,
            'recommended_memory': 0,
            'notes': []
        },
        'overall': {
            'sizing_approach': 'conservative',
            'total_current_nodes': len(nodes),
            'total_recommended_nodes': 0,
            'efficiency_score': 0,
            'warnings': [],
            'opportunities': []
        }
    }
    
    # Categorize nodes
    for node in nodes:
        role = categorize_node_role(node)
        cpu_capacity = node.capacity.cpu / 1000  # Convert to cores
        mem_capacity = node.capacity.memory
        
        if role == 'control-plane':
            recommendations['control_plane']['current_count'] += 1
            recommendations['control_plane']['current_cpu'] = max(
                recommendations['control_plane']['current_cpu'], cpu_capacity)
            recommendations['control_plane']['current_memory'] = max(
                recommendations['control_plane']['current_memory'], mem_capacity)
        elif role == 'infra':
            recommendations['infra']['current_count'] += 1
            recommendations['infra']['current_cpu'] = max(
                recommendations['infra']['current_cpu'], cpu_capacity)
            recommendations['infra']['current_memory'] = max(
                recommendations['infra']['current_memory'], mem_capacity)
        elif role == 'storage':
            recommendations['storage']['current_count'] += 1
            recommendations['storage']['current_cpu'] = max(
                recommendations['storage']['current_cpu'], cpu_capacity)
            recommendations['storage']['current_memory'] = max(
                recommendations['storage']['current_memory'], mem_capacity)
        else:  # worker
            recommendations['worker']['current_count'] += 1
            recommendations['worker']['current_cpu'] += cpu_capacity
            recommendations['worker']['current_memory'] += mem_capacity
            recommendations['worker']['actual_cpu_used'] += node.actual_usage.cpu / 1000
            recommendations['worker']['actual_memory_used'] += node.actual_usage.memory
    
    # Handle small clusters (1-3 nodes) - adjust recommendations
    if summary.total_nodes <= 3:
        recommendations['control_plane']['recommended_count'] = min(3, summary.total_nodes)
        recommendations['infra']['recommended_count'] = 0
        recommendations['infra']['notes'].append('Small cluster - infra workloads can run on control plane or workers')
        recommendations['storage']['recommended_count'] = 0
        recommendations['storage']['notes'].append('Small cluster - consider external storage or hosted storage service')
    
    # Generate worker recommendations
    worker_rec = recommendations['worker']
    if worker_rec['current_count'] > 0:
        # Calculate based on actual usage with 2x headroom
        actual_cpu = worker_rec['actual_cpu_used']
        actual_mem = worker_rec['actual_memory_used']
        
        # Optimized sizing: actual usage * 2 buffer
        opt_cpu_needed = actual_cpu * 2
        opt_mem_needed = actual_mem * 2
        
        # Assume 16 cores, 64GB per worker node (standard OpenShift worker)
        std_worker_cpu = 16
        std_worker_mem = 65536
        
        opt_worker_count = max(2, int((opt_cpu_needed / std_worker_cpu) + 1))
        opt_worker_mem_count = max(2, int((opt_mem_needed / std_worker_mem) + 1))
        
        worker_rec['recommended_count'] = max(opt_worker_count, opt_worker_mem_count)
        worker_rec['recommended_cpu'] = std_worker_cpu
        worker_rec['recommended_memory'] = std_worker_mem
        
        # Calculate efficiency
        if worker_rec['current_cpu'] > 0:
            efficiency = (actual_cpu / worker_rec['current_cpu']) * 100
            recommendations['overall']['efficiency_score'] = round(efficiency, 1)
    elif summary.total_nodes > 0:
        # No dedicated workers - all-in-one or control-plane only cluster
        worker_rec['recommended_count'] = 0
        worker_rec['notes'].append('No dedicated worker nodes - workloads run on control plane')
    
    # Control plane recommendations
    cp_rec = recommendations['control_plane']
    if cp_rec['current_count'] > 0:
        if cp_rec['current_memory'] < 16384:
            cp_rec['notes'].append('Memory below recommended 16 GiB minimum')
        if cp_rec['current_memory'] < 32768 and summary.total_nodes > 3:
            cp_rec['notes'].append('Consider 32 GiB for production clusters')
    
    # Handle single-node cluster
    if summary.total_nodes == 1:
        recommendations['control_plane']['recommended_count'] = 1
        recommendations['control_plane']['notes'].append('Single Node OpenShift (SNO) configuration')
        recommendations['infra']['recommended_count'] = 0
        recommendations['storage']['recommended_count'] = 0
        recommendations['worker']['recommended_count'] = 0
    
    # Infra recommendations
    infra_rec = recommendations['infra']
    if infra_rec['current_count'] == 0 and summary.total_nodes > 3:
        infra_rec['notes'].append('No dedicated infra nodes - recommend adding for logging/monitoring')
        recommendations['overall']['warnings'].append('No dedicated infrastructure nodes detected')
    
    # Storage recommendations
    storage_rec = recommendations['storage']
    if storage_rec['current_count'] > 0 and storage_rec['current_memory'] < 65536:
        storage_rec['notes'].append('ODF recommends 64 GiB RAM per storage node')
    
    # Overall recommendations
    total_recommended = (
        recommendations['control_plane']['recommended_count'] +
        recommendations['infra']['recommended_count'] +
        recommendations['storage']['recommended_count'] +
        recommendations['worker']['recommended_count']
    )
    recommendations['overall']['total_recommended_nodes'] = max(1, total_recommended)
    
    # Identify opportunities
    if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0:
        recommendations['overall']['opportunities'].append(
            f"Low CPU utilization ({recommendations['overall']['efficiency_score']}%) - significant right-sizing opportunity")
    
    return recommendations


# =============================================================================
# HTML Report Generation
# =============================================================================

def generate_html_report(nodes: List[NodeData], summary: ClusterSummary, 
                        recommendations: Dict, pvs: List[PersistentVolume]) -> str:
    """Generate interactive HTML dashboard"""
    
    # Prepare data for charts
    nodes_json = []
    for node in nodes:
        role = categorize_node_role(node)
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
            'container_runtime': node.system_info.container_runtime
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
        role = categorize_node_role(node)
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
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCP Sizing Calculator - Assessment Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&family=Red+Hat+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --rh-red: #EE0000;
            --rh-red-dark: #A30000;
            --rh-red-light: #FF5C5C;
            --rh-black: #151515;
            --rh-gray-900: #212427;
            --rh-gray-800: #2D2D2D;
            --rh-gray-700: #3C3F42;
            --rh-gray-600: #4D5258;
            --rh-gray-500: #6A6E73;
            --rh-gray-400: #8A8D90;
            --rh-gray-300: #B8BBBE;
            --rh-gray-200: #D2D2D2;
            --rh-gray-100: #F0F0F0;
            --rh-white: #FFFFFF;
            --rh-blue: #0066CC;
            --rh-blue-light: #73BCF7;
            --rh-green: #3E8635;
            --rh-green-light: #95D58F;
            --rh-orange: #F0AB00;
            --rh-purple: #6753AC;
            --rh-cyan: #009596;
            
            --bg-primary: var(--rh-gray-900);
            --bg-secondary: var(--rh-gray-800);
            --bg-tertiary: var(--rh-gray-700);
            --text-primary: var(--rh-white);
            --text-secondary: var(--rh-gray-300);
            --text-muted: var(--rh-gray-400);
            --border-color: var(--rh-gray-600);
            --accent: var(--rh-red);
            --accent-hover: var(--rh-red-dark);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--rh-black) 0%, var(--rh-gray-900) 100%);
            border-bottom: 3px solid var(--rh-red);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .header-content {{
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .logo {{
            width: 50px;
            height: 50px;
            background: var(--rh-red);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .logo svg {{
            width: 30px;
            height: 30px;
            fill: white;
        }}
        
        .title-section h1 {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .title-section p {{
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        
        .header-meta {{
            text-align: right;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        
        /* Navigation Tabs */
        .nav-tabs {{
            background: var(--bg-secondary);
            padding: 0 2rem;
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        
        .nav-tabs-inner {{
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            gap: 0;
        }}
        
        .nav-tab {{
            padding: 1rem 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
            font-weight: 500;
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap;
            font-size: 0.9rem;
        }}
        
        .nav-tab:hover {{
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }}
        
        .nav-tab.active {{
            color: var(--rh-red);
            border-bottom-color: var(--rh-red);
        }}
        
        /* Main Content */
        .main-content {{
            max-width: 1800px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Filter Bar */
        .filter-bar {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
        }}
        
        .filter-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .filter-btn:hover {{
            background: var(--rh-gray-600);
            color: var(--text-primary);
        }}
        
        .filter-btn.active {{
            background: var(--rh-red);
            border-color: var(--rh-red);
            color: white;
        }}
        
        .filter-btn.active.control-plane {{ background: var(--rh-blue); border-color: var(--rh-blue); }}
        .filter-btn.active.infra {{ background: var(--rh-purple); border-color: var(--rh-purple); }}
        .filter-btn.active.storage {{ background: var(--rh-cyan); border-color: var(--rh-cyan); }}
        .filter-btn.active.worker {{ background: var(--rh-orange); border-color: var(--rh-orange); }}
        
        .filter-count {{
            background: rgba(255,255,255,0.2);
            padding: 0.1rem 0.5rem;
            border-radius: 100px;
            font-size: 0.7rem;
        }}
        
        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .summary-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        
        .summary-card.highlight {{
            border-color: var(--rh-red);
            background: linear-gradient(135deg, var(--bg-secondary) 0%, rgba(238,0,0,0.1) 100%);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }}
        
        .card-title {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .card-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }}
        
        .card-icon.nodes {{ background: rgba(0,102,204,0.2); color: var(--rh-blue); }}
        .card-icon.cpu {{ background: rgba(62,134,53,0.2); color: var(--rh-green); }}
        .card-icon.memory {{ background: rgba(103,83,172,0.2); color: var(--rh-purple); }}
        .card-icon.pods {{ background: rgba(240,171,0,0.2); color: var(--rh-orange); }}
        .card-icon.storage {{ background: rgba(0,149,150,0.2); color: var(--rh-cyan); }}
        .card-icon.efficiency {{ background: rgba(238,0,0,0.2); color: var(--rh-red); }}
        
        .card-value {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }}
        
        .card-subtitle {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}
        
        .card-detail {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border-color);
        }}
        
        /* Architecture Diagram */
        .architecture-diagram {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }}
        
        .architecture-title {{
            text-align: center;
            margin-bottom: 1.5rem;
        }}
        
        .architecture-title h3 {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            margin-bottom: 0.25rem;
        }}
        
        .architecture-title p {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        .architecture-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
        }}
        
        .arch-tier {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }}
        
        .arch-tier-label {{
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        
        .arch-tier-nodes {{
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .arch-connector {{
            width: 2px;
            height: 25px;
            background: linear-gradient(180deg, var(--rh-gray-600) 0%, var(--rh-gray-600) 50%, transparent 50%, transparent 100%);
            background-size: 2px 8px;
        }}
        
        .arch-connector-h {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 70%;
            height: 25px;
            position: relative;
        }}
        
        .arch-connector-h::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 15%;
            right: 15%;
            height: 2px;
            background: var(--rh-gray-600);
        }}
        
        .arch-connector-h::after {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 2px;
            height: 12px;
            background: var(--rh-gray-600);
        }}
        
        .arch-node-group {{
            background: var(--rh-gray-700);
            border-radius: 10px;
            padding: 1rem 1.5rem;
            text-align: center;
            border: 2px solid transparent;
            transition: all 0.2s;
            min-width: 130px;
        }}
        
        .arch-node-group:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }}
        
        .arch-node-group.control-plane {{
            border-color: var(--rh-blue);
            background: linear-gradient(135deg, rgba(0,102,204,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.infra {{
            border-color: var(--rh-purple);
            background: linear-gradient(135deg, rgba(103,83,172,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.storage {{
            border-color: var(--rh-cyan);
            background: linear-gradient(135deg, rgba(0,149,150,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.worker {{
            border-color: var(--rh-orange);
            background: linear-gradient(135deg, rgba(240,171,0,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group .icon {{
            font-size: 1.75rem;
            margin-bottom: 0.25rem;
        }}
        
        .arch-node-group .role {{
            font-family: 'Red Hat Display', sans-serif;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        
        .arch-node-group .count {{
            font-size: 1.75rem;
            font-weight: 700;
            font-family: 'Red Hat Display', sans-serif;
        }}
        
        .arch-node-group.control-plane .count {{ color: var(--rh-blue); }}
        .arch-node-group.infra .count {{ color: var(--rh-purple); }}
        .arch-node-group.storage .count {{ color: var(--rh-cyan); }}
        .arch-node-group.worker .count {{ color: var(--rh-orange); }}
        
        .arch-node-group .specs {{
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        
        .arch-node-group .node-names {{
            font-size: 0.65rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--rh-gray-600);
            max-width: 150px;
            word-wrap: break-word;
        }}
        
        .arch-middle-tier {{
            display: flex;
            justify-content: center;
            gap: 2rem;
        }}
        
        .arch-legend {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid var(--rh-gray-700);
            flex-wrap: wrap;
        }}
        
        .arch-legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .arch-legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 4px;
        }}
        
        .arch-legend-color.cp {{ background: var(--rh-blue); }}
        .arch-legend-color.infra {{ background: var(--rh-purple); }}
        .arch-legend-color.storage {{ background: var(--rh-cyan); }}
        .arch-legend-color.worker {{ background: var(--rh-orange); }}
        
        /* Charts Section */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .chart-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .chart-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        .chart-container.scrollable {{
            height: auto;
            max-height: 500px;
            overflow-y: auto;
        }}
        
        .chart-container.scrollable canvas {{
            min-height: 400px;
        }}
        
        /* Tables */
        .table-container {{
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}
        
        .table-header {{
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .table-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        
        .table-search {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 0.875rem;
            width: 250px;
        }}
        
        .table-search:focus {{
            outline: none;
            border-color: var(--rh-blue);
        }}
        
        .table-scroll {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}
        
        th {{
            background: var(--bg-tertiary);
            padding: 0.875rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
            white-space: nowrap;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        th:hover {{
            background: var(--rh-gray-600);
        }}
        
        td {{
            padding: 0.875rem 1rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-primary);
            white-space: nowrap;
        }}
        
        tr:hover td {{
            background: var(--bg-tertiary);
        }}
        
        tr.filtered-out {{
            display: none;
        }}
        
        /* Status badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        
        .badge-success {{ background: rgba(62,134,53,0.2); color: var(--rh-green-light); }}
        .badge-warning {{ background: rgba(240,171,0,0.2); color: var(--rh-orange); }}
        .badge-danger {{ background: rgba(238,0,0,0.2); color: var(--rh-red-light); }}
        .badge-info {{ background: rgba(0,102,204,0.2); color: var(--rh-blue-light); }}
        .badge-neutral {{ background: var(--bg-tertiary); color: var(--text-secondary); }}
        
        /* Role badges */
        .role-badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-right: 0.25rem;
            text-transform: uppercase;
        }}
        
        .role-control-plane {{ background: var(--rh-blue); color: white; }}
        .role-infra {{ background: var(--rh-purple); color: white; }}
        .role-storage {{ background: var(--rh-cyan); color: white; }}
        .role-worker {{ background: var(--rh-gray-600); color: white; }}
        
        /* Progress bars */
        .progress-bar {{
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.25rem;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .progress-low {{ background: var(--rh-green); }}
        .progress-medium {{ background: var(--rh-orange); }}
        .progress-high {{ background: var(--rh-red); }}
        
        /* Recommendations Section */
        .recommendations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }}
        
        .rec-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .rec-card-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .rec-icon {{
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }}
        
        .rec-card-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        .rec-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .rec-column {{
            text-align: center;
        }}
        
        .rec-column-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        
        .rec-column-value {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .rec-column-detail {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .rec-notes {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }}
        
        .rec-note {{
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .rec-note-icon {{
            color: var(--rh-orange);
        }}
        
        /* Warnings & Opportunities */
        .warnings-section {{
            background: rgba(238,0,0,0.1);
            border: 1px solid var(--rh-red);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        
        .warnings-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-red-light);
            margin-bottom: 1rem;
        }}
        
        .warning-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        
        .warning-icon {{
            color: var(--rh-orange);
            font-size: 1.25rem;
        }}
        
        .opportunities-section {{
            background: rgba(62,134,53,0.1);
            border: 1px solid var(--rh-green);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1.5rem;
        }}
        
        .opportunities-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-green-light);
            margin-bottom: 1rem;
        }}
        
        .opportunity-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        
        /* Checklist */
        .checklist {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .checklist-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .checklist-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .checklist-item:last-child {{
            border-bottom: none;
        }}
        
        .check-icon {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.875rem;
        }}
        
        .check-icon.pass {{ background: var(--rh-green); color: white; }}
        .check-icon.warn {{ background: var(--rh-orange); color: white; }}
        .check-icon.fail {{ background: var(--rh-red); color: white; }}
        .check-icon.info {{ background: var(--rh-blue); color: white; }}
        
        .check-text {{
            flex: 1;
        }}
        
        .check-label {{
            font-weight: 500;
        }}
        
        .check-detail {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        
        /* Section headers */
        .section-header {{
            margin-bottom: 1.5rem;
        }}
        
        .section-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .section-subtitle {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        /* No Data Available */
        .no-data {{
            text-align: center;
            padding: 4rem 2rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}
        
        .no-data-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }}
        
        .no-data-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }}
        
        .no-data-text {{
            color: var(--text-muted);
            font-size: 0.95rem;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 3rem;
            padding: 2rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        /* Export buttons */
        .export-buttons {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }}
        
        .btn {{
            padding: 0.625rem 1.25rem;
            border-radius: 6px;
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .btn-primary {{
            background: var(--rh-red);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: var(--rh-red-dark);
        }}
        
        .btn-secondary {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }}
        
        .btn-secondary:hover {{
            background: var(--rh-gray-600);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }}
            
            .header-meta {{
                text-align: center;
            }}
            
            .nav-tabs {{
                padding: 0 1rem;
            }}
            
            .nav-tab {{
                padding: 0.75rem 1rem;
                font-size: 0.8rem;
            }}
            
            .main-content {{
                padding: 1rem;
            }}
            
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            
            .filter-bar {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
    </style>
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
            <div class="nav-tab" data-tab="recommendations">OCP Recommendations</div>
            <div class="nav-tab" data-tab="checklist">Migration Checklist</div>
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
                
                <div class="summary-card highlight">
                    <div class="card-header">
                        <span class="card-title">CPU Efficiency</span>
                        <div class="card-icon efficiency">📊</div>
                    </div>
                    <div class="card-value">{recommendations['overall']['efficiency_score']:.1f}%</div>
                    <div class="card-subtitle">actual vs requested</div>
                    <div class="card-detail">
                        Requested: {round(summary.total_requested.cpu / 1000, 1)} cores |
                        Actual: {round(summary.total_actual.cpu / 1000, 1)} cores
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
                    <h3 class="chart-title">Resource Requests vs Actual Usage</h3>
                    <div class="chart-container">
                        <canvas id="requestsVsActualChart"></canvas>
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
                    <h3 class="table-title">All Nodes (<span id="nodesTableCount">{len(nodes)}</span>)</h3>
                    <input type="text" class="table-search" placeholder="Search nodes..." onkeyup="filterTable('nodesTable', this.value)">
                </div>
                <div class="table-scroll">
                    <table id="nodesTable">
                        <thead>
                            <tr>
                                <th onclick="sortTable('nodesTable', 0)">Node Name</th>
                                <th onclick="sortTable('nodesTable', 1)">Role</th>
                                <th onclick="sortTable('nodesTable', 2)">CPU (cores)</th>
                                <th onclick="sortTable('nodesTable', 3)">CPU Requested</th>
                                <th onclick="sortTable('nodesTable', 4)">CPU Actual</th>
                                <th onclick="sortTable('nodesTable', 5)">Memory (GiB)</th>
                                <th onclick="sortTable('nodesTable', 6)">Mem Requested</th>
                                <th onclick="sortTable('nodesTable', 7)">Mem Actual</th>
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
            
            <div class="summary-grid">
                <div class="summary-card highlight">
                    <div class="card-header">
                        <span class="card-title">CPU Over-Provisioning</span>
                        <div class="card-icon cpu">⚡</div>
                    </div>
                    <div class="card-value">{round((1 - summary.total_actual.cpu / max(summary.total_requested.cpu, 1)) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of requested CPU is unused</div>
                    <div class="card-detail">
                        {round(summary.total_requested.cpu / 1000, 1)} cores requested, {round(summary.total_actual.cpu / 1000, 1)} actually used
                    </div>
                </div>
                
                <div class="summary-card highlight">
                    <div class="card-header">
                        <span class="card-title">Memory Over-Provisioning</span>
                        <div class="card-icon memory">🧠</div>
                    </div>
                    <div class="card-value">{round((1 - summary.total_actual.memory / max(summary.total_requested.memory, 1)) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of requested memory is unused</div>
                    <div class="card-detail">
                        {round(summary.total_requested.memory / 1024, 1)} GiB requested, {round(summary.total_actual.memory / 1024, 1)} GiB actually used
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Right-Sizing Potential</span>
                        <div class="card-icon efficiency">💰</div>
                    </div>
                    <div class="card-value">~{max(0, summary.total_nodes - recommendations['overall']['total_recommended_nodes'])}</div>
                    <div class="card-subtitle">nodes could potentially be saved</div>
                    <div class="card-detail">
                        Current: {summary.total_nodes} → Optimized: {recommendations['overall']['total_recommended_nodes']}
                    </div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">CPU: Requested vs Actual per Node</h3>
                    <div class="chart-container">
                        <canvas id="cpuEfficiencyChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Memory: Requested vs Actual per Node</h3>
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
                                    <span class="badge {'badge-danger' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 20 else 'badge-warning' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 50 else 'badge-success'}">
                                        {round(n['cpu_actual']/max(n['cpu_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                                <td>{n['mem_requested']} GiB</td>
                                <td>{n['mem_actual']} GiB</td>
                                <td>
                                    <span class="badge {'badge-danger' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 20 else 'badge-warning' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 50 else 'badge-success'}">
                                        {round(n['mem_actual']/max(n['mem_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
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
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">Pods by Namespace (All {len(sorted_ns)} namespaces)</h3>
                    <div class="chart-container scrollable" id="namespaceChartContainer">
                        <canvas id="namespaceChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Pods per Node</h3>
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
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Recommendations Tab -->
        <div class="tab-content" id="recommendations">
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
        </div>
        
        <!-- Checklist Tab -->
        <div class="tab-content" id="checklist">
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
        </div>
        
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
        
        // Filter functionality
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
                }}
            }});
        }});
        
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
        
        // Requests vs Actual Chart
        new Chart(document.getElementById('requestsVsActualChart'), {{
            type: 'bar',
            data: {{
                labels: ['CPU (cores)', 'Memory (GiB)'],
                datasets: [
                    {{
                        label: 'Capacity',
                        data: [{round(summary.total_capacity.cpu / 1000, 1)}, {round(summary.total_capacity.memory / 1024, 1)}],
                        backgroundColor: colors.gray
                    }},
                    {{
                        label: 'Requested',
                        data: [{round(summary.total_requested.cpu / 1000, 1)}, {round(summary.total_requested.memory / 1024, 1)}],
                        backgroundColor: colors.blue
                    }},
                    {{
                        label: 'Actual Usage',
                        data: [{round(summary.total_actual.cpu / 1000, 1)}, {round(summary.total_actual.memory / 1024, 1)}],
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
        
        // CPU Efficiency Chart
        new Chart(document.getElementById('cpuEfficiencyChart'), {{
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
        
        // Memory Efficiency Chart
        new Chart(document.getElementById('memoryEfficiencyChart'), {{
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
        
        new Chart(nsCanvas, {{
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
        
        // Pods per Node Chart
        new Chart(document.getElementById('podsPerNodeChart'), {{
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

def main():
    parser = argparse.ArgumentParser(
        description='OCP Sizing Calculator - Analyze Kubernetes clusters for OpenShift migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -d nodes_describe.txt -t nodes_top.txt
  %(prog)s -d nodes_describe.txt -t nodes_top.txt -p pvs.txt -o report.html
        '''
    )
    
    parser.add_argument('-d', '--describe', required=True,
                        help='kubectl describe nodes output file (required)')
    parser.add_argument('-t', '--top', required=True,
                        help='kubectl top nodes output file (required)')
    parser.add_argument('-p', '--pvs',
                        help='kubectl get pv -o wide output file (optional)')
    parser.add_argument('-o', '--output', default='ocp_sizing_report.html',
                        help='Output HTML report filename (default: ocp_sizing_report.html)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("OCP Sizing Calculator v1.1")
    print("=" * 60)
    
    # Read input files
    print(f"\n📖 Reading describe nodes: {args.describe}")
    with open(args.describe, 'r') as f:
        describe_content = f.read()
    
    print(f"📖 Reading top nodes: {args.top}")
    with open(args.top, 'r') as f:
        top_content = f.read()
    
    pvs = []
    if args.pvs:
        print(f"📖 Reading PVs: {args.pvs}")
        with open(args.pvs, 'r') as f:
            pv_content = f.read()
        pvs = parse_pvs(pv_content)
        print(f"   Found {len(pvs)} persistent volumes")
    else:
        print("ℹ️  No PV file provided - storage analysis will show 'Data Not Available'")
    
    # Parse data
    print("\n🔍 Parsing node data...")
    nodes = parse_describe_nodes(describe_content)
    print(f"   Found {len(nodes)} nodes")
    
    top_data = parse_top_nodes(top_content)
    print(f"   Found {len(top_data)} nodes with metrics")
    
    # Merge data
    print("\n🔗 Merging describe and top data...")
    merge_top_data(nodes, top_data)
    
    # Calculate summary
    print("📊 Calculating cluster summary...")
    summary = calculate_cluster_summary(nodes, pvs)
    
    # Generate recommendations
    print("💡 Generating OpenShift recommendations...")
    recommendations = generate_ocp_recommendations(nodes, summary)
    
    # Generate report
    print(f"\n📝 Generating HTML report: {args.output}")
    html = generate_html_report(nodes, summary, recommendations, pvs)
    
    with open(args.output, 'w') as f:
        f.write(html)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Nodes:          {summary.total_nodes}")
    print(f"  - Control Plane:    {summary.nodes_by_role.get('control-plane', 0)}")
    print(f"  - Infrastructure:   {summary.nodes_by_role.get('infra', 0)}")
    print(f"  - Storage:          {summary.nodes_by_role.get('storage', 0)}")
    print(f"  - Workers:          {summary.nodes_by_role.get('worker', 0)}")
    print(f"Total CPU Capacity:   {summary.total_capacity.cpu / 1000:.0f} cores")
    print(f"Total Memory:         {summary.total_capacity.memory / 1024:.0f} GiB")
    print(f"Total Pods:           {summary.total_pods}")
    print(f"Efficiency Score:     {recommendations['overall']['efficiency_score']:.1f}%")
    print(f"\nRecommended OCP Nodes: {recommendations['overall']['total_recommended_nodes']}")
    print(f"Potential Savings:    {max(0, summary.total_nodes - recommendations['overall']['total_recommended_nodes'])} nodes")
    print("\n" + "=" * 60)
    print(f"✅ Report generated: {args.output}")
    print("=" * 60)


if __name__ == '__main__':
    main()
