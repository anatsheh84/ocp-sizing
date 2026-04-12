"""
storage_parser.py
-----------------
Parse kubectl get pv output.

Extracts persistent volume information:
- Volume name and capacity
- Access modes and reclaim policy
- Status and claims
- Storage class
"""

from typing import List

from models import PersistentVolume
from parsers.utils import parse_storage


def parse_pvs(content: str) -> List[PersistentVolume]:
    """
    Parse kubectl get pv -o wide output.
    
    Args:
        content: Full text output from 'kubectl get pv -o wide'
        
    Returns:
        List of PersistentVolume objects
        
    Example output format:
        NAME        CAPACITY   ACCESS   RECLAIM   STATUS   CLAIM        STORAGECLASS
        pv-001      10Gi       RWO      Retain    Bound    ns/pvc-001   fast
    """
    pvs = []
    lines = content.strip().split('\n')
    
    for line in lines:
        # Skip header line
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
