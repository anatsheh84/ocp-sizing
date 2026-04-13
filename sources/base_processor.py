"""
base_processor.py
-----------------
Abstract base class for all source processors.
Defines the common interface and shared utility methods.
"""

from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
import re


class BaseProcessor(ABC):
    """Abstract base class for virtualization source processors."""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return source platform identifier (e.g., 'rhv', 'vmware')."""
        pass
    
    @property
    @abstractmethod
    def source_display_name(self) -> str:
        """Return human-readable source name for display."""
        pass
    
    @property
    def has_date_data(self) -> bool:
        """Whether this source provides VM creation dates."""
        return False
    
    @abstractmethod
    def load_and_normalize(self, filepath: str) -> pd.DataFrame:
        """
        Load source file and normalize to standard schema.
        
        Expected columns after normalization:
        - vm_name: str
        - cluster_name: str
        - guest_os: str
        - vm_host: str
        - status: str ('On' or 'Off')
        - mem_size_GB: int
        - num_of_cpus: int
        - storage_size_GB: float
        - used_size_GB: float
        - creation_date: datetime or NaT
        """
        pass
    
    # =========================================================================
    # Common utility methods (shared across all processors)
    # =========================================================================
    
    def get_os_family(self, guest_os) -> str:
        """Determine OS family from guest OS string."""
        if pd.isna(guest_os):
            return 'Unknown'
        os_lower = str(guest_os).lower()
        if 'windows' in os_lower:
            return 'Windows'
        return 'Linux'
    
    def get_consolidated_os(self, guest_os) -> str:
        """
        Consolidate OS versions for cleaner reporting.
        Examples:
        - 'Microsoft Windows Server 2008 R2 (64-bit)' -> 'Windows Server 2008 R2'
        - 'Microsoft Windows Server 2003 Standard (32-bit)' -> 'Windows Server 2003'
        - 'Microsoft Windows XP Professional (32-bit)' -> 'Windows XP'
        - 'Red Hat Enterprise Linux 6 (64-bit)' -> 'RHEL 6'
        """
        if pd.isna(guest_os):
            return 'Unknown'
        
        os_str = str(guest_os).strip()
        
        # RHEL consolidation (check before cleaning to preserve "Enterprise")
        rhel_match = re.match(r'Red Hat Enterprise Linux\s*(\d+)', os_str, re.IGNORECASE)
        if rhel_match:
            return f'RHEL {rhel_match.group(1)}'
        
        # Remove common suffixes: (64-bit), (32-bit)
        os_clean = re.sub(r'\s*\(\d+-bit\)', '', os_str)
        # Remove edition names for Windows
        os_clean = re.sub(r'\s+(Standard|Enterprise|Professional|Datacenter|Ultimate|Home|Premium)\b', '', os_clean, flags=re.IGNORECASE)
        os_clean = os_clean.strip()
        
        # CentOS consolidation
        centos_match = re.match(r'CentOS\s*[\d/]+', os_clean, re.IGNORECASE)
        if centos_match:
            # Extract first version number
            ver_match = re.search(r'(\d+)', os_clean)
            if ver_match:
                return f'CentOS {ver_match.group(1)}'
            return 'CentOS'
        
        # SUSE consolidation
        suse_match = re.match(r'SUSE\s*Linux\s*Enterprise\s*(\d+)', os_str, re.IGNORECASE)
        if suse_match:
            return f'SUSE {suse_match.group(1)}'
        if 'suse' in os_str.lower():
            return 'SUSE Linux'
        
        # Windows consolidation - remove "Microsoft" prefix
        if 'windows' in os_clean.lower():
            os_clean = re.sub(r'^Microsoft\s+', '', os_clean, flags=re.IGNORECASE)
            
            # Windows Server with year
            server_match = re.match(r'Windows\s+Server\s+(\d{4}(?:\s+R2)?)', os_clean, re.IGNORECASE)
            if server_match:
                return f'Windows Server {server_match.group(1)}'
            
            # Windows client versions
            client_match = re.match(r'Windows\s+(XP|Vista|\d+)', os_clean, re.IGNORECASE)
            if client_match:
                return f'Windows {client_match.group(1)}'
            
            return os_clean
        
        # Oracle/Solaris
        if 'solaris' in os_str.lower():
            solaris_match = re.search(r'Solaris\s*(\d+)', os_str, re.IGNORECASE)
            if solaris_match:
                return f'Solaris {solaris_match.group(1)}'
            return 'Solaris'
        
        # FreeBSD
        if 'freebsd' in os_str.lower():
            return 'FreeBSD'
        
        # Other Linux
        if 'linux' in os_str.lower():
            if 'other' in os_str.lower():
                return 'Other Linux'
        
        return os_clean
    
    def get_size_category(self, mem_gb: int, vcpus: int) -> str:
        """
        Categorize VM by size.
        Small: ≤8 GB RAM, ≤4 vCPU
        Medium: ≤32 GB RAM, ≤8 vCPU
        Large: ≤64 GB RAM, ≤16 vCPU
        X-Large: >64 GB RAM or >16 vCPU
        """
        if mem_gb > 64 or vcpus > 16:
            return 'X-Large'
        if mem_gb > 32 or vcpus > 8:
            return 'Large'
        if mem_gb > 8 or vcpus > 4:
            return 'Medium'
        return 'Small'
    
    def get_migration_complexity(self, guest_os, os_family, mem_gb, vcpus) -> str:
        """
        Determine migration complexity.
        Low: Linux VMs (RHEL 8/9) with standard sizing
        Medium: Windows VMs, RHEL 7, or large VMs
        High: Large Windows VMs (>64GB RAM or >16 vCPU)
        """
        is_large = mem_gb > 64 or vcpus > 16
        is_rhel7 = 'rhel 7' in str(guest_os).lower() or 'rhel7' in str(guest_os).lower()
        
        if os_family == 'Windows':
            if is_large:
                return 'High'
            return 'Medium'
        
        # Linux
        if is_rhel7:
            return 'Medium'
        if is_large:
            return 'Medium'
        
        return 'Low'

    
    def add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed fields to dataframe."""
        df['os_family'] = df['guest_os'].apply(self.get_os_family)
        df['os_consolidated'] = df['guest_os'].apply(self.get_consolidated_os)
        df['size_category'] = df.apply(
            lambda r: self.get_size_category(r['mem_size_GB'], r['num_of_cpus']), axis=1
        )
        df['complexity'] = df.apply(
            lambda r: self.get_migration_complexity(
                r['guest_os'], r['os_family'], r['mem_size_GB'], r['num_of_cpus']
            ), axis=1
        )
        df['storage_efficiency'] = df.apply(
            lambda r: round((r['used_size_GB'] / r['storage_size_GB']) * 100, 1) 
            if r['storage_size_GB'] > 0 else 0, axis=1
        )
        return df
    
    def compute_statistics(self, df: pd.DataFrame) -> dict:
        """Compute aggregate statistics for dashboard."""
        stats = {
            'total_vms': len(df),
            'total_vcpus': int(df['num_of_cpus'].sum()),
            'total_memory_gb': int(df['mem_size_GB'].sum()),
            'total_storage_provisioned_gb': round(df['storage_size_GB'].sum(), 2),
            'total_storage_used_gb': round(df['used_size_GB'].sum(), 2),
            'clusters': df['cluster_name'].nunique(),
            'hosts': df['vm_host'].nunique(),
            'running_vms': len(df[df['status'] == 'On']),
            'stopped_vms': len(df[df['status'] == 'Off']),
        }
        
        # Date statistics (only if has_date_data)
        if self.has_date_data:
            valid_dates = df[df['creation_date'].notna()]['creation_date']
            if len(valid_dates) > 0:
                stats['first_vm_date'] = valid_dates.min().strftime('%Y-%m-%d')
                stats['last_vm_date'] = valid_dates.max().strftime('%Y-%m-%d')
                
                df_with_dates = df[df['creation_date'].notna()].copy()
                df_with_dates['month'] = df_with_dates['creation_date'].dt.to_period('M')
                monthly_counts = df_with_dates.groupby('month').size()
                
                if len(monthly_counts) > 0:
                    stats['avg_vms_per_month'] = round(monthly_counts.mean(), 1)
                    stats['peak_month'] = str(monthly_counts.idxmax())
                    stats['peak_month_count'] = int(monthly_counts.max())
        
        return stats

    
    def compute_distributions(self, df: pd.DataFrame) -> dict:
        """Compute distribution data for charts."""
        distributions = {}
        
        distributions['os_family'] = df['os_family'].value_counts().to_dict()
        distributions['os_consolidated'] = df['os_consolidated'].value_counts().to_dict()
        distributions['size_category'] = df['size_category'].value_counts().to_dict()
        distributions['complexity'] = df['complexity'].value_counts().to_dict()
        distributions['status'] = df['status'].value_counts().to_dict()
        
        # Cluster distribution
        cluster_stats = df.groupby('cluster_name').agg({
            'vm_name': 'count',
            'num_of_cpus': 'sum',
            'mem_size_GB': 'sum',
            'storage_size_GB': 'sum',
            'used_size_GB': 'sum'
        }).rename(columns={'vm_name': 'vm_count'})
        distributions['by_cluster'] = cluster_stats.to_dict('index')
        
        # Host distribution
        host_stats = df.groupby('vm_host').agg({
            'vm_name': 'count',
            'num_of_cpus': 'sum',
            'mem_size_GB': 'sum'
        }).rename(columns={'vm_name': 'vm_count'})
        distributions['by_host'] = host_stats.to_dict('index')
        
        return distributions
    
    def compute_size_category_details(self, df: pd.DataFrame) -> list:
        """Compute detailed breakdown by size category."""
        size_order = ['Small', 'Medium', 'Large', 'X-Large']
        size_specs = {
            'Small': {'cpu_range': '≤4', 'mem_range': '≤8 GB'},
            'Medium': {'cpu_range': '≤8', 'mem_range': '≤32 GB'},
            'Large': {'cpu_range': '≤16', 'mem_range': '≤64 GB'},
            'X-Large': {'cpu_range': '>16', 'mem_range': '>64 GB'}
        }
        
        details = []
        for size in size_order:
            subset = df[df['size_category'] == size]
            if len(subset) > 0:
                details.append({
                    'category': size,
                    'cpu_range': size_specs[size]['cpu_range'],
                    'mem_range': size_specs[size]['mem_range'],
                    'vm_count': len(subset),
                    'total_vcpus': int(subset['num_of_cpus'].sum()),
                    'total_memory': int(subset['mem_size_GB'].sum()),
                    'total_storage': round(subset['storage_size_GB'].sum(), 2)
                })
        
        return details

    
    def compute_migration_waves(self, df: pd.DataFrame) -> list:
        """Generate suggested migration waves."""
        waves = []
        
        # Wave 1: Low complexity Linux VMs
        wave1 = df[(df['complexity'] == 'Low') & (df['os_family'] == 'Linux')]
        if len(wave1) > 0:
            waves.append({
                'wave': 1,
                'name': 'Pilot - Low Complexity Linux',
                'description': 'RHEL 8/9 VMs with standard sizing',
                'criteria': 'Linux, Low complexity, Small/Medium size',
                'vm_count': len(wave1),
                'vcpus': int(wave1['num_of_cpus'].sum()),
                'memory_gb': int(wave1['mem_size_GB'].sum())
            })
        
        # Wave 2: Medium complexity Linux
        wave2 = df[(df['complexity'] == 'Medium') & (df['os_family'] == 'Linux')]
        if len(wave2) > 0:
            waves.append({
                'wave': 2,
                'name': 'Linux Extended',
                'description': 'RHEL 7 and large Linux VMs',
                'criteria': 'Linux, Medium complexity',
                'vm_count': len(wave2),
                'vcpus': int(wave2['num_of_cpus'].sum()),
                'memory_gb': int(wave2['mem_size_GB'].sum())
            })
        
        # Wave 3: Medium complexity Windows
        wave3 = df[(df['complexity'] == 'Medium') & (df['os_family'] == 'Windows')]
        if len(wave3) > 0:
            waves.append({
                'wave': 3,
                'name': 'Windows Standard',
                'description': 'Windows VMs with standard sizing',
                'criteria': 'Windows, ≤64GB RAM, ≤16 vCPU',
                'vm_count': len(wave3),
                'vcpus': int(wave3['num_of_cpus'].sum()),
                'memory_gb': int(wave3['mem_size_GB'].sum())
            })
        
        # Wave 4: High complexity
        wave4 = df[df['complexity'] == 'High']
        if len(wave4) > 0:
            waves.append({
                'wave': 4,
                'name': 'High Complexity',
                'description': 'Large Windows VMs requiring special attention',
                'criteria': 'Windows, >64GB RAM or >16 vCPU',
                'vm_count': len(wave4),
                'vcpus': int(wave4['num_of_cpus'].sum()),
                'memory_gb': int(wave4['mem_size_GB'].sum())
            })
        
        return waves

    
    def compute_growth_trends(self, df: pd.DataFrame) -> dict:
        """Compute historical growth data for trend charts."""
        if not self.has_date_data:
            return None
            
        df_dated = df[df['creation_date'].notna()].copy()
        if len(df_dated) == 0:
            return None
        
        df_dated = df_dated.sort_values('creation_date')
        df_dated['month'] = df_dated['creation_date'].dt.to_period('M')
        
        monthly = df_dated.groupby('month').agg({
            'vm_name': 'count',
            'num_of_cpus': 'sum',
            'mem_size_GB': 'sum',
            'storage_size_GB': 'sum'
        }).rename(columns={'vm_name': 'vm_count'})
        
        monthly['cumulative_vms'] = monthly['vm_count'].cumsum()
        monthly['cumulative_vcpus'] = monthly['num_of_cpus'].cumsum()
        monthly['cumulative_memory'] = monthly['mem_size_GB'].cumsum()
        
        return {
            'months': [str(m) for m in monthly.index],
            'monthly_vms': monthly['vm_count'].tolist(),
            'monthly_vcpus': monthly['num_of_cpus'].tolist(),
            'monthly_memory': monthly['mem_size_GB'].tolist(),
            'cumulative_vms': monthly['cumulative_vms'].tolist(),
            'cumulative_vcpus': monthly['cumulative_vcpus'].tolist(),
            'cumulative_memory': monthly['cumulative_memory'].tolist()
        }
    
    def compute_complexity_by_os(self, df: pd.DataFrame) -> dict:
        """Compute complexity breakdown by OS type."""
        result = {}
        for os_type in df['os_consolidated'].unique():
            subset = df[df['os_consolidated'] == os_type]
            result[os_type] = {
                'Low': len(subset[subset['complexity'] == 'Low']),
                'Medium': len(subset[subset['complexity'] == 'Medium']),
                'High': len(subset[subset['complexity'] == 'High'])
            }
        return result
    
    def prepare_vm_list(self, df: pd.DataFrame) -> list:
        """Prepare VM list for inventory table."""
        vm_list = []
        for _, row in df.iterrows():
            vm_list.append({
                'vm_name': str(row['vm_name']),
                'cluster': str(row['cluster_name']),
                'guest_os': str(row['guest_os']),
                'host': str(row['vm_host']),
                'status': str(row['status']),
                'memory_gb': int(row['mem_size_GB']),
                'vcpus': int(row['num_of_cpus']),
                'storage_gb': round(row['storage_size_GB'], 2),
                'used_gb': round(row['used_size_GB'], 2),
                'utilization': round(row['storage_efficiency'], 1),
                'size_category': row['size_category'],
                'complexity': row['complexity'],
                'os_family': row['os_family'],
                'os_consolidated': row['os_consolidated'],
                'creation_date': row['creation_date'].strftime('%Y-%m-%d') 
                    if pd.notna(row['creation_date']) else ''
            })
        return vm_list

    
    def process(self, filepath: str) -> dict:
        """
        Main entry point - returns complete data structure for dashboard.
        
        Args:
            filepath: Path to the source export file
            
        Returns:
            Dictionary with all data needed by dashboard tabs
        """
        # Load and normalize
        df = self.load_and_normalize(filepath)
        df = self.add_derived_fields(df)
        
        # Build output data structure
        data = {
            'stats': self.compute_statistics(df),
            'distributions': self.compute_distributions(df),
            'size_details': self.compute_size_category_details(df),
            'migration_waves': self.compute_migration_waves(df),
            'growth_trends': self.compute_growth_trends(df),
            'complexity_by_os': self.compute_complexity_by_os(df),
            'vm_list': self.prepare_vm_list(df),
            'unique_clusters': sorted(df['cluster_name'].unique().tolist()),
            'unique_hosts': sorted(df['vm_host'].unique().tolist()),
            'unique_os': sorted(df['os_consolidated'].unique().tolist()),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_platform': self.source_name,
            'source_display_name': self.source_display_name,
            'has_date_data': self.has_date_data
        }
        
        return data
