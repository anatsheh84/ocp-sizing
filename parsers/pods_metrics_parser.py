"""
pods_metrics_parser.py
----------------------
Parse kubectl top pods -A output.

Extracts per-pod actual resource usage:
- Namespace
- Pod name
- CPU usage (millicores)
- Memory usage (MiB)
"""

from typing import Dict, Tuple

from parsers.utils import parse_cpu, parse_memory


def parse_top_pods(content: str) -> Dict[Tuple[str, str], Tuple[float, float]]:
    """
    Parse kubectl top pods -A output.
    
    Args:
        content: Full text output from 'kubectl top pods -A'
        
    Returns:
        Dictionary mapping (namespace, pod_name) to (cpu_millicores, memory_mib)
        
    Example:
        {
            ('kube-system', 'coredns-5d685c6f4b-csrln'): (100.0, 42.0),
            ('naba', 'jobs-5977799bcd-4b279'): (450.0, 2100.0),
        }
    """
    usage = {}
    lines = content.strip().split('\n')
    
    for line in lines:
        # Skip header line
        if line.startswith('NAMESPACE') or not line.strip():
            continue
        
        parts = line.split()
        if len(parts) >= 4:
            namespace = parts[0]
            pod_name = parts[1]
            cpu_m = parse_cpu(parts[2])
            mem_mb = parse_memory(parts[3])
            
            usage[(namespace, pod_name)] = (cpu_m, mem_mb)
    
    return usage
