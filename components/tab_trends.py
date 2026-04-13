"""
tab_trends.py
-------------
Tab 4: Growth Trends
Displays historical VM creation and resource growth over time.
Handles cases where date data is not available (e.g., VMware/RVTools).
"""


def generate_no_data_message():
    """Generate message when date data is not available."""
    return '''            <div class="no-data-message">
                <div class="icon">📊</div>
                <h3>Trend Data Not Available</h3>
                <p>VM creation date information is not available from this data source.</p>
                <p>This tab requires historical date data to display growth trends.</p>
                <p style="margin-top: 20px; font-size: 14px; color: #999;">
                    <strong>Tip:</strong> RHV exports include creation dates. VMware/RVTools exports do not include this data.
                </p>
            </div>
'''


def generate_stat_cards(stats):
    """Generate the trends stat cards HTML."""
    first_date = stats.get('first_vm_date', 'N/A')
    last_date = stats.get('last_vm_date', 'N/A')
    avg_per_month = stats.get('avg_vms_per_month', 0)
    peak_month = stats.get('peak_month', 'N/A')
    peak_count = stats.get('peak_month_count', 0)
    
    return f'''            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">First VM Created</div>
                    <div class="stat-value" style="font-size: 24px;">{first_date}</div>
                    <div class="stat-detail">Earliest VM in inventory</div>
                </div>
                <div class="stat-card blue">
                    <div class="stat-label">Last VM Created</div>
                    <div class="stat-value" style="font-size: 24px;">{last_date}</div>
                    <div class="stat-detail">Most recent VM provisioned</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-label">Avg VMs/Month</div>
                    <div class="stat-value">{avg_per_month}</div>
                    <div class="stat-detail">Average monthly provisioning rate</div>
                </div>
                <div class="stat-card orange">
                    <div class="stat-label">Peak Month</div>
                    <div class="stat-value" style="font-size: 24px;">{peak_month}</div>
                    <div class="stat-detail">{peak_count} VMs provisioned</div>
                </div>
            </div>
'''


def generate_charts_section():
    """Generate the chart containers for the trends tab."""
    return '''            <div class="charts-grid">
                <div class="chart-card full-width">
                    <div class="chart-title">VM Count Growth Over Time (Cumulative)</div>
                    <div class="chart-container">
                        <canvas id="chart-vm-growth"></canvas>
                    </div>
                </div>
                <div class="chart-card full-width">
                    <div class="chart-title">CPU & Memory Growth Over Time (Cumulative)</div>
                    <div class="chart-container">
                        <canvas id="chart-resource-growth"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">VMs Provisioned Per Month</div>
                    <div class="chart-container">
                        <canvas id="chart-vms-per-month"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Resources Added Per Month</div>
                    <div class="chart-container">
                        <canvas id="chart-resources-per-month"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_tab_trends(data):
    """
    Generate complete HTML for the Growth Trends tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the trends tab content
    """
    # Check if date data is available
    if not data.get('has_date_data', True):
        return generate_no_data_message()
    
    # Check if we have actual trend data
    growth_trends = data.get('growth_trends')
    if not growth_trends:
        return generate_no_data_message()
    
    stats = data.get('stats', {})
    
    html = generate_stat_cards(stats)
    html += generate_charts_section()
    
    return html


def get_trends_chart_configs(data):
    """
    Generate JavaScript chart configuration objects for Trends tab.
    """
    # Check if date data is available
    if not data.get('has_date_data', True):
        return {
            'vm_growth': {'labels': [], 'values': []},
            'resource_growth': {'labels': [], 'vcpus': [], 'memory': []},
            'vms_per_month': {'labels': [], 'values': []},
            'resources_per_month': {'labels': [], 'vcpus': [], 'memory': []}
        }
    
    trends = data.get('growth_trends', {})
    
    if not trends:
        return {
            'vm_growth': {'labels': [], 'values': []},
            'resource_growth': {'labels': [], 'vcpus': [], 'memory': []},
            'vms_per_month': {'labels': [], 'values': []},
            'resources_per_month': {'labels': [], 'vcpus': [], 'memory': []}
        }
    
    return {
        'vm_growth': {
            'labels': trends.get('months', []),
            'values': trends.get('cumulative_vms', [])
        },
        'resource_growth': {
            'labels': trends.get('months', []),
            'vcpus': trends.get('cumulative_vcpus', []),
            'memory': trends.get('cumulative_memory', [])
        },
        'vms_per_month': {
            'labels': trends.get('months', []),
            'values': trends.get('monthly_vms', [])
        },
        'resources_per_month': {
            'labels': trends.get('months', []),
            'vcpus': trends.get('monthly_vcpus', []),
            'memory': trends.get('monthly_memory', [])
        }
    }


# For testing
if __name__ == '__main__':
    # Test with date data
    mock_data_with_dates = {
        'has_date_data': True,
        'stats': {
            'first_vm_date': '2023-08-20',
            'last_vm_date': '2025-11-04',
            'avg_vms_per_month': 4.5,
            'peak_month': '2023-09',
            'peak_month_count': 35
        },
        'growth_trends': {
            'months': ['2023-08', '2023-09', '2023-10'],
            'monthly_vms': [2, 35, 10],
            'cumulative_vms': [2, 37, 47]
        }
    }
    
    print("=== With Date Data ===")
    html = generate_tab_trends(mock_data_with_dates)
    print(f"HTML generated: {len(html)} characters")
    
    # Test without date data
    mock_data_no_dates = {
        'has_date_data': False,
        'stats': {}
    }
    
    print("\n=== Without Date Data ===")
    html = generate_tab_trends(mock_data_no_dates)
    print(f"HTML generated: {len(html)} characters")
    print(html)
