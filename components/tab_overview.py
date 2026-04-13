"""
tab_overview.py
---------------
Tab 1: Overview
Displays summary statistics and distribution charts.
"""


def generate_stat_cards(stats):
    """Generate the overview stat cards HTML."""
    
    # Calculate storage efficiency
    storage_used = stats.get('total_storage_used_gb', 0)
    storage_provisioned = stats.get('total_storage_provisioned_gb', 0)
    storage_efficiency = round((storage_used / storage_provisioned * 100), 1) if storage_provisioned > 0 else 0
    
    return f'''            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total VMs</div>
                    <div class="stat-value" id="stat-total-vms">{stats.get('total_vms', 0):,}</div>
                    <div class="stat-detail"><span id="stat-running-vms">{stats.get('running_vms', 0)}</span> running, <span id="stat-stopped-vms">{stats.get('stopped_vms', 0)}</span> stopped</div>
                </div>
                <div class="stat-card blue">
                    <div class="stat-label">Clusters</div>
                    <div class="stat-value" id="stat-clusters">{stats.get('clusters', 0)}</div>
                    <div class="stat-detail"><span id="stat-hosts">{stats.get('hosts', 0)}</span> hypervisor hosts</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-label">Total vCPUs</div>
                    <div class="stat-value" id="stat-vcpus">{stats.get('total_vcpus', 0):,}</div>
                    <div class="stat-detail">Allocated across all VMs</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Total Memory</div>
                    <div class="stat-value" id="stat-memory">{stats.get('total_memory_gb', 0):,}</div>
                    <div class="stat-detail">GB allocated</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Storage Used</div>
                    <div class="stat-value" id="stat-storage-used">{storage_used:,.0f}</div>
                    <div class="stat-detail">GB of <span id="stat-storage-provisioned">{storage_provisioned:,.0f}</span> GB provisioned (<span id="stat-storage-efficiency">{storage_efficiency}</span>%)</div>
                </div>
            </div>
'''


def generate_charts_section():
    """Generate the chart containers for the overview tab."""
    return '''            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">OS Family Distribution</div>
                    <div class="chart-container small">
                        <canvas id="chart-os-family"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">VM Size Categories</div>
                    <div class="chart-container small">
                        <canvas id="chart-size-categories"></canvas>
                    </div>
                    <div class="legend-box">
                        <div class="legend-item"><span class="legend-color" style="background: #4CAF50;"></span> Small: ≤8 GB RAM, ≤4 vCPU</div>
                        <div class="legend-item"><span class="legend-color" style="background: #2196F3;"></span> Medium: ≤32 GB RAM, ≤8 vCPU</div>
                        <div class="legend-item"><span class="legend-color" style="background: #FF9800;"></span> Large: ≤64 GB RAM, ≤16 vCPU</div>
                        <div class="legend-item"><span class="legend-color" style="background: #f44336;"></span> X-Large: >64 GB RAM or >16 vCPU</div>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Migration Complexity Distribution</div>
                    <div class="chart-container small">
                        <canvas id="chart-complexity"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Cluster Resource Distribution</div>
                    <div class="chart-container small">
                        <canvas id="chart-cluster-resources"></canvas>
                    </div>
                </div>
                <div class="chart-card full-width">
                    <div class="chart-title">Host Resource Distribution</div>
                    <div class="table-wrapper" style="max-height: 350px; overflow-y: auto;">
                        <table class="data-table" id="host-resource-table">
                            <thead>
                                <tr>
                                    <th onclick="sortHostTable(0)" style="cursor:pointer">Host ↕</th>
                                    <th onclick="sortHostTable(1)" style="cursor:pointer">VMs ↕</th>
                                    <th style="min-width: 150px;">VM Distribution</th>
                                    <th onclick="sortHostTable(3)" style="cursor:pointer">vCPUs ↕</th>
                                    <th onclick="sortHostTable(4)" style="cursor:pointer">Memory (GB) ↕</th>
                                </tr>
                            </thead>
                            <tbody id="host-table-body">
                                <!-- Populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="chart-card full-width">
                    <div class="chart-title">Guest OS Breakdown (Consolidated)</div>
                    <div class="chart-container">
                        <canvas id="chart-guest-os"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_tab_overview(data):
    """
    Generate complete HTML for the Overview tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the overview tab content
    """
    stats = data.get('stats', {})
    
    html = generate_stat_cards(stats)
    html += generate_charts_section()
    
    return html


def get_overview_chart_configs(data):
    """
    Generate JavaScript chart configuration objects for Overview tab.
    Returns a dict of chart configs to be used by scripts.py
    """
    distributions = data.get('distributions', {})
    
    # OS Family data
    os_family = distributions.get('os_family', {})
    
    # Size category data (in order)
    size_order = ['Small', 'Medium', 'Large', 'X-Large']
    size_data = distributions.get('size_category', {})
    size_values = [size_data.get(s, 0) for s in size_order]
    
    # Complexity data (in order)
    complexity_order = ['Low', 'Medium', 'High']
    complexity_data = distributions.get('complexity', {})
    complexity_values = [complexity_data.get(c, 0) for c in complexity_order]
    
    # Cluster data
    cluster_data = distributions.get('by_cluster', {})
    cluster_names = list(cluster_data.keys())
    cluster_vms = [cluster_data[c].get('vm_count', 0) for c in cluster_names]
    cluster_vcpus = [cluster_data[c].get('num_of_cpus', 0) for c in cluster_names]
    cluster_memory = [cluster_data[c].get('mem_size_GB', 0) for c in cluster_names]
    
    # Host data
    host_data = distributions.get('by_host', {})
    host_names = list(host_data.keys())
    host_vms = [host_data[h].get('vm_count', 0) for h in host_names]
    host_vcpus = [host_data[h].get('num_of_cpus', 0) for h in host_names]
    host_memory = [host_data[h].get('mem_size_GB', 0) for h in host_names]
    
    # Guest OS consolidated data
    os_consolidated = distributions.get('os_consolidated', {})
    os_names = list(os_consolidated.keys())
    os_counts = list(os_consolidated.values())
    
    return {
        'os_family': {
            'labels': list(os_family.keys()),
            'values': list(os_family.values())
        },
        'size_category': {
            'labels': size_order,
            'values': size_values
        },
        'complexity': {
            'labels': complexity_order,
            'values': complexity_values
        },
        'cluster': {
            'labels': cluster_names,
            'vms': cluster_vms,
            'vcpus': cluster_vcpus,
            'memory': cluster_memory
        },
        'host': {
            'labels': host_names,
            'vms': host_vms,
            'vcpus': host_vcpus,
            'memory': host_memory
        },
        'guest_os': {
            'labels': os_names,
            'values': os_counts
        }
    }


# For testing
if __name__ == '__main__':
    # Mock data for testing
    mock_data = {
        'stats': {
            'total_vms': 118,
            'running_vms': 109,
            'stopped_vms': 9,
            'clusters': 1,
            'hosts': 6,
            'total_vcpus': 893,
            'total_memory_gb': 2405,
            'total_storage_provisioned_gb': 60304.99,
            'total_storage_used_gb': 17264.12
        },
        'distributions': {
            'os_family': {'Linux': 59, 'Windows': 59},
            'size_category': {'Small': 40, 'Medium': 46, 'Large': 30, 'X-Large': 2},
            'complexity': {'Low': 57, 'Medium': 60, 'High': 1},
            'by_cluster': {
                'HH-NONPROD-CLU01': {'vm_count': 118, 'num_of_cpus': 893, 'mem_size_GB': 2405}
            },
            'by_host': {
                'np-f02-hh-sy01': {'vm_count': 25, 'num_of_cpus': 200, 'mem_size_GB': 500},
                'np-f02-hh-sy02': {'vm_count': 20, 'num_of_cpus': 180, 'mem_size_GB': 450}
            },
            'os_consolidated': {'RHEL 8': 35, 'RHEL 9': 6, 'Windows 2022': 40, 'Windows 2019': 15}
        }
    }
    
    html = generate_tab_overview(mock_data)
    print(f"Overview tab HTML generated: {len(html)} characters")
    print("\n--- Preview ---")
    print(html[:1500])
    
    print("\n--- Chart Configs ---")
    configs = get_overview_chart_configs(mock_data)
    for chart, config in configs.items():
        print(f"{chart}: {config}")
