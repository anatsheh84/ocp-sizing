# -*- coding: utf-8 -*-
"""
scripts.py
----------
Extracted <script> block for the OCP Sizing HTML report.

Phase 2 of the html_reporter.py refactor lifted this block out of the
parent f-string into a dedicated module. The block was ~571 lines with
exactly 5 data-interpolation points; those remain as parameters of
build_script_body() rather than globals so the function is pure and
testable.

Do NOT add new interpolation points here without updating the caller
in reporters/html_reporter.py to pass the new values through.
"""

import json


def build_script_body(nodes_json, sorted_ns, summary) -> str:
    """Return the entire <script>...</script> block, pre-rendered with data.

    Args:
        nodes_json:  list of node dicts (see prepare_report_data in
                     generate_report.py / inline build in html_reporter.py)
        sorted_ns:   list of (namespace, pod_count) tuples, descending
        summary:     ClusterSummary with total_capacity/requested/actual
                     and nodes_by_role

    Returns:
        HTML string starting with '    <script>' and ending with '    </script>'.
        No trailing newline (the caller's injection site supplies it).
    """
    return f'''    <script>
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab).classList.add('active');
            }});
        }});
        
        // Filter functionality - Enhanced with sum row and chart updates
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const tableId = btn.dataset.table;
                const filter = btn.dataset.filter;
                
                // Update active state for this filter group
                btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Filter table rows
                const table = document.getElementById(tableId);
                if (table) {{
                    const rows = table.querySelectorAll('tbody tr');
                    let visibleCount = 0;
                    
                    rows.forEach(row => {{
                        if (filter === 'all' || row.dataset.role === filter) {{
                            row.classList.remove('filtered-out');
                            visibleCount++;
                        }} else {{
                            row.classList.add('filtered-out');
                        }}
                    }});
                    
                    // Update count display
                    const countEl = document.getElementById(tableId + 'Count');
                    if (countEl) {{
                        countEl.textContent = visibleCount;
                    }}
                    
                    // Update sum row for nodesTable
                    if (tableId === 'nodesTable') {{
                        updateNodesTableSumRow(filter);
                    }}
                    
                    // Update efficiency tab cards and charts
                    if (tableId === 'efficiencyTable') {{
                        updateEfficiencyTabForFilter(filter);
                        updateEfficiencyTableSumRow(filter);
                    }}
                    
                    // Update workloads tab charts
                    if (tableId === 'workloadTable') {{
                        updateWorkloadsTabForFilter(filter);
                        updateWorkloadTableSumRow(filter);
                    }}
                }}
            }});
        }});
        
        // Function to update the nodes table sum row
        function updateNodesTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const count = filteredNodes.length;
            const cpuCores = filteredNodes.reduce((sum, n) => sum + n.cpu_capacity, 0);
            const cpuRequested = filteredNodes.reduce((sum, n) => sum + n.cpu_requested, 0);
            const cpuActual = filteredNodes.reduce((sum, n) => sum + n.cpu_actual, 0);
            const memCapacity = filteredNodes.reduce((sum, n) => sum + n.mem_capacity, 0);
            const memRequested = filteredNodes.reduce((sum, n) => sum + n.mem_requested, 0);
            const memActual = filteredNodes.reduce((sum, n) => sum + n.mem_actual, 0);
            const pods = filteredNodes.reduce((sum, n) => sum + n.pod_count, 0);
            
            document.getElementById('sumNodeCount').textContent = count + ' nodes';
            document.getElementById('sumCpuCores').textContent = cpuCores.toFixed(1);
            document.getElementById('sumCpuRequested').textContent = cpuRequested.toFixed(2);
            document.getElementById('sumCpuActual').textContent = cpuActual.toFixed(2);
            document.getElementById('sumMemCapacity').textContent = memCapacity.toFixed(1);
            document.getElementById('sumMemRequested').textContent = memRequested.toFixed(1);
            document.getElementById('sumMemActual').textContent = memActual.toFixed(1);
            document.getElementById('sumPods').textContent = pods;
        }}
        
        // Function to update Pods per Node sum row (#11)
        function updateWorkloadTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const podCount = filteredNodes.reduce((s, n) => s + n.pod_count, 0);
            const podCap = filteredNodes.reduce((s, n) => s + (n.pod_capacity || 0), 0);
            document.getElementById('sumWlNodeCount').textContent = filteredNodes.length + ' nodes';
            document.getElementById('sumWlPodCount').textContent = podCount;
            document.getElementById('sumWlPodCapacity').textContent = podCap;
        }}
        
        // Function to update Efficiency table sum row (#12)
        function updateEfficiencyTableSumRow(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const cpuReq = filteredNodes.reduce((s, n) => s + n.cpu_requested, 0);
            const cpuAct = filteredNodes.reduce((s, n) => s + n.cpu_actual, 0);
            const memReq = filteredNodes.reduce((s, n) => s + n.mem_requested, 0);
            const memAct = filteredNodes.reduce((s, n) => s + n.mem_actual, 0);
            document.getElementById('sumEffNodeCount').textContent = filteredNodes.length + ' nodes';
            document.getElementById('sumEffCpuReq').textContent = cpuReq.toFixed(2) + ' cores';
            document.getElementById('sumEffCpuActual').textContent = cpuAct.toFixed(2) + ' cores';
            document.getElementById('sumEffMemReq').textContent = memReq.toFixed(1) + ' GiB';
            document.getElementById('sumEffMemActual').textContent = memAct.toFixed(1) + ' GiB';
        }}
        
        // Function to update efficiency tab when filter changes
        function updateEfficiencyTabForFilter(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const filterLabel = filter === 'all' ? '' : ' (' + filter + ')';
            
            // Calculate totals for filtered nodes
            const totalCpuCapacity = filteredNodes.reduce((sum, n) => sum + n.cpu_capacity, 0);
            const totalCpuRequested = filteredNodes.reduce((sum, n) => sum + n.cpu_requested, 0);
            const totalCpuActual = filteredNodes.reduce((sum, n) => sum + n.cpu_actual, 0);
            const totalMemCapacity = filteredNodes.reduce((sum, n) => sum + n.mem_capacity, 0);
            const totalMemRequested = filteredNodes.reduce((sum, n) => sum + n.mem_requested, 0);
            const totalMemActual = filteredNodes.reduce((sum, n) => sum + n.mem_actual, 0);
            
            // CPU Request Accuracy Card
            const cpuReqAccuracy = totalCpuRequested > 0 ? Math.round(totalCpuActual / totalCpuRequested * 100) : 0;
            const cpuReqValueEl = document.getElementById('cpuRequestAccuracyValue');
            cpuReqValueEl.textContent = cpuReqAccuracy + '%';
            cpuReqValueEl.className = 'card-value ' + (cpuReqAccuracy <= 100 ? 'text-success' : 'text-danger');
            document.getElementById('cpuRequestAccuracySubtitle').textContent = cpuReqAccuracy <= 100 ? 'of requested CPU is being used' : 'of requested CPU is being used (over limit!)';
            document.getElementById('cpuRequestAccuracyDetail').textContent = totalCpuRequested.toFixed(1) + ' cores requested, ' + totalCpuActual.toFixed(1) + ' actually used';
            const cpuReqAdviceEl = document.getElementById('cpuRequestAccuracyAdvice');
            cpuReqAdviceEl.textContent = cpuReqAccuracy <= 100 ? '💡 Requests well-sized or over-provisioned' : '⚠️ Usage exceeds requests - set proper limits!';
            cpuReqAdviceEl.className = 'card-advice ' + (cpuReqAccuracy <= 100 ? 'advice-success' : 'advice-danger');
            
            // Memory Request Accuracy Card
            const memReqAccuracy = totalMemRequested > 0 ? Math.round(totalMemActual / totalMemRequested * 100) : 0;
            const memReqValueEl = document.getElementById('memRequestAccuracyValue');
            memReqValueEl.textContent = memReqAccuracy + '%';
            memReqValueEl.className = 'card-value ' + (memReqAccuracy <= 100 ? 'text-success' : 'text-danger');
            document.getElementById('memRequestAccuracySubtitle').textContent = memReqAccuracy <= 100 ? 'of requested memory is being used' : 'of requested memory is being used (over limit!)';
            document.getElementById('memRequestAccuracyDetail').textContent = totalMemRequested.toFixed(1) + ' GiB requested, ' + totalMemActual.toFixed(1) + ' GiB actually used';
            const memReqAdviceEl = document.getElementById('memRequestAccuracyAdvice');
            memReqAdviceEl.textContent = memReqAccuracy <= 100 ? '💡 Requests well-sized or over-provisioned' : '⚠️ Usage exceeds requests - set proper limits!';
            memReqAdviceEl.className = 'card-advice ' + (memReqAccuracy <= 100 ? 'advice-success' : 'advice-danger');
            
            // CPU Capacity Utilization Card
            const cpuCapUtil = totalCpuCapacity > 0 ? Math.round(totalCpuActual / totalCpuCapacity * 100) : 0;
            document.getElementById('cpuCapacityValue').textContent = cpuCapUtil + '%';
            document.getElementById('cpuCapacityDetail').textContent = totalCpuCapacity.toFixed(0) + ' cores capacity, ' + totalCpuActual.toFixed(1) + ' actually used';
            const cpuCapAdviceEl = document.getElementById('cpuCapacityAdvice');
            if (cpuCapUtil < 50) {{
                cpuCapAdviceEl.textContent = 'ℹ️ Low utilization - room to grow';
                cpuCapAdviceEl.className = 'card-advice advice-info';
            }} else if (cpuCapUtil < 80) {{
                cpuCapAdviceEl.textContent = '⚡ Moderate utilization';
                cpuCapAdviceEl.className = 'card-advice advice-warning';
            }} else {{
                cpuCapAdviceEl.textContent = '🔥 High utilization - consider scaling';
                cpuCapAdviceEl.className = 'card-advice advice-danger';
            }}
            
            // Memory Capacity Utilization Card
            const memCapUtil = totalMemCapacity > 0 ? Math.round(totalMemActual / totalMemCapacity * 100) : 0;
            document.getElementById('memCapacityValue').textContent = memCapUtil + '%';
            document.getElementById('memCapacityDetail').textContent = totalMemCapacity.toFixed(0) + ' GiB capacity, ' + totalMemActual.toFixed(1) + ' GiB actually used';
            const memCapAdviceEl = document.getElementById('memCapacityAdvice');
            if (memCapUtil < 50) {{
                memCapAdviceEl.textContent = 'ℹ️ Low utilization - room to grow';
                memCapAdviceEl.className = 'card-advice advice-info';
            }} else if (memCapUtil < 80) {{
                memCapAdviceEl.textContent = '⚡ Moderate utilization';
                memCapAdviceEl.className = 'card-advice advice-warning';
            }} else {{
                memCapAdviceEl.textContent = '🔥 High utilization - consider scaling';
                memCapAdviceEl.className = 'card-advice advice-danger';
            }}
            
            // Update filter indicators for all 4 cards
            const filterIndicatorIds = ['cpuRequestAccuracyFilter', 'memRequestAccuracyFilter', 'cpuCapacityFilter', 'memCapacityFilter'];
            filterIndicatorIds.forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    if (filter === 'all') {{
                        el.classList.add('hidden');
                    }} else {{
                        el.classList.remove('hidden');
                        el.innerHTML = 'Filtered: ' + filter + ' <span class="clear-filter" onclick="clearEfficiencyFilter()">✕</span>';
                    }}
                }}
            }});
            
            // Update chart titles
            document.getElementById('cpuChartTitle').textContent = 'CPU: Requested vs Actual per Node' + filterLabel;
            document.getElementById('memChartTitle').textContent = 'Memory: Requested vs Actual per Node' + filterLabel;
            
            // Update CPU Efficiency Chart
            cpuEfficiencyChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            cpuEfficiencyChart.data.datasets[0].data = filteredNodes.map(n => n.cpu_requested);
            cpuEfficiencyChart.data.datasets[1].data = filteredNodes.map(n => n.cpu_actual);
            cpuEfficiencyChart.update();
            
            // Update Memory Efficiency Chart
            memoryEfficiencyChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            memoryEfficiencyChart.data.datasets[0].data = filteredNodes.map(n => n.mem_requested);
            memoryEfficiencyChart.data.datasets[1].data = filteredNodes.map(n => n.mem_actual);
            memoryEfficiencyChart.update();
        }}
        
        // Function to clear efficiency filter
        function clearEfficiencyFilter() {{
            const allBtn = document.querySelector('#efficiency .filter-btn[data-filter="all"]');
            if (allBtn) allBtn.click();
        }}
        
        // Function to update workloads tab when filter changes
        function updateWorkloadsTabForFilter(filter) {{
            const filteredNodes = filter === 'all' ? nodesData : nodesData.filter(n => n.role === filter);
            const filterLabel = filter === 'all' ? '' : ' (' + filter + ')';
            
            // Calculate namespace data for filtered nodes only
            const filteredNsData = {{}};
            filteredNodes.forEach(node => {{
                // Find full node data to get pods
                const fullNode = nodesData.find(n => n.name === node.name);
                if (fullNode && fullNode.pods) {{
                    fullNode.pods.forEach(pod => {{
                        filteredNsData[pod.namespace] = (filteredNsData[pod.namespace] || 0) + 1;
                    }});
                }}
            }});
            
            // If we don't have pod details, use the pod_count as estimate
            if (Object.keys(filteredNsData).length === 0) {{
                // Fallback: just update the pods per node chart
            }}
            
            // Update Pods per Node chart
            document.getElementById('podsPerNodeChartTitle').textContent = 'Pods per Node' + filterLabel;
            podsPerNodeChart.data.labels = filteredNodes.map(n => n.name.split('.')[0]);
            podsPerNodeChart.data.datasets[0].data = filteredNodes.map(n => n.pod_count);
            podsPerNodeChart.update();
            
            // Update namespace chart title
            const nsCount = filter === 'all' ? Object.keys(namespaceData).length : Object.keys(filteredNsData).length;
            document.getElementById('namespaceChartTitle').textContent = 'Pods by Namespace (' + nsCount + ' namespaces)' + filterLabel;
            
            // For namespace chart, we need the full pod data which isn't in nodesData
            // So we'll show a message or keep the full data with a note
            if (filter !== 'all') {{
                // Update with filtered namespace data if available
                if (Object.keys(filteredNsData).length > 0) {{
                    const sortedFiltered = Object.entries(filteredNsData).sort((a, b) => b[1] - a[1]);
                    namespaceChart.data.labels = sortedFiltered.map(([k, v]) => k);
                    namespaceChart.data.datasets[0].data = sortedFiltered.map(([k, v]) => v);
                    namespaceChart.update();
                }}
            }} else {{
                // Reset to full namespace data
                namespaceChart.data.labels = Object.keys(namespaceData);
                namespaceChart.data.datasets[0].data = Object.values(namespaceData);
                namespaceChart.update();
            }}
        }}
        
        // Chart data
        const nodesData = {json.dumps(nodes_json)};
        const namespaceData = {json.dumps(dict(sorted_ns))};
        
        // Chart colors
        const colors = {{
            red: '#EE0000',
            blue: '#0066CC',
            green: '#3E8635',
            purple: '#6753AC',
            orange: '#F0AB00',
            cyan: '#009596',
            gray: '#6A6E73'
        }};
        
        // CPU Overview Chart (Capacity vs Requested vs Actual)
        new Chart(document.getElementById('cpuOverviewChart'), {{
            type: 'bar',
            data: {{
                labels: ['Capacity', 'Requested', 'Actual'],
                datasets: [{{
                    label: 'CPU (cores)',
                    data: [{round(summary.total_capacity.cpu / 1000, 1)}, {round(summary.total_requested.cpu / 1000, 1)}, {round(summary.total_actual.cpu / 1000, 1)}],
                    backgroundColor: [colors.gray, colors.blue, colors.green]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'Cores', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Memory Overview Chart (Capacity vs Requested vs Actual)
        new Chart(document.getElementById('memoryOverviewChart'), {{
            type: 'bar',
            data: {{
                labels: ['Capacity', 'Requested', 'Actual'],
                datasets: [{{
                    label: 'Memory (GiB)',
                    data: [{round(summary.total_capacity.memory / 1024, 1)}, {round(summary.total_requested.memory / 1024, 1)}, {round(summary.total_actual.memory / 1024, 1)}],
                    backgroundColor: [colors.gray, colors.blue, colors.green]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'GiB', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Nodes by Role Chart
        const roleData = {json.dumps(dict(summary.nodes_by_role))};
        new Chart(document.getElementById('nodesByRoleChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(roleData),
                datasets: [{{
                    data: Object.values(roleData),
                    backgroundColor: [colors.blue, colors.purple, colors.cyan, colors.orange, colors.gray]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // CPU Efficiency Chart - store as variable for updates
        const cpuEfficiencyChart = new Chart(document.getElementById('cpuEfficiencyChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [
                    {{
                        label: 'CPU Requested',
                        data: nodesData.map(n => n.cpu_requested),
                        backgroundColor: colors.blue
                    }},
                    {{
                        label: 'CPU Actual',
                        data: nodesData.map(n => n.cpu_actual),
                        backgroundColor: colors.green
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'Cores', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Memory Efficiency Chart - store as variable for updates
        const memoryEfficiencyChart = new Chart(document.getElementById('memoryEfficiencyChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [
                    {{
                        label: 'Memory Requested',
                        data: nodesData.map(n => n.mem_requested),
                        backgroundColor: colors.purple
                    }},
                    {{
                        label: 'Memory Actual',
                        data: nodesData.map(n => n.mem_actual),
                        backgroundColor: colors.green
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#B8BBBE' }}
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }},
                        title: {{ display: true, text: 'GiB', color: '#B8BBBE' }}
                    }}
                }}
            }}
        }});
        
        // Namespace Chart - Scrollable with ALL namespaces
        const nsLabels = Object.keys(namespaceData);
        const nsValues = Object.values(namespaceData);
        const chartHeight = Math.max(400, nsLabels.length * 25);
        
        const nsChartContainer = document.getElementById('namespaceChartContainer');
        const nsCanvas = document.getElementById('namespaceChart');
        nsCanvas.style.height = chartHeight + 'px';
        
        // Namespace Chart - store as variable for updates
        const namespaceChart = new Chart(nsCanvas, {{
            type: 'bar',
            data: {{
                labels: nsLabels,
                datasets: [{{
                    label: 'Pods',
                    data: nsValues,
                    backgroundColor: colors.cyan
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }}
                }}
            }}
        }});
        
        // Pods per Node Chart - store as variable for updates
        const podsPerNodeChart = new Chart(document.getElementById('podsPerNodeChart'), {{
            type: 'bar',
            data: {{
                labels: nodesData.map(n => n.name.split('.')[0]),
                datasets: [{{
                    label: 'Running Pods',
                    data: nodesData.map(n => n.pod_count),
                    backgroundColor: colors.orange
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#B8BBBE', maxRotation: 45 }},
                        grid: {{ color: '#3C3F42' }}
                    }},
                    y: {{
                        ticks: {{ color: '#B8BBBE' }},
                        grid: {{ color: '#3C3F42' }}
                    }}
                }}
            }}
        }});
        
        // Table functions
        function filterTable(tableId, searchText) {{
            const table = document.getElementById(tableId);
            const rows = table.getElementsByTagName('tr');
            searchText = searchText.toLowerCase();
            
            for (let i = 1; i < rows.length; i++) {{
                const cells = rows[i].getElementsByTagName('td');
                let found = false;
                for (let j = 0; j < cells.length; j++) {{
                    if (cells[j].textContent.toLowerCase().includes(searchText)) {{
                        found = true;
                        break;
                    }}
                }}
                rows[i].style.display = found ? '' : 'none';
            }}
        }}
        
        function sortTable(tableId, columnIndex) {{
            const table = document.getElementById(tableId);
            const rows = Array.from(table.rows).slice(1);
            const isNumeric = !isNaN(parseFloat(rows[0]?.cells[columnIndex]?.textContent));
            
            rows.sort((a, b) => {{
                let aVal = a.cells[columnIndex].textContent;
                let bVal = b.cells[columnIndex].textContent;
                
                if (isNumeric) {{
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                    return bVal - aVal;
                }}
                return aVal.localeCompare(bVal);
            }});
            
            rows.forEach(row => table.tBodies[0].appendChild(row));
        }}
        
        function exportTableToCSV(tableId, filename) {{
            const table = document.getElementById(tableId);
            let csv = [];
            
            for (let row of table.rows) {{
                let cols = [];
                for (let cell of row.cells) {{
                    cols.push('"' + cell.textContent.replace(/"/g, '""') + '"');
                }}
                csv.push(cols.join(','));
            }}
            
            const blob = new Blob([csv.join('\\n')], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
        }}
    </script>'''
