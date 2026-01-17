"""
nodes_parser.py
---------------
Parse kubectl describe nodes output.

Extracts comprehensive node information including:
- Node metadata (name, roles, labels, taints)
- Resource capacity and allocatable
- Resource requests and limits
- Pod information
- Node conditions and system info
"""

import re
from typing import List

from models import (
    NodeData, PodInfo, NodeCondition, SystemInfo, ResourceSpec
)
from parsers.utils import parse_cpu, parse_memory, parse_storage


def parse_describe_nodes(content: str) -> List[NodeData]:
    """
    Parse kubectl describe nodes output.
    
    Args:
        content: Full text output from 'kubectl describe nodes'
        
    Returns:
        List of NodeData objects
    """
    nodes = []
    
    # Split by node blocks (each starts with "Name:")
    node_blocks = re.split(r'\n(?=Name:\s+\S)', content)
    
    for block in node_blocks:
        if not block.strip() or not block.strip().startswith('Name:'):
            continue
        
        node = _parse_node_block(block)
        if node.name:
            nodes.append(node)
    
    # Deduplicate nodes (file might have duplicates)
    return _deduplicate_nodes(nodes)


def _parse_node_block(block: str) -> NodeData:
    """
    Parse a single node block from describe output.
    
    Args:
        block: Text block for one node
        
    Returns:
        NodeData object
    """
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
            i = _parse_labels(lines, i, node)
            continue
        
        # Taints
        elif line.startswith('Taints:'):
            i = _parse_taints(lines, i, node)
            continue
        
        # Creation timestamp
        elif line.startswith('CreationTimestamp:'):
            node.creation_timestamp = line.split(':', 1)[1].strip()
        
        # Unschedulable
        elif line.startswith('Unschedulable:'):
            node.is_schedulable = line.split(':', 1)[1].strip().lower() != 'true'
        
        # Addresses - extract IP
        elif line.startswith('Addresses:'):
            i = _parse_addresses(lines, i, node)
            continue
        
        # Capacity
        elif line.startswith('Capacity:'):
            i = _parse_capacity(lines, i, node)
            continue
        
        # Allocatable
        elif line.startswith('Allocatable:'):
            i = _parse_allocatable(lines, i, node)
            continue
        
        # System Info
        elif line.startswith('System Info:'):
            i = _parse_system_info(lines, i, node)
            continue
        
        # Provider ID
        elif line.startswith('ProviderID:'):
            node.provider_id = line.split(':', 1)[1].strip()
        
        # Non-terminated Pods
        elif line.startswith('Non-terminated Pods:'):
            i = _parse_pods(lines, i, node)
            continue
        
        # Allocated resources
        elif line.startswith('Allocated resources:'):
            i = _parse_allocated_resources(lines, i, node)
            continue
        
        # Conditions
        elif line.startswith('Conditions:'):
            i = _parse_conditions(lines, i, node)
            continue
        
        i += 1
    
    return node


def _parse_labels(lines: List[str], i: int, node: NodeData) -> int:
    """Parse labels section."""
    label_str = lines[i].split(':', 1)[1].strip()
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
    
    # Extract instance type from labels
    for key in node.labels:
        if 'instance-type' in key:
            node.instance_type = node.labels[key]
            break
    
    return i


def _parse_taints(lines: List[str], i: int, node: NodeData) -> int:
    """Parse taints section."""
    taint_str = lines[i].split(':', 1)[1].strip()
    if taint_str and taint_str != '<none>':
        node.taints.append(taint_str)
    
    i += 1
    while i < len(lines) and lines[i].startswith(' ') and not lines[i].strip().startswith(('Unschedulable', 'Lease')):
        taint_line = lines[i].strip()
        if taint_line and taint_line != '<none>':
            node.taints.append(taint_line)
        i += 1
    
    return i


def _parse_addresses(lines: List[str], i: int, node: NodeData) -> int:
    """Parse addresses section to extract IP."""
    i += 1
    while i < len(lines) and lines[i].startswith(' '):
        addr_line = lines[i].strip()
        if addr_line.startswith('InternalIP:'):
            node.ip_address = addr_line.split(':', 1)[1].strip()
        i += 1
    
    return i


def _parse_capacity(lines: List[str], i: int, node: NodeData) -> int:
    """Parse capacity section."""
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
    
    return i


def _parse_allocatable(lines: List[str], i: int, node: NodeData) -> int:
    """Parse allocatable section."""
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
    
    return i


def _parse_system_info(lines: List[str], i: int, node: NodeData) -> int:
    """Parse system info section."""
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
    
    return i


def _parse_pods(lines: List[str], i: int, node: NodeData) -> int:
    """Parse non-terminated pods section."""
    match = re.search(r'\((\d+)\s+in total\)', lines[i])
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
    
    return i


def _parse_allocated_resources(lines: List[str], i: int, node: NodeData) -> int:
    """Parse allocated resources section."""
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
    
    return i


def _parse_conditions(lines: List[str], i: int, node: NodeData) -> int:
    """Parse conditions section."""
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
    
    return i


def _deduplicate_nodes(nodes: List[NodeData]) -> List[NodeData]:
    """
    Remove duplicate nodes (file might have duplicates).
    
    Args:
        nodes: List of NodeData objects
        
    Returns:
        Deduplicated list of NodeData objects
    """
    seen = set()
    unique_nodes = []
    
    for node in nodes:
        if node.name not in seen:
            seen.add(node.name)
            unique_nodes.append(node)
    
    return unique_nodes
