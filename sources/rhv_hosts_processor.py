"""
rhv_hosts_processor.py
----------------------
Processor for Red Hat Virtualization (RHV) hosts data.
Loads host information from a second sheet in the Excel file.
"""

import pandas as pd


# Column mapping: expected name -> possible variations in Excel
RHV_HOSTS_COLUMN_MAPPING = {
    'host_name': ['host_name', 'hostname', 'host', 'vds_name'],
    'cluster_name': ['cluster_name', 'cluster'],
    'cpu_model': ['cpu_model', 'cpu_hostel', 'model'],
    'cpu_sockets': ['cpu_sockets', 'sockets'],
    'vcores_per_socket': ['vcores_per_socket', 'cores_per_socket', 'cpu_cores'],
    'total_vcores': ['total_vcores', 'total_cores'],
    'cpu_threads': ['cpu_threads', 'threads'],
    'physical_mem_mb': ['physical_mem_mb', 'memory_mb', 'mem_mb'],
    'running_vms': ['running_vms', 'vm_count'],
    'allocated_vcpus': ['allocated_vcpus', 'vms_cores_count'],
    'status': ['status']
}

# Status code mapping
HOST_STATUS_MAP = {
    1: 'Down',
    2: 'Maintenance',
    3: 'Up',
    4: 'Non-Responsive',
    5: 'Error'
}


class RHVHostsProcessor:
    """Processor for RHV hosts data."""
    
    def __init__(self):
        pass
    
    def _find_column(self, df_columns, expected_name):
        """Find matching column from possible variations."""
        variations = RHV_HOSTS_COLUMN_MAPPING.get(expected_name, [expected_name])
        for var in variations:
            for col in df_columns:
                if col.lower().strip() == var.lower().strip():
                    return col
        return None
    
    def _find_hosts_sheet(self, excel_file):
        """Find the hosts sheet in the Excel file."""
        xl = pd.ExcelFile(excel_file)
        sheet_names = xl.sheet_names
        
        # Look for common host sheet names
        possible_names = ['hosts', 'host', 'rhv_hosts', 'hypervisors', 'nodes']
        
        for sheet in sheet_names:
            if sheet.lower() in possible_names:
                return sheet
        
        # If not found by name, check if there's a second sheet
        if len(sheet_names) >= 2:
            return sheet_names[1]
        
        return None
    
    def load_and_normalize(self, filepath: str) -> pd.DataFrame:
        """Load RHV hosts Excel file and normalize to standard schema."""
        # Find the hosts sheet
        sheet_name = self._find_hosts_sheet(filepath)
        
        if sheet_name is None:
            raise ValueError("No hosts sheet found in Excel file. Expected sheet named 'hosts' or as second sheet.")
        
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        
        # Map columns to standardized names
        column_map = {}
        for std_name in RHV_HOSTS_COLUMN_MAPPING.keys():
            found = self._find_column(df.columns, std_name)
            if found:
                column_map[found] = std_name
        
        df = df.rename(columns=column_map)
        
        # Clean data
        df = self._clean_data(df)
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out invalid rows and handle data types."""
        # Remove rows without host_name
        df = df[df['host_name'].notna() & (df['host_name'] != '')]
        
        # Ensure numeric columns
        numeric_cols = {
            'cpu_sockets': 0,
            'vcores_per_socket': 0,
            'total_vcores': 0,
            'cpu_threads': 0,
            'physical_mem_mb': 0,
            'running_vms': 0,
            'allocated_vcpus': 0,
            'status': 3  # Default to 'Up'
        }
        
        for col, default_val in numeric_cols.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default_val).astype(int)
            else:
                df[col] = default_val
        
        # Ensure string columns
        if 'cluster_name' not in df.columns:
            df['cluster_name'] = 'Unknown'
        
        if 'cpu_model' not in df.columns:
            df['cpu_model'] = 'Unknown'
        
        # Fix: use cpu_threads as actual vCPU capacity (total_vcores from RHV
        # export is inflated — it's cores_per_socket * sockets which double-counts).
        # cpu_threads = physical cores * 2 (hyperthreading) = real vCPU count.
        if 'cpu_threads' in df.columns:
            df['total_vcores'] = df['cpu_threads']
        
        return df.reset_index(drop=True)
    
    def get_status_name(self, status_code: int) -> str:
        """Convert status code to readable name."""
        return HOST_STATUS_MAP.get(status_code, 'Unknown')
    
    def get_utilization_category(self, cpu_overcommit: float) -> str:
        """
        Categorize host utilization based on CPU overcommit ratio.
        Low: <1.5x
        Medium: 1.5x - 2.5x
        High: 2.5x - 4.0x
        Critical: >4.0x
        """
        if cpu_overcommit >= 4.0:
            return 'Critical'
        elif cpu_overcommit >= 2.5:
            return 'High'
        elif cpu_overcommit >= 1.5:
            return 'Medium'
        else:
            return 'Low'
    
    def add_derived_fields(self, df: pd.DataFrame, vm_data: dict = None) -> pd.DataFrame:
        """Add computed fields to dataframe."""
        # CPU Overcommit Ratio
        df['cpu_overcommit'] = df.apply(
            lambda r: round(r['allocated_vcpus'] / r['total_vcores'], 2) if r['total_vcores'] > 0 else 0,
            axis=1
        )
        
        # Utilization Category
        df['utilization_category'] = df['cpu_overcommit'].apply(self.get_utilization_category)
        
        # Status Name
        df['status_name'] = df['status'].apply(self.get_status_name)
        
        # Physical Memory in GB (for display)
        df['physical_mem_gb'] = (df['physical_mem_mb'] / 1024).round(0).astype(int)
        
        # Memory utilization - if we have VM data, calculate actual memory allocation
        if vm_data and 'vm_list' in vm_data:
            host_memory_usage = {}
            for vm in vm_data['vm_list']:
                host = vm.get('host', 'Unknown')
                mem_gb = vm.get('memory_gb', 0)
                if host not in host_memory_usage:
                    host_memory_usage[host] = 0
                host_memory_usage[host] += mem_gb
            
            df['allocated_memory_gb'] = df['host_name'].map(host_memory_usage).fillna(0).astype(int)
            df['memory_utilization_pct'] = df.apply(
                lambda r: round((r['allocated_memory_gb'] / r['physical_mem_gb']) * 100, 1) 
                if r['physical_mem_gb'] > 0 else 0,
                axis=1
            )
        else:
            df['allocated_memory_gb'] = 0
            df['memory_utilization_pct'] = 0.0
        
        return df
    
    def compute_statistics(self, df: pd.DataFrame) -> dict:
        """Compute aggregate statistics for hosts."""
        stats = {
            'total_hosts': len(df),
            'total_vcores': int(df['total_vcores'].sum()),
            'total_physical_memory_gb': int(df['physical_mem_gb'].sum()),
            'total_running_vms': int(df['running_vms'].sum()),
            'total_allocated_vcpus': int(df['allocated_vcpus'].sum()),
            'avg_cpu_overcommit': round(df['cpu_overcommit'].mean(), 2),
            'max_cpu_overcommit': round(df['cpu_overcommit'].max(), 2),
            'min_cpu_overcommit': round(df['cpu_overcommit'].min(), 2),
            'avg_vms_per_host': round(df['running_vms'].mean(), 1),
        }
        
        # Status breakdown
        status_counts = df['status_name'].value_counts().to_dict()
        stats['hosts_up'] = status_counts.get('Up', 0)
        stats['hosts_down'] = status_counts.get('Down', 0)
        stats['hosts_maintenance'] = status_counts.get('Maintenance', 0)
        stats['hosts_error'] = status_counts.get('Error', 0) + status_counts.get('Non-Responsive', 0)
        
        # Utilization breakdown
        util_counts = df['utilization_category'].value_counts().to_dict()
        stats['hosts_low_util'] = util_counts.get('Low', 0)
        stats['hosts_medium_util'] = util_counts.get('Medium', 0)
        stats['hosts_high_util'] = util_counts.get('High', 0)
        stats['hosts_critical_util'] = util_counts.get('Critical', 0)
        
        # Cluster count
        stats['total_clusters'] = df['cluster_name'].nunique()
        
        return stats
    
    def compute_distributions(self, df: pd.DataFrame) -> dict:
        """Compute distribution data for charts."""
        distributions = {}
        
        # By cluster
        cluster_stats = df.groupby('cluster_name').agg({
            'host_name': 'count',
            'total_vcores': 'sum',
            'physical_mem_gb': 'sum',
            'running_vms': 'sum',
            'allocated_vcpus': 'sum',
            'cpu_overcommit': 'mean'
        }).rename(columns={'host_name': 'host_count'})
        distributions['by_cluster'] = cluster_stats.to_dict('index')
        
        # By utilization category
        distributions['by_utilization'] = df['utilization_category'].value_counts().to_dict()
        
        # By status
        distributions['by_status'] = df['status_name'].value_counts().to_dict()
        
        return distributions
    
    def prepare_host_list(self, df: pd.DataFrame) -> list:
        """Prepare host list for inventory table."""
        host_list = []
        for _, row in df.iterrows():
            host_list.append({
                'host_name': str(row['host_name']),
                'cluster': str(row['cluster_name']),
                'cpu_model': str(row['cpu_model']),
                'cpu_sockets': int(row['cpu_sockets']),
                'vcores_per_socket': int(row['vcores_per_socket']),
                'total_vcores': int(row['total_vcores']),
                'physical_mem_gb': int(row['physical_mem_gb']),
                'running_vms': int(row['running_vms']),
                'allocated_vcpus': int(row['allocated_vcpus']),
                'allocated_memory_gb': int(row['allocated_memory_gb']),
                'cpu_overcommit': float(row['cpu_overcommit']),
                'memory_utilization_pct': float(row['memory_utilization_pct']),
                'utilization_category': str(row['utilization_category']),
                'status': int(row['status']),
                'status_name': str(row['status_name'])
            })
        return host_list
    
    def process(self, filepath: str, vm_data: dict = None) -> dict:
        """
        Main entry point - returns complete host data structure.
        
        Args:
            filepath: Path to the Excel file
            vm_data: Optional VM data for cross-referencing
            
        Returns:
            Dictionary with all host data
        """
        try:
            # Load and normalize
            df = self.load_and_normalize(filepath)
            df = self.add_derived_fields(df, vm_data)
            
            # Build output data structure
            data = {
                'stats': self.compute_statistics(df),
                'distributions': self.compute_distributions(df),
                'host_list': self.prepare_host_list(df),
                'unique_clusters': sorted(df['cluster_name'].unique().tolist()),
                'has_host_data': True
            }
            
            return data
            
        except Exception as e:
            # Return empty structure if host data not available
            return {
                'stats': {},
                'distributions': {},
                'host_list': [],
                'unique_clusters': [],
                'has_host_data': False,
                'error': str(e)
            }


# For testing
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python rhv_hosts_processor.py <excel_file>")
        sys.exit(1)
    
    processor = RHVHostsProcessor()
    data = processor.process(sys.argv[1])
    
    if data['has_host_data']:
        print(f"\n{'='*50}")
        print(f"RHV HOSTS PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total Hosts: {data['stats']['total_hosts']}")
        print(f"Total vCores: {data['stats']['total_vcores']}")
        print(f"Total Memory: {data['stats']['total_physical_memory_gb']} GB")
        print(f"Avg CPU Overcommit: {data['stats']['avg_cpu_overcommit']}x")
        print(f"Hosts Up: {data['stats']['hosts_up']}")
    else:
        print(f"Error loading host data: {data.get('error', 'Unknown error')}")
