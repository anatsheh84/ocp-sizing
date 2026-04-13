"""
tab_migration.py
----------------
Tab 3: Migration Planning
Displays complexity analysis, migration waves, and pre-migration checklist.
"""


def generate_complexity_cards(distributions):
    """Generate the complexity summary cards."""
    complexity = distributions.get('complexity', {})
    low = complexity.get('Low', 0)
    medium = complexity.get('Medium', 0)
    high = complexity.get('High', 0)
    
    return f'''            <div class="complexity-cards">
                <div class="complexity-card low">
                    <div class="complexity-count">{low}</div>
                    <div class="complexity-label">Low Complexity</div>
                    <div class="complexity-desc">Linux VMs (RHEL 8/9) with standard sizing. Ready for straightforward migration with MTV.</div>
                </div>
                <div class="complexity-card medium">
                    <div class="complexity-count">{medium}</div>
                    <div class="complexity-label">Medium Complexity</div>
                    <div class="complexity-desc">Windows VMs, RHEL 7, or large VMs (>64GB or >16 vCPU). May require VirtIO drivers or additional planning.</div>
                </div>
                <div class="complexity-card high">
                    <div class="complexity-count">{high}</div>
                    <div class="complexity-label">High Complexity</div>
                    <div class="complexity-desc">Large Windows VMs (>64GB RAM or >16 vCPU). Requires careful resource planning and extended testing.</div>
                </div>
            </div>
'''


def generate_migration_waves_table(waves):
    """Generate the migration waves table."""
    rows = ''
    for wave in waves:
        rows += f'''                        <tr>
                            <td><strong>Wave {wave.get('wave', '')}</strong></td>
                            <td>
                                <strong>{wave.get('name', '')}</strong><br>
                                <span class="text-muted">{wave.get('description', '')}</span>
                            </td>
                            <td>{wave.get('vm_count', 0)}</td>
                            <td>{wave.get('vcpus', 0):,}</td>
                            <td>{wave.get('memory_gb', 0):,}</td>
                            <td><span class="text-muted">{wave.get('criteria', '')}</span></td>
                        </tr>
'''
    
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">Suggested Migration Waves</div>
                </div>
                <div class="table-wrapper">
                    <table id="migration-waves-table">
                        <thead>
                            <tr>
                                <th>Wave</th>
                                <th>Description</th>
                                <th>VM Count</th>
                                <th>vCPUs</th>
                                <th>Memory (GB)</th>
                                <th>Criteria</th>
                            </tr>
                        </thead>
                        <tbody>
{rows}                        </tbody>
                    </table>
                </div>
            </div>
'''


def generate_charts_section():
    """Generate the chart containers for the migration tab."""
    return '''            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">Complexity by OS Type</div>
                    <div class="chart-container">
                        <canvas id="chart-complexity-os"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">Migration Waves Overview</div>
                    <div class="chart-container">
                        <canvas id="chart-migration-waves"></canvas>
                    </div>
                </div>
            </div>
'''


def generate_checklist():
    """Generate the pre-migration checklist."""
    checklist_items = [
        {
            'title': 'Install MTV Operator',
            'description': 'Deploy Migration Toolkit for Virtualization operator on OpenShift cluster'
        },
        {
            'title': 'Configure RHV Provider',
            'description': 'Add RHV as source provider with valid credentials and CA certificate'
        },
        {
            'title': 'Set Up Storage Classes',
            'description': 'Create storage classes mapped to RHV storage domains (ODF, NFS, etc.)'
        },
        {
            'title': 'Install VirtIO Drivers (Windows)',
            'description': 'Ensure Windows VMs have latest VirtIO drivers installed before migration'
        },
        {
            'title': 'Configure Network Mappings',
            'description': 'Map RHV networks to OpenShift networks (OVN-Kubernetes, bridge, SR-IOV)'
        },
        {
            'title': 'Verify Resource Capacity',
            'description': 'Ensure OpenShift cluster has sufficient CPU, memory, and storage capacity'
        },
        {
            'title': 'Plan Maintenance Windows',
            'description': 'Schedule migration waves during maintenance windows to minimize impact'
        },
        {
            'title': 'Backup VMs',
            'description': 'Create backups or snapshots of VMs before migration'
        },
        {
            'title': 'Test Migration (Pilot)',
            'description': 'Perform pilot migration with non-critical VMs to validate process'
        },
        {
            'title': 'Document Rollback Plan',
            'description': 'Prepare rollback procedures in case of migration issues'
        }
    ]
    
    items_html = ''
    for item in checklist_items:
        items_html += f'''                <div class="checklist-item">
                    <input type="checkbox" class="checklist-checkbox">
                    <div class="checklist-text">
                        <strong>{item['title']}</strong>
                        <span>{item['description']}</span>
                    </div>
                </div>
'''
    
    return f'''            <div class="checklist">
                <div class="checklist-title">Pre-Migration Checklist</div>
{items_html}            </div>
'''


def generate_tab_migration(data):
    """
    Generate complete HTML for the Migration Planning tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the migration tab content
    """
    distributions = data.get('distributions', {})
    waves = data.get('migration_waves', [])
    
    html = generate_complexity_cards(distributions)
    html += generate_charts_section()
    html += generate_migration_waves_table(waves)
    html += generate_checklist()
    
    return html


def get_migration_chart_configs(data):
    """
    Generate JavaScript chart configuration objects for Migration tab.
    """
    complexity_by_os = data.get('complexity_by_os', {})
    waves = data.get('migration_waves', [])
    
    # Complexity by OS for stacked bar chart
    os_types = list(complexity_by_os.keys())
    low_values = [complexity_by_os[os].get('Low', 0) for os in os_types]
    medium_values = [complexity_by_os[os].get('Medium', 0) for os in os_types]
    high_values = [complexity_by_os[os].get('High', 0) for os in os_types]
    
    # Migration waves data
    wave_labels = [f"Wave {w.get('wave', '')}" for w in waves]
    wave_vms = [w.get('vm_count', 0) for w in waves]
    wave_vcpus = [w.get('vcpus', 0) for w in waves]
    wave_memory = [w.get('memory_gb', 0) for w in waves]
    
    return {
        'complexity_os': {
            'labels': os_types,
            'low': low_values,
            'medium': medium_values,
            'high': high_values
        },
        'migration_waves': {
            'labels': wave_labels,
            'vms': wave_vms,
            'vcpus': wave_vcpus,
            'memory': wave_memory
        }
    }


# For testing
if __name__ == '__main__':
    mock_data = {
        'distributions': {
            'complexity': {'Low': 57, 'Medium': 60, 'High': 1}
        },
        'migration_waves': [
            {'wave': 1, 'name': 'Pilot', 'description': 'Low complexity Linux', 'vm_count': 57, 'vcpus': 400, 'memory_gb': 800, 'criteria': 'Linux, Low complexity'},
            {'wave': 2, 'name': 'Windows', 'description': 'Standard Windows', 'vm_count': 58, 'vcpus': 450, 'memory_gb': 1400, 'criteria': 'Windows, Medium complexity'}
        ],
        'complexity_by_os': {
            'RHEL 8': {'Low': 30, 'Medium': 5, 'High': 0},
            'Windows 2022': {'Low': 0, 'Medium': 35, 'High': 1}
        }
    }
    
    html = generate_tab_migration(mock_data)
    print(f"Migration tab HTML generated: {len(html)} characters")
