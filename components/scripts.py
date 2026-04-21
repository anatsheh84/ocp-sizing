"""
scripts.py
----------
All JavaScript for the dashboard:
- Tab switching
- Filter functionality
- Chart.js configurations
- Forecast calculations
- Dynamic updates
"""

import json


# ---------------------------------------------------------------------------
# SCRIPT_BODY is the static JS body (everything after the data-injection block).
# Phase 2 of the components refactor extracted it from the previous monolithic
# f-string so the JS reads as plain JavaScript with no {{/}} brace escaping.
# The 7 data-bearing const declarations at the top of the <script> are produced
# by build_data_prelude() below; SCRIPT_BODY contains everything after them.
# ---------------------------------------------------------------------------
SCRIPT_BODY = r"""
// Chart instances storage
const charts = {};

// ============================================
// TAB SWITCHING
// ============================================
function switchTab(tabId) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === 'tab-' + tabId);
    });
    
    // Resize charts when switching tabs (fixes rendering issues)
    setTimeout(() => {
        Object.values(charts).forEach(chart => {
            if (chart) chart.resize();
        });
    }, 100);
}

// ============================================
// FILTERING
// ============================================
let filteredData = [...vmData];

function applyFilters() {
    const clusterFilter = document.getElementById('filter-cluster').value;
    const osFilter = document.getElementById('filter-os').value;
    const statusFilter = document.getElementById('filter-status').value;
    const complexityFilter = document.getElementById('filter-complexity').value;
    const hostFilter = document.getElementById('filter-host').value;
    
    filteredData = vmData.filter(vm => {
        if (clusterFilter !== 'all' && vm.cluster !== clusterFilter) return false;
        if (osFilter !== 'all' && vm.os_family !== osFilter) return false;
        if (statusFilter !== 'all' && vm.status !== statusFilter) return false;
        if (complexityFilter !== 'all' && vm.complexity !== complexityFilter) return false;
        if (hostFilter !== 'all' && vm.host !== hostFilter) return false;
        return true;
    });
    
    updateInventoryTable();
    updateAllCharts();
    updateStatCards();
}

function resetFilters() {
    document.getElementById('filter-cluster').value = 'all';
    document.getElementById('filter-os').value = 'all';
    document.getElementById('filter-status').value = 'all';
    document.getElementById('filter-complexity').value = 'all';
    document.getElementById('filter-host').value = 'all';
    applyFilters();
}

// ============================================
// INVENTORY TABLE UPDATE
// ============================================
function updateInventoryTable() {
    const tbody = document.getElementById('inventory-tbody');
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll('.vm-row');
    
    const clusterFilter = document.getElementById('filter-cluster').value;
    const osFilter = document.getElementById('filter-os').value;
    const statusFilter = document.getElementById('filter-status').value;
    const complexityFilter = document.getElementById('filter-complexity').value;
    const hostFilter = document.getElementById('filter-host').value;
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        const cluster = row.dataset.cluster || '';
        const osFamily = row.dataset.osfamily || '';
        const status = row.dataset.status || '';
        const complexity = row.dataset.complexity || '';
        const host = row.dataset.host || '';
        
        let visible = true;
        if (clusterFilter !== 'all' && cluster !== clusterFilter) visible = false;
        if (osFilter !== 'all' && osFamily !== osFilter) visible = false;
        if (statusFilter !== 'all' && status !== statusFilter) visible = false;
        if (complexityFilter !== 'all' && complexity !== complexityFilter) visible = false;
        if (hostFilter !== 'all' && host !== hostFilter) visible = false;
        
        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });
    
    // Update footer count
    const totalCount = vmData.length;
    const filteredCountEl = document.getElementById('filtered-count');
    const totalCountEl = document.getElementById('total-count');
    if (filteredCountEl) filteredCountEl.textContent = visibleCount;
    if (totalCountEl) totalCountEl.textContent = totalCount;
}

// ============================================
// STAT CARDS UPDATE
// ============================================
function updateStatCards() {
    // Calculate stats from filtered data
    const totalVms = filteredData.length;
    const runningVms = filteredData.filter(vm => vm.status === 'On').length;
    const stoppedVms = filteredData.filter(vm => vm.status === 'Off').length;
    
    // Get unique clusters and hosts from filtered data
    const uniqueClusters = new Set(filteredData.map(vm => vm.cluster));
    const uniqueHosts = new Set(filteredData.map(vm => vm.host));
    
    // Calculate totals
    const totalVcpus = filteredData.reduce((sum, vm) => sum + (vm.vcpus || 0), 0);
    const totalMemory = filteredData.reduce((sum, vm) => sum + (vm.memory_gb || 0), 0);
    const storageUsed = filteredData.reduce((sum, vm) => sum + (vm.used_gb || 0), 0);
    const storageProvisioned = filteredData.reduce((sum, vm) => sum + (vm.storage_gb || 0), 0);
    const storageEfficiency = storageProvisioned > 0 ? ((storageUsed / storageProvisioned) * 100).toFixed(1) : 0;
    
    // Update DOM elements
    const updateEl = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = typeof value === 'number' ? value.toLocaleString() : value;
    };
    
    updateEl('stat-total-vms', totalVms);
    updateEl('stat-running-vms', runningVms);
    updateEl('stat-stopped-vms', stoppedVms);
    updateEl('stat-clusters', uniqueClusters.size);
    updateEl('stat-hosts', uniqueHosts.size);
    updateEl('stat-vcpus', totalVcpus);
    updateEl('stat-memory', totalMemory);
    updateEl('stat-storage-used', Math.round(storageUsed));
    updateEl('stat-storage-provisioned', Math.round(storageProvisioned));
    updateEl('stat-storage-efficiency', storageEfficiency);
}

// ============================================
// CHART COLORS
// ============================================
const chartColors = {
    red: '#CC0000',
    blue: '#2196F3',
    green: '#4CAF50',
    orange: '#FF9800',
    purple: '#9C27B0',
    teal: '#009688',
    pink: '#E91E63',
    indigo: '#3F51B5',
    cyan: '#00BCD4',
    lime: '#CDDC39',
    amber: '#FFC107',
    deepOrange: '#FF5722'
};

const sizeColors = {
    'Small': '#4CAF50',
    'Medium': '#2196F3',
    'Large': '#FF9800',
    'X-Large': '#f44336'
};

const complexityColors = {
    'Low': '#4CAF50',
    'Medium': '#FF9800',
    'High': '#f44336'
};

// ============================================
// CHART INITIALIZATION
// ============================================
function initCharts() {
    initOverviewCharts();
    initSizingCharts();
    initMigrationCharts();
    initTrendsCharts();
    initForecastChart();
    initHostsCharts();
}

function initOverviewCharts() {
    // OS Family Pie Chart
    const osFamilyCtx = document.getElementById('chart-os-family');
    if (osFamilyCtx) {
        charts.osFamily = new Chart(osFamilyCtx, {
            type: 'pie',
            data: {
                labels: overviewChartData.os_family?.labels || [],
                datasets: [{
                    data: overviewChartData.os_family?.values || [],
                    backgroundColor: [chartColors.blue, chartColors.orange],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
    
    // Size Categories Bar Chart
    const sizeCatCtx = document.getElementById('chart-size-categories');
    if (sizeCatCtx) {
        charts.sizeCategories = new Chart(sizeCatCtx, {
            type: 'bar',
            data: {
                labels: overviewChartData.size_category?.labels || [],
                datasets: [{
                    label: 'VM Count',
                    data: overviewChartData.size_category?.values || [],
                    backgroundColor: ['#4CAF50', '#2196F3', '#FF9800', '#f44336']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
    
    // Complexity Pie Chart
    const complexityCtx = document.getElementById('chart-complexity');
    if (complexityCtx) {
        charts.complexity = new Chart(complexityCtx, {
            type: 'pie',
            data: {
                labels: overviewChartData.complexity?.labels || [],
                datasets: [{
                    data: overviewChartData.complexity?.values || [],
                    backgroundColor: ['#4CAF50', '#FF9800', '#f44336'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
    
    // Cluster Resources Bar Chart
    const clusterCtx = document.getElementById('chart-cluster-resources');
    if (clusterCtx) {
        charts.clusterResources = new Chart(clusterCtx, {
            type: 'bar',
            data: {
                labels: overviewChartData.cluster?.labels || [],
                datasets: [
                    {
                        label: 'VMs',
                        data: overviewChartData.cluster?.vms || [],
                        backgroundColor: chartColors.blue
                    },
                    {
                        label: 'vCPUs (÷10)',
                        data: (overviewChartData.cluster?.vcpus || []).map(v => v / 10),
                        backgroundColor: chartColors.green
                    },
                    {
                        label: 'Memory GB (÷100)',
                        data: (overviewChartData.cluster?.memory || []).map(v => v / 100),
                        backgroundColor: chartColors.orange
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Host Resources Data Table (replaces chart for better readability)
    initHostResourceTable();
    
    // Guest OS Bar Chart
    const guestOsCtx = document.getElementById('chart-guest-os');
    if (guestOsCtx) {
        const labels = overviewChartData.guest_os?.labels || [];
        const colors = labels.map(label => 
            label.toLowerCase().includes('windows') ? chartColors.blue : chartColors.red
        );
        
        charts.guestOs = new Chart(guestOsCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'VM Count',
                    data: overviewChartData.guest_os?.values || [],
                    backgroundColor: colors
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

function initSizingCharts() {
    // Size Distribution Pie
    const sizePieCtx = document.getElementById('chart-size-pie');
    if (sizePieCtx) {
        charts.sizePie = new Chart(sizePieCtx, {
            type: 'pie',
            data: {
                labels: sizingChartData.size_pie?.labels || [],
                datasets: [{
                    data: sizingChartData.size_pie?.values || [],
                    backgroundColor: ['#4CAF50', '#2196F3', '#FF9800', '#f44336'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }
    
    // Resources by Size Bar Chart
    const resourcesSizeCtx = document.getElementById('chart-resources-by-size');
    if (resourcesSizeCtx) {
        charts.resourcesBySize = new Chart(resourcesSizeCtx, {
            type: 'bar',
            data: {
                labels: sizingChartData.resources_by_size?.labels || [],
                datasets: [
                    {
                        label: 'vCPUs',
                        data: sizingChartData.resources_by_size?.vcpus || [],
                        backgroundColor: chartColors.green
                    },
                    {
                        label: 'Memory (GB)',
                        data: sizingChartData.resources_by_size?.memory || [],
                        backgroundColor: chartColors.blue
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

// ============================================
// HOST RESOURCE TABLE (Data Table with Mini Bars)
// ============================================
let hostTableData = [];
let hostSortColumn = 1; // Default sort by VMs
let hostSortAsc = false; // Descending by default

function initHostResourceTable() {
    const tbody = document.getElementById('host-table-body');
    if (!tbody) return;
    
    // Build host data array
    const labels = overviewChartData.host?.labels || [];
    const vms = overviewChartData.host?.vms || [];
    const vcpus = overviewChartData.host?.vcpus || [];
    const memory = overviewChartData.host?.memory || [];
    
    hostTableData = labels.map((name, i) => ({
        name: name,
        vms: vms[i] || 0,
        vcpus: vcpus[i] || 0,
        memory: memory[i] || 0
    }));
    
    // Sort by VMs descending initially
    hostTableData.sort((a, b) => b.vms - a.vms);
    
    renderHostTable();
}

function renderHostTable() {
    const tbody = document.getElementById('host-table-body');
    if (!tbody) return;
    
    const maxVms = Math.max(...hostTableData.map(h => h.vms), 1);
    
    tbody.innerHTML = hostTableData.map(host => {
        const pct = (host.vms / maxVms * 100).toFixed(0);
        return `
            <tr>
                <td><strong>${host.name}</strong></td>
                <td>${host.vms}</td>
                <td>
                    <div class="mini-bar">
                        <div class="mini-bar-fill vms" style="width: ${pct}%"></div>
                    </div>
                </td>
                <td>${host.vcpus.toLocaleString()}</td>
                <td>${host.memory.toLocaleString()}</td>
            </tr>
        `;
    }).join('');
}

function sortHostTable(colIndex) {
    // Toggle sort direction if same column
    if (hostSortColumn === colIndex) {
        hostSortAsc = !hostSortAsc;
    } else {
        hostSortColumn = colIndex;
        hostSortAsc = false; // Default descending for numbers
    }
    
    const keys = ['name', 'vms', 'vms', 'vcpus', 'memory']; // col 2 uses vms for distribution
    const key = keys[colIndex];
    
    hostTableData.sort((a, b) => {
        let cmp = 0;
        if (typeof a[key] === 'string') {
            cmp = a[key].localeCompare(b[key]);
        } else {
            cmp = a[key] - b[key];
        }
        return hostSortAsc ? cmp : -cmp;
    });
    
    renderHostTable();
}

function updateHostResourceTable() {
    // Rebuild host data from filtered data
    const hostData = sumBy(filteredData, 'host', ['vcpus', 'memory_gb']);
    
    hostTableData = Object.keys(hostData).map(name => ({
        name: name,
        vms: hostData[name].count || 0,
        vcpus: hostData[name].vcpus || 0,
        memory: hostData[name].memory_gb || 0
    }));
    
    // Re-sort by current sort column
    const keys = ['name', 'vms', 'vms', 'vcpus', 'memory'];
    const key = keys[hostSortColumn];
    
    hostTableData.sort((a, b) => {
        let cmp = 0;
        if (typeof a[key] === 'string') {
            cmp = a[key].localeCompare(b[key]);
        } else {
            cmp = a[key] - b[key];
        }
        return hostSortAsc ? cmp : -cmp;
    });
    
    renderHostTable();
}

function initMigrationCharts() {
    // Complexity by OS Stacked Bar
    const complexityOsCtx = document.getElementById('chart-complexity-os');
    if (complexityOsCtx) {
        charts.complexityOs = new Chart(complexityOsCtx, {
            type: 'bar',
            data: {
                labels: migrationChartData.complexity_os?.labels || [],
                datasets: [
                    {
                        label: 'Low',
                        data: migrationChartData.complexity_os?.low || [],
                        backgroundColor: '#4CAF50'
                    },
                    {
                        label: 'Medium',
                        data: migrationChartData.complexity_os?.medium || [],
                        backgroundColor: '#FF9800'
                    },
                    {
                        label: 'High',
                        data: migrationChartData.complexity_os?.high || [],
                        backgroundColor: '#f44336'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                }
            }
        });
    }
    
    // Migration Waves Bar Chart
    const wavesCtx = document.getElementById('chart-migration-waves');
    if (wavesCtx) {
        charts.migrationWaves = new Chart(wavesCtx, {
            type: 'bar',
            data: {
                labels: migrationChartData.migration_waves?.labels || [],
                datasets: [
                    {
                        label: 'VMs',
                        data: migrationChartData.migration_waves?.vms || [],
                        backgroundColor: chartColors.blue
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

function initTrendsCharts() {
    // VM Growth Line Chart
    const vmGrowthCtx = document.getElementById('chart-vm-growth');
    if (vmGrowthCtx) {
        charts.vmGrowth = new Chart(vmGrowthCtx, {
            type: 'line',
            data: {
                labels: trendsChartData.vm_growth?.labels || [],
                datasets: [{
                    label: 'Cumulative VMs',
                    data: trendsChartData.vm_growth?.values || [],
                    borderColor: chartColors.red,
                    backgroundColor: 'rgba(204, 0, 0, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Resource Growth Dual Axis
    const resourceGrowthCtx = document.getElementById('chart-resource-growth');
    if (resourceGrowthCtx) {
        charts.resourceGrowth = new Chart(resourceGrowthCtx, {
            type: 'line',
            data: {
                labels: trendsChartData.resource_growth?.labels || [],
                datasets: [
                    {
                        label: 'Cumulative vCPUs',
                        data: trendsChartData.resource_growth?.vcpus || [],
                        borderColor: chartColors.green,
                        backgroundColor: 'transparent',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cumulative Memory (GB)',
                        data: trendsChartData.resource_growth?.memory || [],
                        borderColor: chartColors.blue,
                        backgroundColor: 'transparent',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true,
                        title: { display: true, text: 'vCPUs' }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        beginAtZero: true,
                        title: { display: true, text: 'Memory (GB)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }
    
    // VMs Per Month Bar
    const vmsMonthCtx = document.getElementById('chart-vms-per-month');
    if (vmsMonthCtx) {
        charts.vmsPerMonth = new Chart(vmsMonthCtx, {
            type: 'bar',
            data: {
                labels: trendsChartData.vms_per_month?.labels || [],
                datasets: [{
                    label: 'VMs Provisioned',
                    data: trendsChartData.vms_per_month?.values || [],
                    backgroundColor: chartColors.red
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Resources Per Month Bar
    const resourcesMonthCtx = document.getElementById('chart-resources-per-month');
    if (resourcesMonthCtx) {
        charts.resourcesPerMonth = new Chart(resourcesMonthCtx, {
            type: 'bar',
            data: {
                labels: trendsChartData.resources_per_month?.labels || [],
                datasets: [
                    {
                        label: 'vCPUs Added',
                        data: trendsChartData.resources_per_month?.vcpus || [],
                        backgroundColor: chartColors.green
                    },
                    {
                        label: 'Memory Added (GB ÷10)',
                        data: (trendsChartData.resources_per_month?.memory || []).map(v => v / 10),
                        backgroundColor: chartColors.blue
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

function initForecastChart() {
    const forecastCtx = document.getElementById('chart-forecast');
    if (forecastCtx) {
        charts.forecast = new Chart(forecastCtx, {
            type: 'line',
            data: {
                labels: ['2025', '2026', '2027', '2028'],
                datasets: [
                    {
                        label: 'VMs',
                        data: [forecastBaseData.current?.vms || 0],
                        borderColor: chartColors.red,
                        backgroundColor: 'transparent',
                        tension: 0.3
                    },
                    {
                        label: 'vCPUs (÷10)',
                        data: [(forecastBaseData.current?.vcpus || 0) / 10],
                        borderColor: chartColors.green,
                        backgroundColor: 'transparent',
                        tension: 0.3
                    },
                    {
                        label: 'Memory GB (÷100)',
                        data: [(forecastBaseData.current?.memory || 0) / 100],
                        borderColor: chartColors.blue,
                        backgroundColor: 'transparent',
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
    
    // Initialize with default forecast
    applyForecast();
}

// ============================================
// HOSTS CHARTS
// ============================================
function initHostsCharts() {
    if (!hostsChartData || Object.keys(hostsChartData).length === 0) return;

    // CPU Overcommitment by Host (horizontal bar)
    const cpuOcCtx = document.getElementById('chart-host-cpu-overcommit');
    if (cpuOcCtx && hostsChartData.cpu_overcommit) {
        // Shorten labels for display
        const shortLabels = (hostsChartData.cpu_overcommit.labels || []).map(l => l.replace(/^host-dc01-rhv-/, '').replace(/\.host$/, ''));
        charts.hostCpuOvercommit = new Chart(cpuOcCtx, {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: hostsChartData.cpu_overcommit.datasets || []
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Overcommit Ratio' }, beginAtZero: true }
                }
            }
        });
    }

    // VM Density by Host (horizontal bar)
    const vmDensityCtx = document.getElementById('chart-host-vm-density');
    if (vmDensityCtx && hostsChartData.vm_density) {
        const shortLabels = (hostsChartData.vm_density.labels || []).map(l => l.replace(/^host-dc01-rhv-/, '').replace(/\.host$/, ''));
        charts.hostVmDensity = new Chart(vmDensityCtx, {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: hostsChartData.vm_density.datasets || []
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Running VMs' }, beginAtZero: true }
                }
            }
        });
    }

    // Hosts by Utilization Level (doughnut)
    const utilCtx = document.getElementById('chart-host-utilization');
    if (utilCtx && hostsChartData.utilization) {
        charts.hostUtilization = new Chart(utilCtx, {
            type: 'doughnut',
            data: hostsChartData.utilization,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }

    // Hosts by Status (doughnut)
    const statusCtx = document.getElementById('chart-host-status');
    if (statusCtx && hostsChartData.status) {
        charts.hostStatus = new Chart(statusCtx, {
            type: 'doughnut',
            data: hostsChartData.status,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
}

// ============================================
// FORECAST CALCULATIONS
// ============================================
function toggleCustomGrowth() {
    const scenario = document.getElementById('growth-scenario').value;
    const customInput = document.getElementById('custom-growth');
    customInput.disabled = scenario !== 'custom';
}

function toggleCustomNodeSpec() {
    const spec = document.getElementById('node-spec').value;
    const customRow = document.getElementById('custom-node-spec-row');
    if (customRow) {
        customRow.style.display = spec === 'custom' ? 'flex' : 'none';
    }
}

function applyForecast() {
    const scenarioSelect = document.getElementById('growth-scenario');
    const customInput = document.getElementById('custom-growth');
    const nodeSpecSelect = document.getElementById('node-spec');
    
    let growthRate = parseInt(scenarioSelect.value);
    if (scenarioSelect.value === 'custom') {
        growthRate = parseInt(customInput.value);
        if (isNaN(growthRate)) growthRate = 15;
    }
    
    const nodeSpec = nodeSpecSelect.value;
    const nodeSpecs = forecastBaseData.node_specs || {
        small: { vcpus: 64, memory: 512 },
        medium: { vcpus: 128, memory: 1024 },
        large: { vcpus: 256, memory: 2048 }
    };
    
    const currentVms = forecastBaseData.current?.vms || 0;
    const currentVcpus = forecastBaseData.current?.vcpus || 0;
    const currentMemory = forecastBaseData.current?.memory || 0;
    
    // Calculate projections
    const years = [2025, 2026, 2027, 2028];
    const projections = {};
    
    years.forEach((year, i) => {
        const factor = Math.pow(1 + growthRate / 100, i);
        projections[year] = {
            vms: Math.ceil(currentVms * factor),
            vcpus: Math.ceil(currentVcpus * factor),
            memory: Math.ceil(currentMemory * factor)
        };
    });
    
    // Update year cards
    years.forEach(year => {
        const vmsEl = document.getElementById(`year-${year}-vms`);
        const vcpusEl = document.getElementById(`year-${year}-vcpus`);
        const memoryEl = document.getElementById(`year-${year}-memory`);
        
        if (vmsEl) vmsEl.textContent = projections[year].vms.toLocaleString();
        if (vcpusEl) vcpusEl.textContent = projections[year].vcpus.toLocaleString();
        if (memoryEl) memoryEl.textContent = projections[year].memory.toLocaleString();
    });
    
    // Update assumptions table
    const growthText = `+${growthRate}% annually`;
    const assumptionGrowth = document.getElementById('assumption-growth');
    if (assumptionGrowth) assumptionGrowth.textContent = growthText;
    
    // Update overhead assumption display
    const overheadInput = document.getElementById('overhead-factor');
    const overheadPct = overheadInput ? (parseInt(overheadInput.value) || 20) : 20;
    const overheadFactor = 1 + overheadPct / 100;
    const assumptionOverhead = document.getElementById('assumption-overhead');
    if (assumptionOverhead) assumptionOverhead.textContent = `${overheadFactor.toFixed(1)}x (${overheadPct}%)`;
    
    // Update forecast chart
    if (charts.forecast) {
        charts.forecast.data.datasets[0].data = years.map(y => projections[y].vms);
        charts.forecast.data.datasets[1].data = years.map(y => projections[y].vcpus / 10);
        charts.forecast.data.datasets[2].data = years.map(y => projections[y].memory / 100);
        charts.forecast.update();
    }
    
    // Update infrastructure table
    // Build effective spec (handle custom)
    let effectiveSpec;
    if (nodeSpec === 'custom') {
        const customVcpus = parseInt(document.getElementById('custom-node-vcpus').value) || 128;
        const customRam = parseInt(document.getElementById('custom-node-ram').value) || 1024;
        effectiveSpec = { vcpus: customVcpus, memory: customRam };
    } else {
        effectiveSpec = nodeSpecs[nodeSpec];
    }
    updateInfrastructureTable(projections[2028], nodeSpec, effectiveSpec, overheadFactor);
}

function updateInfrastructureTable(projection2028, nodeSpec, spec, overheadFactor) {
    const specNames = {
        small: 'Small (64 vCPU / 512 GB)',
        medium: 'Medium (128 vCPU / 1024 GB)',
        large: 'Large (256 vCPU / 2048 GB)',
        custom: `Custom (${spec.vcpus} vCPU / ${spec.memory} GB)`
    };
    
    const clusters = forecastBaseData.clusters || [];
    const totalCurrent = forecastBaseData.current || {};
    
    let totalNodes = 0;
    let total2028Vms = 0;
    let total2028Vcpus = 0;
    let total2028Memory = 0;
    
    clusters.forEach(cluster => {
        const ratio = cluster.vms / totalCurrent.vms;
        const vms2028 = Math.ceil(projection2028.vms * ratio);
        const vcpus2028 = Math.ceil(projection2028.vcpus * ratio);
        const memory2028 = Math.ceil(projection2028.memory * ratio);
        
        // Calculate nodes needed (with overhead, minimum 3 for HA)
        const vcpuNodes = Math.ceil((vcpus2028 * overheadFactor) / spec.vcpus);
        const memoryNodes = Math.ceil((memory2028 * overheadFactor) / spec.memory);
        const nodes = Math.max(3, Math.max(vcpuNodes, memoryNodes));
        
        // Update row
        const row = document.querySelector(`tr[data-cluster="${cluster.name}"]`);
        if (row) {
            row.querySelector('.infra-2028-vms').textContent = vms2028.toLocaleString();
            row.querySelector('.infra-2028-vcpus').textContent = vcpus2028.toLocaleString();
            row.querySelector('.infra-2028-memory').textContent = memory2028.toLocaleString();
            row.querySelector('.infra-node-spec').textContent = specNames[nodeSpec] || 'Medium';
            row.querySelector('.infra-nodes').textContent = nodes;
        }
        
        totalNodes += nodes;
        total2028Vms += vms2028;
        total2028Vcpus += vcpus2028;
        total2028Memory += memory2028;
    });
    
    // Update totals
    const totalVmsEl = document.getElementById('infra-total-2028-vms');
    const totalVcpusEl = document.getElementById('infra-total-2028-vcpus');
    const totalMemoryEl = document.getElementById('infra-total-2028-memory');
    const totalNodesEl = document.getElementById('infra-total-nodes');
    
    if (totalVmsEl) totalVmsEl.textContent = total2028Vms.toLocaleString();
    if (totalVcpusEl) totalVcpusEl.textContent = total2028Vcpus.toLocaleString();
    if (totalMemoryEl) totalMemoryEl.textContent = total2028Memory.toLocaleString();
    if (totalNodesEl) totalNodesEl.textContent = totalNodes;
}

// ============================================
// UPDATE ALL CHARTS
// ============================================
function updateAllCharts() {
    updateOverviewCharts();
    updateSizingCharts();
    updateMigrationCharts();
    updateTrendsCharts();
}

// Helper function to count by property
function countBy(data, prop) {
    return data.reduce((acc, item) => {
        const key = item[prop] || 'Unknown';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});
}

// Helper function to sum by property
function sumBy(data, groupProp, sumProps) {
    return data.reduce((acc, item) => {
        const key = item[groupProp] || 'Unknown';
        if (!acc[key]) {
            acc[key] = {};
            sumProps.forEach(p => acc[key][p] = 0);
            acc[key].count = 0;
        }
        sumProps.forEach(p => acc[key][p] += (item[p] || 0));
        acc[key].count += 1;
        return acc;
    }, {});
}

function updateOverviewCharts() {
    // OS Family Pie Chart
    if (charts.osFamily) {
        const osFamilyCounts = countBy(filteredData, 'os_family');
        charts.osFamily.data.labels = Object.keys(osFamilyCounts);
        charts.osFamily.data.datasets[0].data = Object.values(osFamilyCounts);
        charts.osFamily.update();
    }
    
    // Size Categories Bar Chart
    if (charts.sizeCategories) {
        const sizeOrder = ['Small', 'Medium', 'Large', 'X-Large'];
        const sizeCounts = countBy(filteredData, 'size_category');
        charts.sizeCategories.data.labels = sizeOrder;
        charts.sizeCategories.data.datasets[0].data = sizeOrder.map(s => sizeCounts[s] || 0);
        charts.sizeCategories.update();
    }
    
    // Complexity Pie Chart
    if (charts.complexity) {
        const complexityOrder = ['Low', 'Medium', 'High'];
        const complexityCounts = countBy(filteredData, 'complexity');
        charts.complexity.data.labels = complexityOrder;
        charts.complexity.data.datasets[0].data = complexityOrder.map(c => complexityCounts[c] || 0);
        charts.complexity.update();
    }
    
    // Cluster Resources Bar Chart
    if (charts.clusterResources) {
        const clusterData = sumBy(filteredData, 'cluster', ['vcpus', 'memory_gb']);
        const clusterNames = Object.keys(clusterData);
        charts.clusterResources.data.labels = clusterNames;
        charts.clusterResources.data.datasets[0].data = clusterNames.map(c => clusterData[c].count);
        charts.clusterResources.data.datasets[1].data = clusterNames.map(c => clusterData[c].vcpus / 10);
        charts.clusterResources.data.datasets[2].data = clusterNames.map(c => clusterData[c].memory_gb / 100);
        charts.clusterResources.update();
    }
    
    // Host Resources Data Table
    updateHostResourceTable();
    
    // Guest OS Bar Chart
    if (charts.guestOs) {
        const osCounts = countBy(filteredData, 'os_consolidated');
        const labels = Object.keys(osCounts);
        const colors = labels.map(label => 
            label.toLowerCase().includes('windows') ? chartColors.blue : chartColors.red
        );
        charts.guestOs.data.labels = labels;
        charts.guestOs.data.datasets[0].data = Object.values(osCounts);
        charts.guestOs.data.datasets[0].backgroundColor = colors;
        charts.guestOs.update();
    }
}

function updateSizingCharts() {
    // Size Distribution Pie
    if (charts.sizePie) {
        const sizeOrder = ['Small', 'Medium', 'Large', 'X-Large'];
        const sizeCounts = countBy(filteredData, 'size_category');
        charts.sizePie.data.labels = sizeOrder;
        charts.sizePie.data.datasets[0].data = sizeOrder.map(s => sizeCounts[s] || 0);
        charts.sizePie.update();
    }
    
    // Resources by Size Bar Chart
    if (charts.resourcesBySize) {
        const sizeOrder = ['Small', 'Medium', 'Large', 'X-Large'];
        const sizeData = sumBy(filteredData, 'size_category', ['vcpus', 'memory_gb']);
        charts.resourcesBySize.data.labels = sizeOrder;
        charts.resourcesBySize.data.datasets[0].data = sizeOrder.map(s => (sizeData[s]?.vcpus || 0));
        charts.resourcesBySize.data.datasets[1].data = sizeOrder.map(s => (sizeData[s]?.memory_gb || 0));
        charts.resourcesBySize.update();
    }
}

function updateMigrationCharts() {
    // Complexity by OS Stacked Bar
    if (charts.complexityOs) {
        const osTypes = ['Linux', 'Windows'];
        const complexityData = {};
        
        osTypes.forEach(os => {
            const osVms = filteredData.filter(vm => vm.os_family === os);
            complexityData[os] = countBy(osVms, 'complexity');
        });
        
        charts.complexityOs.data.labels = osTypes;
        charts.complexityOs.data.datasets[0].data = osTypes.map(os => complexityData[os]?.Low || 0);
        charts.complexityOs.data.datasets[1].data = osTypes.map(os => complexityData[os]?.Medium || 0);
        charts.complexityOs.data.datasets[2].data = osTypes.map(os => complexityData[os]?.High || 0);
        charts.complexityOs.update();
    }
    
    // Migration Waves Bar Chart
    if (charts.migrationWaves) {
        const waveOrder = ['Wave 1 (Low)', 'Wave 2 (Medium)', 'Wave 3 (High)'];
        const complexityCounts = countBy(filteredData, 'complexity');
        const waveData = [
            complexityCounts['Low'] || 0,
            complexityCounts['Medium'] || 0,
            complexityCounts['High'] || 0
        ];
        charts.migrationWaves.data.labels = waveOrder;
        charts.migrationWaves.data.datasets[0].data = waveData;
        charts.migrationWaves.update();
    }
}

function updateTrendsCharts() {
    // For trends charts, we need creation dates - filter data that has dates
    const vmsWithDates = filteredData.filter(vm => vm.creation_date);
    
    if (vmsWithDates.length === 0) return;
    
    // Group by month for trends
    const monthlyData = {};
    vmsWithDates.forEach(vm => {
        const date = new Date(vm.creation_date);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (!monthlyData[monthKey]) {
            monthlyData[monthKey] = { count: 0, vcpus: 0, memory: 0 };
        }
        monthlyData[monthKey].count += 1;
        monthlyData[monthKey].vcpus += (vm.vcpus || 0);
        monthlyData[monthKey].memory += (vm.memory_gb || 0);
    });
    
    // Sort months
    const months = Object.keys(monthlyData).sort();
    
    // Calculate cumulative data
    let cumVms = 0, cumVcpus = 0, cumMemory = 0;
    const cumulative = months.map(m => {
        cumVms += monthlyData[m].count;
        cumVcpus += monthlyData[m].vcpus;
        cumMemory += monthlyData[m].memory;
        return { vms: cumVms, vcpus: cumVcpus, memory: cumMemory };
    });
    
    // VM Growth Line Chart
    if (charts.vmGrowth) {
        charts.vmGrowth.data.labels = months;
        charts.vmGrowth.data.datasets[0].data = cumulative.map(c => c.vms);
        charts.vmGrowth.update();
    }
    
    // Resource Growth Dual Axis
    if (charts.resourceGrowth) {
        charts.resourceGrowth.data.labels = months;
        charts.resourceGrowth.data.datasets[0].data = cumulative.map(c => c.vcpus);
        charts.resourceGrowth.data.datasets[1].data = cumulative.map(c => c.memory);
        charts.resourceGrowth.update();
    }
    
    // VMs Per Month Bar
    if (charts.vmsPerMonth) {
        charts.vmsPerMonth.data.labels = months;
        charts.vmsPerMonth.data.datasets[0].data = months.map(m => monthlyData[m].count);
        charts.vmsPerMonth.update();
    }
    
    // Resources Per Month Bar
    if (charts.resourcesPerMonth) {
        charts.resourcesPerMonth.data.labels = months;
        charts.resourcesPerMonth.data.datasets[0].data = months.map(m => monthlyData[m].vcpus);
        charts.resourcesPerMonth.data.datasets[1].data = months.map(m => monthlyData[m].memory / 10);
        charts.resourcesPerMonth.update();
    }
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    applyFilters();
});
"""


def build_data_prelude(data, chart_configs) -> str:
    """Render the data-injection prelude shown at the top of the <script> block.

    Produces 7 const declarations that expose vmData and the 6 chart-config blobs
    to the static JS in SCRIPT_BODY below.
    """
    vm_list_json = json.dumps(data.get('vm_list', []))
    overview_charts = json.dumps(chart_configs.get('overview', {}))
    sizing_charts = json.dumps(chart_configs.get('sizing', {}))
    migration_charts = json.dumps(chart_configs.get('migration', {}))
    trends_charts = json.dumps(chart_configs.get('trends', {}))
    forecast_data = json.dumps(chart_configs.get('forecast', {}))
    hosts_charts = json.dumps(chart_configs.get('hosts', {}))
    return f'''
// ============================================
// DATA
// ============================================
const vmData = {vm_list_json};
const overviewChartData = {overview_charts};
const sizingChartData = {sizing_charts};
const migrationChartData = {migration_charts};
const trendsChartData = {trends_charts};
const forecastBaseData = {forecast_data};
const hostsChartData = {hosts_charts};
'''


def generate_scripts(data, chart_configs) -> str:
    """Thin wrapper: data prelude + static JS body. Same external contract as
    before the Phase 2 refactor.
    """
    return build_data_prelude(data, chart_configs) + SCRIPT_BODY



def collect_chart_configs(data, tab_configs):
    """
    Collect all chart configurations from individual tab modules.
    
    Args:
        data: Processed data from data_processor
        tab_configs: Dict containing configs from each tab module
        
    Returns:
        Combined chart configurations dictionary
    """
    return {
        'overview': tab_configs.get('overview', {}),
        'sizing': tab_configs.get('sizing', {}),
        'migration': tab_configs.get('migration', {}),
        'trends': tab_configs.get('trends', {}),
        'forecast': tab_configs.get('forecast', {})
    }


# For testing
if __name__ == '__main__':
    mock_data = {
        'vm_list': [{'vm_name': 'VM-1', 'cluster': 'TEST'}],
        'stats': {'total_vms': 118, 'total_vcpus': 893, 'total_memory_gb': 2405}
    }
    
    mock_configs = {
        'overview': {'os_family': {'labels': ['Linux', 'Windows'], 'values': [59, 59]}},
        'sizing': {},
        'migration': {},
        'trends': {},
        'forecast': {'current': {'vms': 118, 'vcpus': 893, 'memory': 2405}, 'clusters': [], 'node_specs': {}}
    }
    
    js = generate_scripts(mock_data, mock_configs)
    print(f"JavaScript generated: {len(js)} characters ({len(js)/1024:.1f} KB)")
