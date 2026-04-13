"""
tab_sizing.py
-------------
Tab 2: Sizing Analysis
Displays VM sizing details, categories, and resource requirements.
"""


def generate_stat_cards(stats):
    """Generate the sizing stat cards HTML."""
    return f'''            <div class="stats-grid">
                <div class="stat-card green">
                    <div class="stat-label">vCPUs Required</div>
                    <div class="stat-value">{stats.get('total_vcpus', 0):,}</div>
                    <div class="stat-detail">Total virtual CPUs allocated</div>
                </div>
                <div class="stat-card blue">
                    <div class="stat-label">Memory Required</div>
                    <div class="stat-value">{stats.get('total_memory_gb', 0):,}</div>
                    <div class="stat-detail">GB total RAM allocated</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Storage Used</div>
                    <div class="stat-value">{stats.get('total_storage_used_gb', 0):,.0f}</div>
                    <div class="stat-detail">GB actual usage</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-label">Storage Provisioned</div>
                    <div class="stat-value">{stats.get('total_storage_provisioned_gb', 0):,.0f}</div>
                    <div class="stat-detail">GB thin provisioned</div>
                </div>
            </div>
'''


def generate_size_details_table(size_details):
    """Generate the size category details table."""
    rows = ''
    for detail in size_details:
        category = detail.get('category', '')
        badge_class = {
            'Small': 'badge-small',
            'Medium': 'badge-size-medium',
            'Large': 'badge-large',
            'X-Large': 'badge-xlarge'
        }.get(category, '')
        
        rows += f'''                        <tr>
                            <td><span class="badge {badge_class}">{category}</span></td>
                            <td>{detail.get('cpu_range', '')}</td>
                            <td>{detail.get('mem_range', '')}</td>
                            <td>{detail.get('vm_count', 0)}</td>
                            <td>{detail.get('total_vcpus', 0):,}</td>
                            <td>{detail.get('total_memory', 0):,}</td>
                            <td>{detail.get('total_storage', 0):,.0f}</td>
                        </tr>
'''
    
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">VM Size Category Details</div>
                </div>
                <div class="table-wrapper">
                    <table id="size-details-table">
                        <thead>
                            <tr>
                                <th>Size Category</th>
                                <th>CPU Range</th>
                                <th>Memory Range</th>
                                <th>VM Count</th>
                                <th>Total vCPUs</th>
                                <th>Total Memory (GB)</th>
                                <th>Total Storage (GB)</th>
                            </tr>
                        </thead>
                        <tbody>
{rows}                        </tbody>
                    </table>
                </div>
            </div>
'''


def generate_charts_section():
    """Generate the chart containers for the sizing tab."""
    return '''            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">VM Size Distribution</div>
                    <div class="chart-container">
                        <canvas id="chart-size-pie"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Resources by Size Category</div>
                    <div class="chart-container">
                        <canvas id="chart-resources-by-size"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_tab_sizing(data):
    """
    Generate complete HTML for the Sizing Analysis tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the sizing tab content
    """
    stats = data.get('stats', {})
    size_details = data.get('size_details', [])
    
    html = generate_stat_cards(stats)
    html += generate_charts_section()
    html += generate_size_details_table(size_details)
    
    return html


def get_sizing_chart_configs(data):
    """
    Generate JavaScript chart configuration objects for Sizing tab.
    """
    size_details = data.get('size_details', [])
    
    labels = [d.get('category', '') for d in size_details]
    vm_counts = [d.get('vm_count', 0) for d in size_details]
    vcpus = [d.get('total_vcpus', 0) for d in size_details]
    memory = [d.get('total_memory', 0) for d in size_details]
    
    return {
        'size_pie': {
            'labels': labels,
            'values': vm_counts
        },
        'resources_by_size': {
            'labels': labels,
            'vcpus': vcpus,
            'memory': memory
        }
    }


# For testing
if __name__ == '__main__':
    mock_data = {
        'stats': {
            'total_vcpus': 893,
            'total_memory_gb': 2405,
            'total_storage_used_gb': 17264.12,
            'total_storage_provisioned_gb': 60304.99
        },
        'size_details': [
            {'category': 'Small', 'cpu_range': '≤4', 'mem_range': '≤8 GB', 'vm_count': 40, 'total_vcpus': 140, 'total_memory': 280, 'total_storage': 8000},
            {'category': 'Medium', 'cpu_range': '≤8', 'mem_range': '≤32 GB', 'vm_count': 46, 'total_vcpus': 320, 'total_memory': 900, 'total_storage': 20000},
            {'category': 'Large', 'cpu_range': '≤16', 'mem_range': '≤64 GB', 'vm_count': 30, 'total_vcpus': 400, 'total_memory': 1100, 'total_storage': 28000},
            {'category': 'X-Large', 'cpu_range': '>16', 'mem_range': '>64 GB', 'vm_count': 2, 'total_vcpus': 33, 'total_memory': 125, 'total_storage': 4000}
        ]
    }
    
    html = generate_tab_sizing(mock_data)
    print(f"Sizing tab HTML generated: {len(html)} characters")
