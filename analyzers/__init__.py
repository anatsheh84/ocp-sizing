"""
analyzers package
-----------------
Analysis and recommendation engines for OCP Sizing Calculator.

Modules:
- cluster_analyzer: Cluster-wide analysis
- recommendation_engine: OCP sizing recommendations

Note: Data models have been moved to the shared 'models' package.
"""

from models import (
    ResourceSpec,
    PodInfo,
    NodeCondition,
    SystemInfo,
    NodeData,
    PersistentVolume,
    ClusterSummary
)
from .cluster_analyzer import ClusterAnalyzer
from .recommendation_engine import RecommendationEngine
from .workload_analyzer import analyze_workloads

__all__ = [
    'ResourceSpec',
    'PodInfo',
    'NodeCondition',
    'SystemInfo',
    'NodeData',
    'PersistentVolume',
    'ClusterSummary',
    'ClusterAnalyzer',
    'RecommendationEngine',
    'analyze_workloads'
]
