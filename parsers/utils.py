"""
utils.py
--------
Parsing utility functions for unit conversions.

Functions to parse Kubernetes resource strings:
- parse_cpu: Convert CPU strings to millicores
- parse_memory: Convert memory strings to MiB
- parse_storage: Convert storage strings to GiB
- parse_percentage: Extract percentage values
"""

import re


def parse_cpu(value: str) -> float:
    """
    Parse CPU value to millicores.
    
    Examples:
        "2" -> 2000.0 (2 cores)
        "500m" -> 500.0 (500 millicores)
        "1500000n" -> 1.5 (nanocores to millicores)
    
    Args:
        value: CPU value string
        
    Returns:
        CPU in millicores
    """
    if not value or value == "0":
        return 0.0
    
    value = value.strip()
    
    if value.endswith('m'):
        # Millicores
        return float(value[:-1])
    elif value.endswith('n'):
        # Nanocores
        return float(value[:-1]) / 1_000_000
    else:
        # Cores
        return float(value) * 1000


def parse_memory(value: str) -> float:
    """
    Parse memory value to MiB (Mebibytes).
    
    Examples:
        "1Gi" -> 1024.0 MiB
        "512Mi" -> 512.0 MiB
        "1073741824" -> 1024.0 MiB (bytes)
    
    Args:
        value: Memory value string
        
    Returns:
        Memory in MiB
    """
    if not value or value == "0":
        return 0.0
    
    value = value.strip()
    
    # Binary units (Ki, Mi, Gi, Ti)
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
    
    # Assume bytes if no unit
    try:
        return float(value) / (1024 * 1024)
    except:
        return 0.0


def parse_storage(value: str) -> float:
    """
    Parse storage value to GiB (Gibibytes).
    
    Examples:
        "100Gi" -> 100.0 GiB
        "1Ti" -> 1024.0 GiB
        "512Mi" -> 0.5 GiB
    
    Args:
        value: Storage value string
        
    Returns:
        Storage in GiB
    """
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
    
    # Assume bytes if no unit
    try:
        return float(value) / (1024**3)
    except:
        return 0.0


def parse_percentage(value: str) -> float:
    """
    Parse percentage string to float.
    
    Examples:
        "45%" -> 45.0
        "12.5%" -> 12.5
    
    Args:
        value: Percentage string
        
    Returns:
        Percentage value as float
    """
    if not value:
        return 0.0
    
    match = re.search(r'(\d+\.?\d*)%', value)
    if match:
        return float(match.group(1))
    
    return 0.0
