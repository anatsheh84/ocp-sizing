"""
vmware_processor.py
-------------------
Processor for VMware vSphere exports (RVTools format).
Dynamically detects and uses creation date if available.
"""

import pandas as pd
from .base_processor import BaseProcessor


# Possible column names for creation date in RVTools exports
CREATION_DATE_COLUMNS = [
    'Creation Date',
    'CreationDate', 
    'Created',
    'Create Date',
    'VM Created',
    'Annotation',  # Sometimes contains date info
]


class VMwareProcessor(BaseProcessor):
    """Processor for VMware/RVTools vInfo exports."""
    
    def __init__(self):
        self._has_date_data = False  # Will be set dynamically during load
    
    @property
    def source_name(self) -> str:
        return 'vmware'
    
    @property
    def source_display_name(self) -> str:
        return 'VMware vSphere'
    
    @property
    def has_date_data(self) -> bool:
        return self._has_date_data
    
    def load_and_normalize(self, filepath: str) -> pd.DataFrame:
        """Load RVTools vInfo sheet and normalize to standard schema."""
        # Try to load vInfo sheet, fallback to first sheet
        try:
            df = pd.read_excel(filepath, sheet_name='vInfo')
        except ValueError:
            # vInfo sheet not found, try first sheet
            df = pd.read_excel(filepath)
        
        # Filter out templates
        if 'Template' in df.columns:
            df = df[df['Template'] == False]
        
        # Normalize column names
        df = self._normalize_columns(df)
        
        # Clean and convert data (including date detection)
        df = self._clean_data(df)
        
        return df
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize RVTools column names to standard schema."""
        # RVTools column mapping
        column_map = {
            'VM': 'vm_name',
            'Cluster': 'cluster_name',
            'Datacenter': 'datacenter',
            'Host': 'vm_host',
            'CPUs': 'num_of_cpus',
            'OS according to the VMware Tools': 'guest_os',
            'OS according to the configuration file': 'guest_os_config',
            'Powerstate': 'power_state',
            'Memory': 'memory_mb',
            'Provisioned MB': 'storage_provisioned_mb',
            'In Use MB': 'storage_used_mb'
        }
        
        # Rename columns that exist
        rename_map = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_map)
        
        return df
    
    def _find_creation_date_column(self, df: pd.DataFrame) -> str:
        """Find the creation date column if it exists."""
        # Check for known column names (case-insensitive)
        df_columns_lower = {col.lower(): col for col in df.columns}
        
        for candidate in CREATION_DATE_COLUMNS:
            if candidate.lower() in df_columns_lower:
                return df_columns_lower[candidate.lower()]
        
        # Also check for columns containing 'creat' and 'date'
        for col in df.columns:
            col_lower = col.lower()
            if 'creat' in col_lower and 'date' in col_lower:
                return col
        
        return None

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert VMware data to standard format."""
        # Remove rows without vm_name
        df = df[df['vm_name'].notna() & (df['vm_name'] != '')]
        
        # Use guest_os from VMware Tools, fallback to config file
        if 'guest_os' not in df.columns and 'guest_os_config' in df.columns:
            df['guest_os'] = df['guest_os_config']
        elif 'guest_os' in df.columns and 'guest_os_config' in df.columns:
            df['guest_os'] = df['guest_os'].fillna(df['guest_os_config'])
        
        # Convert memory (MB → GB)
        if 'memory_mb' in df.columns:
            df['mem_size_GB'] = (df['memory_mb'] / 1024).round(0).astype(int)
        else:
            df['mem_size_GB'] = 0
        
        # Convert storage (MB → GB)
        if 'storage_provisioned_mb' in df.columns:
            df['storage_size_GB'] = (df['storage_provisioned_mb'] / 1024).round(2)
        else:
            df['storage_size_GB'] = 0.0
            
        if 'storage_used_mb' in df.columns:
            df['used_size_GB'] = (df['storage_used_mb'] / 1024).round(2)
        else:
            df['used_size_GB'] = 0.0
        
        # Ensure num_of_cpus is numeric
        df['num_of_cpus'] = pd.to_numeric(df['num_of_cpus'], errors='coerce').fillna(0).astype(int)
        
        # Normalize status (poweredOn → On, poweredOff → Off)
        if 'power_state' in df.columns:
            df['status'] = df['power_state'].map({
                'poweredOn': 'On',
                'poweredOff': 'Off'
            }).fillna('Unknown')
        else:
            df['status'] = 'Unknown'
        
        # Try to find and parse creation date
        df['creation_date'] = pd.NaT
        date_col = self._find_creation_date_column(df)
        
        if date_col:
            # Try to parse the date column
            df['creation_date'] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Check if we got valid dates
            valid_dates = df['creation_date'].notna().sum()
            if valid_dates > 0:
                self._has_date_data = True
                print(f"  ✓ Found creation dates in column '{date_col}' ({valid_dates} valid dates)")
            else:
                self._has_date_data = False
        else:
            self._has_date_data = False
        
        # Handle missing cluster_name (use datacenter if available)
        if 'cluster_name' not in df.columns or df['cluster_name'].isna().all():
            if 'datacenter' in df.columns:
                df['cluster_name'] = df['datacenter']
            else:
                df['cluster_name'] = 'Unknown'
        
        # Handle missing vm_host
        if 'vm_host' not in df.columns:
            df['vm_host'] = 'Unknown'
        
        return df.reset_index(drop=True)


# For testing
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vmware_processor.py <excel_file>")
        sys.exit(1)
    
    processor = VMwareProcessor()
    data = processor.process(sys.argv[1])
    
    print(f"\n{'='*50}")
    print(f"VMWARE PROCESSING SUMMARY")
    print(f"{'='*50}")
    print(f"Source: {data['source_display_name']}")
    print(f"Total VMs: {data['stats']['total_vms']}")
    print(f"Total vCPUs: {data['stats']['total_vcpus']}")
    print(f"Total Memory: {data['stats']['total_memory_gb']} GB")
    print(f"Has Date Data: {data['has_date_data']}")
    
    if data['has_date_data']:
        print(f"First VM Date: {data['stats'].get('first_vm_date', 'N/A')}")
        print(f"Last VM Date: {data['stats'].get('last_vm_date', 'N/A')}")
