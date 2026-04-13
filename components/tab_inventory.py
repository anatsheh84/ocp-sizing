"""
tab_inventory.py
----------------
Tab 6: VM Inventory
Displays the full VM inventory table with filtering and sorting.
"""


def get_status_badge(status):
    """Get the appropriate badge class for VM status."""
    if status.lower() == 'on':
        return 'badge-on', 'Running'
    return 'badge-off', 'Stopped'


def get_complexity_badge(complexity):
    """Get the appropriate badge class for complexity."""
    badge_map = {
        'Low': 'badge-low',
        'Medium': 'badge-medium',
        'High': 'badge-high'
    }
    return badge_map.get(complexity, 'badge-medium')


def get_size_badge(size_category):
    """Get the appropriate badge class for size category."""
    badge_map = {
        'Small': 'badge-small',
        'Medium': 'badge-size-medium',
        'Large': 'badge-large',
        'X-Large': 'badge-xlarge'
    }
    return badge_map.get(size_category, 'badge-size-medium')


def get_utilization_badge(utilization):
    """Get the appropriate badge class for storage utilization."""
    if utilization < 50:
        return 'badge-util-low'
    elif utilization < 80:
        return 'badge-util-medium'
    return 'badge-util-high'


def generate_inventory_table(vm_list):
    """Generate the VM inventory table HTML."""
    rows = ''
    for vm in vm_list:
        status_class, status_text = get_status_badge(vm.get('status', ''))
        complexity_class = get_complexity_badge(vm.get('complexity', ''))
        size_class = get_size_badge(vm.get('size_category', ''))
        util_class = get_utilization_badge(vm.get('utilization', 0))
        
        rows += f'''                            <tr class="vm-row" 
                                data-cluster="{vm.get('cluster', '')}"
                                data-osfamily="{vm.get('os_family', '')}"
                                data-status="{vm.get('status', '')}"
                                data-complexity="{vm.get('complexity', '')}"
                                data-host="{vm.get('host', '')}">
                                <td>{vm.get('vm_name', '')}</td>
                                <td><span class="badge badge-cluster">{vm.get('cluster', '')}</span></td>
                                <td>{vm.get('guest_os', '')}</td>
                                <td>{vm.get('host', '')}</td>
                                <td><span class="badge {status_class}">{status_text}</span></td>
                                <td>{vm.get('memory_gb', 0)}</td>
                                <td>{vm.get('vcpus', 0)}</td>
                                <td>{vm.get('storage_gb', 0):,.0f}</td>
                                <td><span class="badge {util_class}">{vm.get('utilization', 0):.1f}%</span></td>
                                <td><span class="badge {size_class}">{vm.get('size_category', '')}</span></td>
                                <td><span class="badge {complexity_class}">{vm.get('complexity', '')}</span></td>
                            </tr>
'''
    
    total_vms = len(vm_list)
    
    return f'''            <div class="table-container">
                <div class="table-header">
                    <div class="table-title">VM Inventory</div>
                </div>
                <div class="table-wrapper scrollable">
                    <table id="inventory-table">
                        <thead>
                            <tr>
                                <th>VM Name</th>
                                <th>Cluster</th>
                                <th>Guest OS</th>
                                <th>Host</th>
                                <th>Status</th>
                                <th>Memory (GB)</th>
                                <th>vCPUs</th>
                                <th>Storage (GB)</th>
                                <th>Utilization</th>
                                <th>Size Category</th>
                                <th>Migration Complexity</th>
                            </tr>
                        </thead>
                        <tbody id="inventory-tbody">
{rows}                        </tbody>
                    </table>
                </div>
                <div class="table-footer" id="inventory-footer">
                    Showing <span id="filtered-count">{total_vms}</span> of <span id="total-count">{total_vms}</span> VMs
                </div>
            </div>
'''


def generate_tab_inventory(data):
    """
    Generate complete HTML for the VM Inventory tab.
    
    Args:
        data: Processed data dictionary from data_processor
        
    Returns:
        HTML string for the inventory tab content
    """
    vm_list = data.get('vm_list', [])
    
    return generate_inventory_table(vm_list)


def get_inventory_data(data):
    """
    Get the VM list data for JavaScript filtering.
    Returns the raw VM list for embedding in JavaScript.
    """
    return data.get('vm_list', [])


# For testing
if __name__ == '__main__':
    mock_data = {
        'vm_list': [
            {
                'vm_name': 'VM-1', 'cluster': 'HH-NONPROD-CLU01', 'guest_os': 'RHEL 8.6',
                'host': 'np-f02-hh-sy03', 'status': 'Off', 'memory_gb': 8, 'vcpus': 4,
                'storage_gb': 200, 'utilization': 4.6, 'size_category': 'Small',
                'complexity': 'Low', 'os_family': 'Linux'
            },
            {
                'vm_name': 'VM-5', 'cluster': 'HH-NONPROD-CLU01', 'guest_os': 'Windows 2022',
                'host': 'np-f02-hh-sy01', 'status': 'On', 'memory_gb': 8, 'vcpus': 16,
                'storage_gb': 200, 'utilization': 6.8, 'size_category': 'Medium',
                'complexity': 'Medium', 'os_family': 'Windows'
            }
        ]
    }
    
    html = generate_tab_inventory(mock_data)
    print(f"Inventory tab HTML generated: {len(html)} characters")
    print("\n--- Preview ---")
    print(html[:2000])
