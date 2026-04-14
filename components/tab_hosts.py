"""
tab_hosts.py
------------
Tab 7: Hosts Inventory
Displays hypervisor host information, CPU overcommitment, and utilization.
Handles cases where host data is not available.
"""


def generate_no_data_message():
    """Generate message when host data is not available."""
    return '''            <div class="no-data-message">
                <div class="icon">🖥️</div>
                <h3>Host Data Not Available</h3>
                <p>Hypervisor host information is not included in this data source.</p>
                <p>The Hosts Inventory tab requires host data from RHV database exports.</p>
                <p style="margin-top: 20px; font-size: 14px; color: #999;">
                    <strong>Tip:</strong> Include host data as a second sheet named "Hosts" in your Excel file.
                </p>
                <p style="margin-top: 15px; font-size: 14px; color: #666;">
                    You can still use other tabs to analyze VM-level information and plan your migration.
                </p>
            </div>
'''


def generate_summary_cards(host_data):
    """Generate summary metric cards for hosts."""
    stats = host_data.get('stats', {})
    
    return f'''            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Hosts</div>
                    <div class="stat-value">{stats.get('total_hosts', 0)}</div>
                    <div class="stat-detail">{stats.get('hosts_up', 0)} Up, {stats.get('hosts_down', 0)} Down, {stats.get('hosts_maintenance', 0)} Maintenance</div>
                </div>
                <div class="stat-card blue">
                    <div class="stat-label">Total vCPUs</div>
                    <div class="stat-value">{stats.get('total_vcores', 0):,}</div>
                    <div class="stat-detail">{stats.get('total_allocated_vcpus', 0):,} Allocated</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-label">Physical Memory</div>
                    <div class="stat-value">{stats.get('total_physical_memory_gb', 0):,} GB</div>
                    <div class="stat-detail">{stats.get('total_clusters', 0)} Clusters</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Avg CPU Overcommit</div>
                    <div class="stat-value">{stats.get('avg_cpu_overcommit', 0)}x</div>
                    <div class="stat-detail">{stats.get('min_cpu_overcommit', 0)}x - {stats.get('max_cpu_overcommit', 0)}x</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Avg VMs per Host</div>
                    <div class="stat-value">{stats.get('avg_vms_per_host', 0)}</div>
                    <div class="stat-detail">{stats.get('total_running_vms', 0)} Total VMs</div>
                </div>
            </div>
'''


def get_status_badge_class(status_name):
    """Get badge class for host status."""
    if status_name == 'Up':
        return 'badge-on'
    elif status_name in ('Down', 'Error', 'Non-Responsive'):
        return 'badge-high'
    return 'badge-medium'


def get_utilization_badge_class(category):
    """Get badge class for utilization category."""
    badge_map = {
        'Low': 'badge-low',
        'Medium': 'badge-medium',
        'High': 'badge-high',
        'Critical': 'badge-high'
    }
    return badge_map.get(category, 'badge-medium')


def get_overcommit_color(ratio):
    """Get inline color style for overcommit ratio."""
    if ratio >= 4.0:
        return 'color: #e74c3c; font-weight: 700;'
    elif ratio >= 2.5:
        return 'color: #e67e22; font-weight: 700;'
    elif ratio >= 1.5:
        return 'color: #f39c12; font-weight: 600;'
    return 'color: #27ae60; font-weight: 600;'


def generate_hosts_table(host_data):
    """Generate the searchable hosts inventory table."""
    host_list = host_data.get('host_list', [])
    
    # Build table rows
    rows = ''
    for host in host_list:
        status_class = get_status_badge_class(host['status_name'])
        util_class = get_utilization_badge_class(host['utilization_category'])
        oc_style = get_overcommit_color(host['cpu_overcommit'])
        
        rows += f'''                            <tr>
                                <td><span class="host-name">{host['host_name']}</span></td>
                                <td><span class="badge badge-cluster">{host['cluster']}</span></td>
                                <td class="host-cpu-model">{host['cpu_model']}</td>
                                <td class="text-center">{host['cpu_sockets']} × {host['vcores_per_socket']}</td>
                                <td class="text-center">{host['total_vcores']}</td>
                                <td class="text-right">{host['physical_mem_gb']}</td>
                                <td class="text-center">{host['running_vms']}</td>
                                <td class="text-center">{host['allocated_vcpus']}</td>
                                <td class="text-center" style="{oc_style}">{host['cpu_overcommit']}x</td>
                                <td class="text-center"><span class="badge {util_class}">{host['utilization_category']}</span></td>
                                <td class="text-center"><span class="badge {status_class}">{host['status_name']}</span></td>
                            </tr>
'''
    
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">Hosts Inventory ({len(host_list)} Hosts)</div>
                    <div class="search-box">
                        <input type="text" id="hosts-search" placeholder="Search hosts..." />
                    </div>
                </div>
                <div class="table-wrapper">
                    <table id="hosts-table">
                        <thead>
                            <tr>
                                <th>Host Name</th>
                                <th>Cluster</th>
                                <th>CPU Model</th>
                                <th class="text-center">Sockets × vCPUs</th>
                                <th class="text-center">Total vCPUs</th>
                                <th class="text-right">Memory (GB)</th>
                                <th class="text-center">Running VMs</th>
                                <th class="text-center">Allocated vCPUs</th>
                                <th class="text-center">CPU Overcommit</th>
                                <th class="text-center">Utilization</th>
                                <th class="text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody id="hosts-tbody">
{rows}                        </tbody>
                    </table>
                </div>
            </div>
'''


def generate_charts_section():
    """Generate the charts section for hosts tab."""
    return '''            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">CPU Overcommitment by Host</div>
                    <div class="chart-container" style="height:600px;">
                        <canvas id="chart-host-cpu-overcommit"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">VM Density by Host</div>
                    <div class="chart-container" style="height:600px;">
                        <canvas id="chart-host-vm-density"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Hosts by Utilization Level</div>
                    <div class="chart-container small">
                        <canvas id="chart-host-utilization"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Hosts by Status</div>
                    <div class="chart-container small">
                        <canvas id="chart-host-status"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_tab_hosts(data):
    """
    Generate complete HTML for the Hosts Inventory tab.
    
    Args:
        data: Complete data dictionary including host_data
        
    Returns:
        HTML string for the hosts tab content
    """
    host_data = data.get('host_data', {})
    
    # Check if host data is available
    if not host_data.get('has_host_data', False):
        return generate_no_data_message()
    
    html = generate_summary_cards(host_data)
    html += generate_charts_section()
    html += generate_hosts_table(host_data)
    
    return html


def get_hosts_chart_configs(data):
    """
    Get chart configuration data for hosts tab.
    
    Args:
        data: Complete data dictionary including host_data
        
    Returns:
        Dictionary with chart configurations
    """
    host_data = data.get('host_data', {})
    
    if not host_data.get('has_host_data', False):
        return {}
    
    host_list = host_data.get('host_list', [])
    distributions = host_data.get('distributions', {})
    
    # CPU Overcommit by host (bar chart)
    cpu_overcommit_data = {
        'labels': [h['host_name'] for h in host_list],
        'datasets': [{
            'label': 'CPU Overcommit Ratio',
            'data': [h['cpu_overcommit'] for h in host_list],
            'backgroundColor': ['#e74c3c' if h['cpu_overcommit'] >= 4.0 else 
                              '#f39c12' if h['cpu_overcommit'] >= 2.5 else
                              '#3498db' for h in host_list]
        }]
    }
    
    # VM Density by host (bar chart)
    vm_density_data = {
        'labels': [h['host_name'] for h in host_list],
        'datasets': [{
            'label': 'Running VMs',
            'data': [h['running_vms'] for h in host_list],
            'backgroundColor': '#27ae60'
        }]
    }
    
    # Utilization breakdown (donut chart)
    util_dist = distributions.get('by_utilization', {})
    utilization_data = {
        'labels': list(util_dist.keys()),
        'datasets': [{
            'data': list(util_dist.values()),
            'backgroundColor': ['#27ae60', '#f39c12', '#e67e22', '#e74c3c']
        }]
    }
    
    # Status breakdown (donut chart)
    status_dist = distributions.get('by_status', {})
    status_data = {
        'labels': list(status_dist.keys()),
        'datasets': [{
            'data': list(status_dist.values()),
            'backgroundColor': ['#27ae60', '#e74c3c', '#f39c12', '#95a5a6']
        }]
    }
    
    return {
        'cpu_overcommit': cpu_overcommit_data,
        'vm_density': vm_density_data,
        'utilization': utilization_data,
        'status': status_data
    }


# For testing
if __name__ == '__main__':
    # Test with host data
    mock_data = {
        'host_data': {
            'has_host_data': True,
            'stats': {
                'total_hosts': 6,
                'total_vcores': 672,
                'total_physical_memory_gb': 2262,
                'total_running_vms': 115,
                'total_allocated_vcpus': 1089,
                'avg_cpu_overcommit': 1.62,
                'max_cpu_overcommit': 1.68,
                'min_cpu_overcommit': 1.05,
                'avg_vms_per_host': 19.2,
                'hosts_up': 6,
                'hosts_down': 0,
                'total_clusters': 1
            },
            'host_list': [
                {
                    'host_name': 'host-01',
                    'cluster': 'NONPROD',
                    'cpu_model': 'Intel Xeon Gold 6238R',
                    'cpu_sockets': 2,
                    'vcores_per_socket': 56,
                    'total_vcores': 112,
                    'physical_mem_gb': 377,
                    'running_vms': 20,
                    'allocated_vcpus': 188,
                    'allocated_memory_gb': 0,
                    'cpu_overcommit': 1.68,
                    'memory_utilization_pct': 0.0,
                    'utilization_category': 'Medium',
                    'status': 3,
                    'status_name': 'Up'
                }
            ],
            'distributions': {
                'by_utilization': {'Low': 3, 'Medium': 2, 'High': 1},
                'by_status': {'Up': 6}
            }
        }
    }
    
    print("=== With Host Data ===")
    html = generate_tab_hosts(mock_data)
    print(f"HTML generated: {len(html)} characters")
    
    # Test without host data
    mock_data_no_hosts = {
        'host_data': {
            'has_host_data': False
        }
    }
    
    print("\n=== Without Host Data ===")
    html = generate_tab_hosts(mock_data_no_hosts)
    print(f"HTML generated: {len(html)} characters")
