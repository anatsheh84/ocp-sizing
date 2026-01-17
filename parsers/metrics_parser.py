"""
metrics_parser.py
-----------------
Parse kubectl top nodes output.

Extracts actual resource usage metrics:
- CPU usage (cores and percentage)
- Memory usage (MiB and percentage)
"""

from typing import Dict, Tuple

from parsers.utils import parse_cpu, parse_memory, parse_percentage


def parse_top_nodes(content: str) -> Dict[str, Tuple[float, float, float, float]]:
    """
    Parse kubectl top nodes output.
    
    Args:
        content: Full text output from 'kubectl top nodes'
        
    Returns:
        Dictionary mapping node_name to (cpu_cores, cpu_percent, memory_mib, memory_percent)
        
    Example:
        {
            'node-1': (2500.0, 25.0, 4096.0, 32.0),
            'node-2': (1800.0, 18.0, 3072.0, 24.0)
        }
    """
    usage = {}
    lines = content.strip().split('\n')
    
    for line in lines:
        # Skip header line
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
