"""
data_processor.py
-----------------
Dispatcher module for source-specific processors.
Routes processing to the appropriate source handler.
"""

from sources import get_processor
from sources.rhv_hosts_processor import RHVHostsProcessor


def process_excel(filepath, source='rhv'):
    """
    Process virtualization export file.
    
    Args:
        filepath: Path to the export file
        source: Source platform ('rhv' or 'vmware')
        
    Returns:
        Dictionary with all data needed by dashboard tabs (including host_data)
    """
    # Process VM data
    processor = get_processor(source)
    vm_data = processor.process(filepath)
    
    # Process host data (if available in second sheet)
    host_data = {}
    if source == 'rhv':
        try:
            hosts_processor = RHVHostsProcessor()
            host_data = hosts_processor.process(filepath, vm_data=vm_data)
        except Exception as e:
            # Host data not available - continue without it
            host_data = {
                'has_host_data': False,
                'stats': {},
                'distributions': {},
                'host_list': [],
                'unique_clusters': [],
                'error': str(e)
            }
    else:
        # Other sources don't have host data yet
        host_data = {
            'has_host_data': False,
            'stats': {},
            'distributions': {},
            'host_list': [],
            'unique_clusters': []
        }
    
    # Merge VM and host data
    vm_data['host_data'] = host_data
    
    return vm_data


# For backward compatibility
def process_rhv(filepath):
    """Process RHV export (backward compatible)."""
    return process_excel(filepath, source='rhv')


def process_vmware(filepath):
    """Process VMware/RVTools export."""
    return process_excel(filepath, source='vmware')


# For testing
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python data_processor.py <source> <excel_file>")
        print("  source: rhv | vmware")
        sys.exit(1)
    
    source = sys.argv[1]
    filepath = sys.argv[2]
    
    data = process_excel(filepath, source=source)
    
    print(f"\n{'='*50}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Source: {data['source_display_name']}")
    print(f"Total VMs: {data['stats']['total_vms']}")
    print(f"Total vCPUs: {data['stats']['total_vcpus']}")
    print(f"Total Memory: {data['stats']['total_memory_gb']} GB")
    print(f"Has Date Data: {data['has_date_data']}")
    
    # Show host data if available
    if data.get('host_data', {}).get('has_host_data', False):
        host_stats = data['host_data']['stats']
        print(f"\n{'='*50}")
        print(f"HOST INFORMATION")
        print(f"{'='*50}")
        print(f"Total Hosts: {host_stats.get('total_hosts', 0)}")
        print(f"Total vCores: {host_stats.get('total_vcores', 0):,}")
        print(f"Avg CPU Overcommit: {host_stats.get('avg_cpu_overcommit', 0)}x")
    else:
        print(f"\nHost data: Not available")
