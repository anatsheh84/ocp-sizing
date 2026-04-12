"""
cluster_analyzer.py
-------------------
Cluster-wide analysis and summary calculations.

Provides:
- Node role categorization
- Cluster summary statistics
- Resource aggregation
- Metrics merging
"""

from typing import List, Dict, Tuple
from models import NodeData, PersistentVolume, ClusterSummary, ResourceSpec


class ClusterAnalyzer:
    """
    Analyzes Kubernetes cluster data to produce summary statistics.
    """
    
    def __init__(self, nodes: List[NodeData], pvs: List[PersistentVolume] = None):
        """
        Initialize analyzer with node and storage data.
        
        Args:
            nodes: List of NodeData objects
            pvs: List of PersistentVolume objects (optional)
        """
        self.nodes = nodes
        self.pvs = pvs or []
    
    def merge_metrics(self, top_data: Dict[str, Tuple[float, float, float, float]]):
        """
        Merge kubectl top nodes data into node objects.
        
        Args:
            top_data: Dict mapping node_name to (cpu, cpu_pct, mem, mem_pct)
        """
        for node in self.nodes:
            if node.name in top_data:
                cpu, cpu_pct, mem, mem_pct = top_data[node.name]
                node.actual_usage.cpu = cpu
                node.actual_usage.memory = mem
    
    def calculate_summary(self) -> ClusterSummary:
        """
        Calculate cluster-wide summary statistics.
        
        Returns:
            ClusterSummary object with aggregated statistics
        """
        summary = ClusterSummary()
        summary.total_nodes = len(self.nodes)
        
        for node in self.nodes:
            # Count by role
            role = self.categorize_node_role(node)
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
                summary.provider = self._detect_provider(node.provider_id)
        
        # PV summary
        for pv in self.pvs:
            summary.total_pv_count += 1
            summary.total_pv_capacity += pv.capacity
            if pv.storage_class:
                summary.storage_classes.add(pv.storage_class)
        
        return summary
    
    @staticmethod
    def categorize_node_role(node: NodeData) -> str:
        """
        Categorize node into primary role.
        
        Args:
            node: NodeData object
            
        Returns:
            Role string: 'control-plane', 'infra', 'storage', or 'worker'
        """
        roles = [r.lower() for r in node.roles]
        
        if 'master' in roles or 'control-plane' in roles:
            return 'control-plane'
        elif 'infra' in roles:
            return 'infra'
        elif 'storage' in roles:
            return 'storage'
        else:
            return 'worker'
    
    @staticmethod
    def _detect_provider(provider_id: str) -> str:
        """
        Detect cloud provider from provider ID.
        
        Args:
            provider_id: Provider ID string from node
            
        Returns:
            Provider name string
        """
        provider_id_lower = provider_id.lower()
        
        if 'vsphere' in provider_id_lower:
            return 'VMware vSphere'
        elif 'aws' in provider_id_lower:
            return 'AWS'
        elif 'azure' in provider_id_lower:
            return 'Azure'
        elif 'gce' in provider_id_lower:
            return 'Google Cloud'
        else:
            return 'Unknown'
