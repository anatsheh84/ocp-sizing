"""
tab_forecast.py
---------------
Tab 5: Forecasting (2026-2028)
Displays growth projections and infrastructure sizing recommendations.
Handles cases where date data is not available (e.g., VMware/RVTools).
"""


def generate_no_data_message():
    """Generate message when date data is not available."""
    return '''            <div class="no-data-message">
                <div class="icon">🔮</div>
                <h3>Forecast Data Not Available</h3>
                <p>VM creation date information is not available from this data source.</p>
                <p>Forecasting requires historical growth data to project future infrastructure needs.</p>
                <p style="margin-top: 20px; font-size: 14px; color: #999;">
                    <strong>Tip:</strong> RHV exports include creation dates which enable growth forecasting. 
                    VMware/RVTools exports do not include this data.
                </p>
                <p style="margin-top: 15px; font-size: 14px; color: #666;">
                    You can still use the <strong>Sizing Analysis</strong> and <strong>Migration Planning</strong> 
                    tabs to plan your migration based on current resource requirements.
                </p>
            </div>
'''


def generate_config_panel():
    """Generate the forecast configuration panel."""
    return '''            <div class="config-panel">
                <div class="config-title">Forecast Configuration</div>
                <div class="config-grid">
                    <div class="config-group">
                        <label>Growth Scenario</label>
                        <select id="growth-scenario" onchange="toggleCustomGrowth()">
                            <option value="5">Conservative (+5% annually)</option>
                            <option value="15" selected>Typical (+15% annually)</option>
                            <option value="25">Aggressive (+25% annually)</option>
                            <option value="custom">Custom</option>
                        </select>
                    </div>
                    <div class="config-group">
                        <label>Custom Growth Rate (%)</label>
                        <input type="number" id="custom-growth" value="15" min="0" max="100" disabled>
                    </div>
                    <div class="config-group">
                        <label>Node Specification</label>
                        <select id="node-spec">
                            <option value="small">Small: 32 cores / 64 vCPU / 512 GB RAM</option>
                            <option value="medium" selected>Medium: 64 cores / 128 vCPU / 1024 GB RAM</option>
                            <option value="large">Large: 128 cores / 256 vCPU / 2048 GB RAM</option>
                        </select>
                    </div>
                </div>
                <button class="apply-btn" onclick="applyForecast()">Apply & Recalculate</button>
            </div>
'''


def generate_assumptions_table(stats):
    """Generate the forecast assumptions table."""
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">Forecast Assumptions</div>
                </div>
                <div class="table-wrapper">
                    <table id="forecast-assumptions-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Current Value (2025)</th>
                                <th>Growth Rate</th>
                                <th>Notes</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Total VMs</td>
                                <td id="assumption-vms">{stats.get('total_vms', 0)}</td>
                                <td id="assumption-growth">+15% annually</td>
                                <td class="assumptions-note">Applied to VM count, vCPUs, and memory</td>
                            </tr>
                            <tr>
                                <td>Total vCPUs</td>
                                <td id="assumption-vcpus">{stats.get('total_vcpus', 0):,}</td>
                                <td>—</td>
                                <td class="assumptions-note">Scales proportionally with VMs</td>
                            </tr>
                            <tr>
                                <td>Total Memory</td>
                                <td id="assumption-memory">{stats.get('total_memory_gb', 0):,} GB</td>
                                <td>—</td>
                                <td class="assumptions-note">Scales proportionally with VMs</td>
                            </tr>
                            <tr>
                                <td>Overhead Factor</td>
                                <td>1.2x (20%)</td>
                                <td>—</td>
                                <td class="assumptions-note">Added buffer for scheduling and burst</td>
                            </tr>
                            <tr>
                                <td>Minimum Nodes</td>
                                <td>3</td>
                                <td>—</td>
                                <td class="assumptions-note">High availability requirement</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
'''


def generate_year_cards(stats):
    """Generate the year projection cards."""
    total_vms = stats.get('total_vms', 0)
    total_vcpus = stats.get('total_vcpus', 0)
    total_memory = stats.get('total_memory_gb', 0)
    
    return f'''            <div class="year-cards" id="year-projections">
                <div class="year-card current">
                    <div class="year-label">Current</div>
                    <div class="year-title">2025</div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2025-vms">{total_vms}</div>
                        <div class="year-stat-label">VMs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2025-vcpus">{total_vcpus:,}</div>
                        <div class="year-stat-label">vCPUs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2025-memory">{total_memory:,}</div>
                        <div class="year-stat-label">GB Memory</div>
                    </div>
                </div>
                <div class="year-card projected">
                    <div class="year-label">Projected</div>
                    <div class="year-title">2026</div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2026-vms">—</div>
                        <div class="year-stat-label">VMs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2026-vcpus">—</div>
                        <div class="year-stat-label">vCPUs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2026-memory">—</div>
                        <div class="year-stat-label">GB Memory</div>
                    </div>
                </div>
                <div class="year-card projected">
                    <div class="year-label">Projected</div>
                    <div class="year-title">2027</div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2027-vms">—</div>
                        <div class="year-stat-label">VMs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2027-vcpus">—</div>
                        <div class="year-stat-label">vCPUs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2027-memory">—</div>
                        <div class="year-stat-label">GB Memory</div>
                    </div>
                </div>
                <div class="year-card projected">
                    <div class="year-label">Projected</div>
                    <div class="year-title">2028</div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2028-vms">—</div>
                        <div class="year-stat-label">VMs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2028-vcpus">—</div>
                        <div class="year-stat-label">vCPUs</div>
                    </div>
                    <div class="year-stat">
                        <div class="year-stat-value" id="year-2028-memory">—</div>
                        <div class="year-stat-label">GB Memory</div>
                    </div>
                </div>
            </div>
'''


def generate_forecast_chart():
    """Generate the forecast chart container."""
    return '''            <div class="charts-grid">
                <div class="chart-card full-width">
                    <div class="chart-title">Resource Forecast (Historical + Projected)</div>
                    <div class="chart-container tall">
                        <canvas id="chart-forecast"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_infrastructure_table(data):
    """Generate the infrastructure sizing table."""
    distributions = data.get('distributions', {})
    cluster_data = distributions.get('by_cluster', {})
    
    rows = ''
    for cluster_name, cluster_stats in cluster_data.items():
        vm_count = cluster_stats.get('vm_count', 0)
        rows += f'''                            <tr data-cluster="{cluster_name}">
                                <td><span class="badge badge-cluster">{cluster_name}</span></td>
                                <td>{vm_count}</td>
                                <td class="infra-2028-vms">—</td>
                                <td class="infra-2028-vcpus">—</td>
                                <td class="infra-2028-memory">—</td>
                                <td class="infra-node-spec">Medium</td>
                                <td class="infra-nodes">—</td>
                            </tr>
'''
    
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">Infrastructure Sizing for 2028</div>
                </div>
                <div class="table-wrapper">
                    <table id="infrastructure-table">
                        <thead>
                            <tr>
                                <th>Cluster</th>
                                <th>Current VMs</th>
                                <th>2028 VMs</th>
                                <th>2028 vCPUs</th>
                                <th>2028 Memory (GB)</th>
                                <th>Node Spec</th>
                                <th>Recommended Nodes</th>
                            </tr>
                        </thead>
                        <tbody id="infrastructure-tbody">
{rows}                        </tbody>
                        <tfoot id="infrastructure-tfoot">
                            <tr style="font-weight: bold; background: #f8f8f8;">
                                <td>TOTAL</td>
                                <td id="infra-total-current">{data.get('stats', {}).get('total_vms', 0)}</td>
                                <td id="infra-total-2028-vms">—</td>
                                <td id="infra-total-2028-vcpus">—</td>
                                <td id="infra-total-2028-memory">—</td>
                                <td>—</td>
                                <td id="infra-total-nodes">—</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
'''


def generate_tab_forecast(data):
    """
    Generate complete HTML for the Forecasting tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the forecast tab content
    """
    # Check if date data is available
    if not data.get('has_date_data', True):
        return generate_no_data_message()
    
    stats = data.get('stats', {})
    
    html = generate_config_panel()
    html += generate_assumptions_table(stats)
    html += generate_year_cards(stats)
    html += generate_forecast_chart()
    html += generate_infrastructure_table(data)
    
    return html


def get_forecast_base_data(data):
    """
    Get the base data needed for forecast calculations in JavaScript.
    """
    # Check if date data is available
    if not data.get('has_date_data', True):
        return {
            'current': {'vms': 0, 'vcpus': 0, 'memory': 0},
            'clusters': [],
            'node_specs': {
                'small': {'vcpus': 64, 'memory': 512},
                'medium': {'vcpus': 128, 'memory': 1024},
                'large': {'vcpus': 256, 'memory': 2048}
            }
        }
    
    stats = data.get('stats', {})
    distributions = data.get('distributions', {})
    cluster_data = distributions.get('by_cluster', {})
    
    clusters = []
    for cluster_name, cluster_stats in cluster_data.items():
        clusters.append({
            'name': cluster_name,
            'vms': cluster_stats.get('vm_count', 0),
            'vcpus': cluster_stats.get('num_of_cpus', 0),
            'memory': cluster_stats.get('mem_size_GB', 0)
        })
    
    return {
        'current': {
            'vms': stats.get('total_vms', 0),
            'vcpus': stats.get('total_vcpus', 0),
            'memory': stats.get('total_memory_gb', 0)
        },
        'clusters': clusters,
        'node_specs': {
            'small': {'vcpus': 64, 'memory': 512},
            'medium': {'vcpus': 128, 'memory': 1024},
            'large': {'vcpus': 256, 'memory': 2048}
        }
    }


# For testing
if __name__ == '__main__':
    # Test with date data
    mock_data_with_dates = {
        'has_date_data': True,
        'stats': {
            'total_vms': 118,
            'total_vcpus': 893,
            'total_memory_gb': 2405
        },
        'distributions': {
            'by_cluster': {
                'HH-NONPROD-CLU01': {'vm_count': 118, 'num_of_cpus': 893, 'mem_size_GB': 2405}
            }
        }
    }
    
    print("=== With Date Data ===")
    html = generate_tab_forecast(mock_data_with_dates)
    print(f"HTML generated: {len(html)} characters")
    
    # Test without date data
    mock_data_no_dates = {
        'has_date_data': False,
        'stats': {}
    }
    
    print("\n=== Without Date Data ===")
    html = generate_tab_forecast(mock_data_no_dates)
    print(f"HTML generated: {len(html)} characters")
    print(html)
