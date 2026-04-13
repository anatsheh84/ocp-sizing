"""
rhv_processor.py
----------------
Processor for Red Hat Virtualization (RHV/oVirt) Excel exports.
"""

import pandas as pd
from .base_processor import BaseProcessor


# Column mapping: expected name -> possible variations in Excel
RHV_COLUMN_MAPPING = {
    'vm_name': ['vm_name', 'name', 'vm'],
    'cluster_name': ['cluster_name', 'cluster'],
    'storage_pool_name': ['storage_pool_name', 'storage_pool', 'storage_domain'],
    'guest_os': ['guest_os', 'os', 'operating_system'],
    'vm_host': ['vm_host', 'host', 'hypervisor'],
    'status': ['On/Off', 'status', 'power_state', 'state'],
    'mem_size_GB': ['mem_size_GB', 'memory', 'ram', 'mem_gb'],
    'num_of_cpus': ['num_of_cpus', 'vcpus', 'cpus', 'cpu'],
    'storage_size_GB': ['storage_size-GB', 'storage_size_GB', 'provisioned_storage', 'storage'],
    'used_size_GB': ['used_size-GB', 'used_size_GB', 'used_storage'],
    'creation_date': ['creation_date', 'created', 'create_date']
}


class RHVProcessor(BaseProcessor):
    """Processor for Red Hat Virtualization exports."""
    
    @property
    def source_name(self) -> str:
        return 'rhv'
    
    @property
    def source_display_name(self) -> str:
        return 'Red Hat Virtualization'
    
    @property
    def has_date_data(self) -> bool:
        return True
    
    def _find_column(self, df_columns, expected_name):
        """Find matching column from possible variations."""
        variations = RHV_COLUMN_MAPPING.get(expected_name, [expected_name])
        for var in variations:
            for col in df_columns:
                if col.lower().strip() == var.lower().strip():
                    return col
        return None
    
    def load_and_normalize(self, filepath: str) -> pd.DataFrame:
        """Load RHV Excel file and normalize to standard schema."""
        df = pd.read_excel(filepath)
        
        # Map columns to standardized names
        column_map = {}
        for std_name in RHV_COLUMN_MAPPING.keys():
            found = self._find_column(df.columns, std_name)
            if found:
                column_map[found] = std_name
        
        df = df.rename(columns=column_map)
        
        # Clean data
        df = self._clean_data(df)
        
        return df

    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out invalid rows and handle data types."""
        # Remove rows without vm_name
        df = df[df['vm_name'].notna() & (df['vm_name'] != '')]
        
        # Remove potential total/summary rows
        if len(df) > 1 and 'mem_size_GB' in df.columns:
            mem_threshold = df['mem_size_GB'].quantile(0.99) * 10
            df = df[df['mem_size_GB'] <= mem_threshold]
        
        # Ensure numeric columns (with fallback for missing columns)
        if 'mem_size_GB' in df.columns:
            df['mem_size_GB'] = pd.to_numeric(df['mem_size_GB'], errors='coerce').fillna(0).astype(int)
        else:
            df['mem_size_GB'] = 0
            
        if 'num_of_cpus' in df.columns:
            df['num_of_cpus'] = pd.to_numeric(df['num_of_cpus'], errors='coerce').fillna(0).astype(int)
        else:
            df['num_of_cpus'] = 0
            
        if 'storage_size_GB' in df.columns:
            df['storage_size_GB'] = pd.to_numeric(df['storage_size_GB'], errors='coerce').fillna(0)
        else:
            df['storage_size_GB'] = 0.0
            
        if 'used_size_GB' in df.columns:
            df['used_size_GB'] = pd.to_numeric(df['used_size_GB'], errors='coerce').fillna(0)
        else:
            df['used_size_GB'] = 0.0
        
        # Parse dates
        if 'creation_date' in df.columns:
            df['creation_date'] = pd.to_datetime(df['creation_date'], errors='coerce')
        else:
            df['creation_date'] = pd.NaT
        
        # Ensure status column exists
        if 'status' not in df.columns:
            df['status'] = 'Unknown'
        
        # Ensure guest_os column exists
        if 'guest_os' not in df.columns:
            df['guest_os'] = 'Unknown'
            
        # Ensure vm_host column exists
        if 'vm_host' not in df.columns:
            df['vm_host'] = 'Unknown'
            
        # Ensure cluster_name column exists
        if 'cluster_name' not in df.columns:
            df['cluster_name'] = 'Unknown'
        
        return df.reset_index(drop=True)


# For testing
if __name__ == '__main__':
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python rhv_processor.py <excel_file>")
        sys.exit(1)
    
    processor = RHVProcessor()
    data = processor.process(sys.argv[1])
    
    print(f"\n{'='*50}")
    print(f"RHV PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Source: {data['source_display_name']}")
    print(f"Total VMs: {data['stats']['total_vms']}")
    print(f"Total vCPUs: {data['stats']['total_vcpus']}")
    print(f"Total Memory: {data['stats']['total_memory_gb']} GB")
    print(f"Has Date Data: {data['has_date_data']}")
