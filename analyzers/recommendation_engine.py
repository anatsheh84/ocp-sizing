"""
recommendation_engine.py
------------------------
OpenShift sizing recommendations based on Kubernetes cluster analysis.

Generates node count and sizing recommendations for:
- Control Plane nodes
- Infrastructure nodes
- Storage nodes (ODF)
- Worker nodes
"""

from typing import List, Dict
from models import NodeData, ClusterSummary
from .cluster_analyzer import ClusterAnalyzer


class RecommendationEngine:
    """
    Generates OpenShift cluster sizing recommendations.
    """
    
    def __init__(self, nodes: List[NodeData], summary: ClusterSummary):
        """
        Initialize recommendation engine.
        
        Args:
            nodes: List of NodeData objects
            summary: ClusterSummary object
        """
        self.nodes = nodes
        self.summary = summary
        self.analyzer = ClusterAnalyzer(nodes)
    
    def generate_recommendations(self) -> Dict:
        """
        Generate complete OCP sizing recommendations.
        
        Returns:
            Dictionary with recommendations per role and overall summary
        """
        recommendations = self._initialize_recommendations()
        
        # Categorize current nodes
        self._categorize_current_nodes(recommendations)
        
        # Generate role-specific recommendations
        self._recommend_control_plane(recommendations)
        self._recommend_infra(recommendations)
        self._recommend_storage(recommendations)
        self._recommend_workers(recommendations)
        
        # Calculate overall metrics
        self._calculate_overall(recommendations)
        
        return recommendations
    
    def _initialize_recommendations(self) -> Dict:
        """Initialize recommendations structure."""
        return {
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
                'total_current_nodes': len(self.nodes),
                'total_recommended_nodes': 0,
                'efficiency_score': 0,
                'warnings': [],
                'opportunities': []
            }
        }
    
    def _categorize_current_nodes(self, recommendations: Dict):
        """Categorize current nodes by role and collect stats."""
        for node in self.nodes:
            role = self.analyzer.categorize_node_role(node)
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
    
    def _recommend_control_plane(self, recommendations: Dict):
        """Generate control plane recommendations."""
        cp_rec = recommendations['control_plane']
        
        # Handle single-node cluster
        if self.summary.total_nodes == 1:
            cp_rec['recommended_count'] = 1
            cp_rec['notes'].append('Single Node OpenShift (SNO) configuration')
            return
        
        # Handle small clusters (2-3 nodes)
        if self.summary.total_nodes <= 3:
            cp_rec['recommended_count'] = min(3, self.summary.total_nodes)
        
        # Check memory adequacy
        if cp_rec['current_count'] > 0:
            if cp_rec['current_memory'] < 16384:
                cp_rec['notes'].append('Memory below recommended 16 GiB minimum')
            if cp_rec['current_memory'] < 32768 and self.summary.total_nodes > 3:
                cp_rec['notes'].append('Consider 32 GiB for production clusters')
    
    def _recommend_infra(self, recommendations: Dict):
        """Generate infrastructure node recommendations."""
        infra_rec = recommendations['infra']
        
        # Small clusters don't need dedicated infra
        if self.summary.total_nodes <= 3:
            infra_rec['recommended_count'] = 0
            infra_rec['notes'].append(
                'Small cluster - infra workloads can run on control plane or workers')
            return
        
        # No current infra nodes
        if infra_rec['current_count'] == 0 and self.summary.total_nodes > 3:
            infra_rec['notes'].append(
                'No dedicated infra nodes - recommend adding for logging/monitoring')
            recommendations['overall']['warnings'].append(
                'No dedicated infrastructure nodes detected')
    
    def _recommend_storage(self, recommendations: Dict):
        """Generate storage node recommendations."""
        storage_rec = recommendations['storage']
        
        # Small clusters - recommend external storage
        if self.summary.total_nodes <= 3:
            storage_rec['recommended_count'] = 0
            storage_rec['notes'].append(
                'Small cluster - consider external storage or hosted storage service')
            return
        
        # Check memory for ODF
        if storage_rec['current_count'] > 0 and storage_rec['current_memory'] < 65536:
            storage_rec['notes'].append('ODF recommends 64 GiB RAM per storage node')
    
    def _recommend_workers(self, recommendations: Dict):
        """Generate worker node recommendations."""
        worker_rec = recommendations['worker']
        
        # No workers in compact cluster
        if worker_rec['current_count'] == 0:
            if self.summary.total_nodes > 0:
                worker_rec['notes'].append(
                    'No dedicated worker nodes - workloads run on control plane')
            return
        
        # Calculate based on actual usage with 2x headroom
        actual_cpu = worker_rec['actual_cpu_used']
        actual_mem = worker_rec['actual_memory_used']
        
        # Optimized sizing: actual usage * 2 buffer
        opt_cpu_needed = actual_cpu * 2
        opt_mem_needed = actual_mem * 2
        
        # Standard OpenShift worker: 16 cores, 64GB
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
    
    def _calculate_overall(self, recommendations: Dict):
        """Calculate overall recommendations and identify opportunities."""
        overall = recommendations['overall']
        
        # Calculate total recommended nodes
        total_recommended = (
            recommendations['control_plane']['recommended_count'] +
            recommendations['infra']['recommended_count'] +
            recommendations['storage']['recommended_count'] +
            recommendations['worker']['recommended_count']
        )
        overall['total_recommended_nodes'] = max(1, total_recommended)
        
        # Identify opportunities
        efficiency_score = overall['efficiency_score']
        if efficiency_score < 30 and efficiency_score > 0:
            overall['opportunities'].append(
                f"Low CPU utilization ({efficiency_score}%) - significant right-sizing opportunity")
