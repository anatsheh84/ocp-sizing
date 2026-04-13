"""
sources package
---------------
Contains source-specific data processors for different virtualization platforms.
"""

from .base_processor import BaseProcessor
from .rhv_processor import RHVProcessor
from .vmware_processor import VMwareProcessor

__all__ = [
    'BaseProcessor',
    'RHVProcessor',
    'VMwareProcessor'
]

def get_processor(source_type):
    """
    Factory function to get the appropriate processor for a source type.
    
    Args:
        source_type: 'rhv' or 'vmware'
        
    Returns:
        Processor instance
    """
    processors = {
        'rhv': RHVProcessor,
        'vmware': VMwareProcessor
    }
    
    if source_type not in processors:
        raise ValueError(f"Unknown source type: {source_type}. Supported: {list(processors.keys())}")
    
    return processors[source_type]()
