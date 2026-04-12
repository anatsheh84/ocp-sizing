"""
models package
--------------
Data class definitions for OCP Sizing Calculator.

All data structures used throughout the analysis:
- ResourceSpec: CPU, Memory, Storage, Pods
- PodInfo: Pod information from nodes
- NodeCondition: Node health conditions
- SystemInfo: Node system information
- NodeData: Complete node data structure
- PersistentVolume: Storage volume information
- ClusterSummary: Cluster-wide statistics
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


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


__all__ = [
    'ResourceSpec',
    'PodInfo',
    'NodeCondition',
    'SystemInfo',
    'NodeData',
    'PersistentVolume',
    'ClusterSummary'
]
