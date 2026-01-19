"""
html_reporter.py
---------------
HTML Report Generation for OCP Sizing Calculator.

Generates interactive Red Hat-branded HTML dashboard with:
- Architecture diagrams
- Resource utilization charts
- Node inventory tables  
- Efficiency analysis
- OCP migration recommendations
"""

import json
from datetime import datetime
from typing import List, Dict
from models import NodeData, ClusterSummary, PersistentVolume


def categorize_node_role(node: NodeData) -> str:
    """Determine node role from labels/taints"""
    if 'node-role.kubernetes.io/master' in node.labels or 'node-role.kubernetes.io/control-plane' in node.labels:
        return 'control-plane'
    if 'node-role.kubernetes.io/infra' in node.labels:
        return 'infra'
    if any('storage' in label.lower() for label in node.labels):
        return 'storage'
    return 'worker'


def generate_html_report(nodes: List[NodeData], summary: ClusterSummary, 
                        recommendations: Dict, pvs: List[PersistentVolume]) -> str:
    """Generate interactive HTML dashboard"""
    
    # Prepare data for charts
    nodes_json = []
    for node in nodes:
        role = categorize_node_role(node)
        cpu_req_pct = (node.allocated_requests.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_req_pct = (node.allocated_requests.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        cpu_actual_pct = (node.actual_usage.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_actual_pct = (node.actual_usage.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        
        nodes_json.append({
            'name': node.name,
            'role': role,
            'roles': ', '.join(node.roles),
            'cpu_capacity': round(node.capacity.cpu / 1000, 1),
            'cpu_allocatable': round(node.allocatable.cpu / 1000, 1),
            'cpu_requested': round(node.allocated_requests.cpu / 1000, 2),
            'cpu_actual': round(node.actual_usage.cpu / 1000, 2),
            'cpu_req_pct': round(cpu_req_pct, 1),
            'cpu_actual_pct': round(cpu_actual_pct, 1),
            'mem_capacity': round(node.capacity.memory / 1024, 1),
            'mem_allocatable': round(node.allocatable.memory / 1024, 1),
            'mem_requested': round(node.allocated_requests.memory / 1024, 1),
            'mem_actual': round(node.actual_usage.memory / 1024, 1),
            'mem_req_pct': round(mem_req_pct, 1),
            'mem_actual_pct': round(mem_actual_pct, 1),
            'pod_count': node.pod_count,
            'pod_capacity': node.capacity.pods,
            'is_ready': node.is_ready,
            'is_schedulable': node.is_schedulable,
            'taints': ', '.join(node.taints) if node.taints else 'None',
            'instance_type': node.instance_type or 'N/A',
            'ip_address': node.ip_address,
            'kubelet_version': node.system_info.kubelet_version,
            'os_image': node.system_info.os_image,
            'container_runtime': node.system_info.container_runtime,
            'pods': [{'namespace': p.namespace, 'name': p.name} for p in node.pods]
        })
    
    # Namespace pod distribution - ALL namespaces
    namespace_pods = {}
    for node in nodes:
        for pod in node.pods:
            ns = pod.namespace
            namespace_pods[ns] = namespace_pods.get(ns, 0) + 1
    
    # Sort by count (all namespaces)
    sorted_ns = sorted(namespace_pods.items(), key=lambda x: x[1], reverse=True)
    
    # PV data
    pvs_json = []
    for pv in pvs:
        pvs_json.append({
            'name': pv.name,
            'capacity': round(pv.capacity, 2),
            'access_modes': pv.access_modes,
            'reclaim_policy': pv.reclaim_policy,
            'status': pv.status,
            'claim': pv.claim or '-',
            'storage_class': pv.storage_class or '-'
        })
    
    # Group nodes by role for architecture diagram
    nodes_by_role = {}
    for node in nodes:
        role = categorize_node_role(node)
        if role not in nodes_by_role:
            nodes_by_role[role] = []
        nodes_by_role[role].append({
            'name': node.name.split('.')[0],
            'cpu': round(node.capacity.cpu / 1000, 0),
            'memory': round(node.capacity.memory / 1024, 0)
        })
    
    # Calculate role summaries for architecture diagram
    role_summaries = {}
    for role, role_nodes in nodes_by_role.items():
        if role_nodes:
            role_summaries[role] = {
                'count': len(role_nodes),
                'cpu': role_nodes[0]['cpu'],  # Assuming same specs
                'memory': role_nodes[0]['memory'],
                'nodes': role_nodes
            }
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCP Sizing Calculator - Assessment Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&family=Red+Hat+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --rh-red: #EE0000;
            --rh-red-dark: #A30000;
            --rh-red-light: #FF5C5C;
            --rh-black: #151515;
            --rh-gray-900: #212427;
            --rh-gray-800: #2D2D2D;
            --rh-gray-700: #3C3F42;
            --rh-gray-600: #4D5258;
            --rh-gray-500: #6A6E73;
            --rh-gray-400: #8A8D90;
            --rh-gray-300: #B8BBBE;
            --rh-gray-200: #D2D2D2;
            --rh-gray-100: #F0F0F0;
            --rh-white: #FFFFFF;
            --rh-blue: #0066CC;
            --rh-blue-light: #73BCF7;
            --rh-green: #3E8635;
            --rh-green-light: #95D58F;
            --rh-orange: #F0AB00;
            --rh-purple: #6753AC;
            --rh-cyan: #009596;
            
            --bg-primary: var(--rh-gray-900);
            --bg-secondary: var(--rh-gray-800);
            --bg-tertiary: var(--rh-gray-700);
            --text-primary: var(--rh-white);
            --text-secondary: var(--rh-gray-300);
            --text-muted: var(--rh-gray-400);
            --border-color: var(--rh-gray-600);
            --accent: var(--rh-red);
            --accent-hover: var(--rh-red-dark);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--rh-black) 0%, var(--rh-gray-900) 100%);
            border-bottom: 3px solid var(--rh-red);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .header-content {{
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .logo {{
            width: 50px;
            height: 50px;
            background: var(--rh-red);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .logo svg {{
            width: 30px;
            height: 30px;
            fill: white;
        }}
        
        .title-section h1 {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .title-section p {{
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        
        .header-meta {{
            text-align: right;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        
        /* Navigation Tabs */
        .nav-tabs {{
            background: var(--bg-secondary);
            padding: 0 2rem;
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        
        .nav-tabs-inner {{
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            gap: 0;
        }}
        
        .nav-tab {{
            padding: 1rem 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
            font-weight: 500;
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap;
            font-size: 0.9rem;
        }}
        
        .nav-tab:hover {{
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }}
        
        .nav-tab.active {{
            color: var(--rh-red);
            border-bottom-color: var(--rh-red);
        }}
        
        /* Main Content */
        .main-content {{
            max-width: 1800px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Filter Bar */
        .filter-bar {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
        }}
        
        .filter-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .filter-btn:hover {{
            background: var(--rh-gray-600);
            color: var(--text-primary);
        }}
        
        .filter-btn.active {{
            background: var(--rh-red);
            border-color: var(--rh-red);
            color: white;
        }}
        
        .filter-btn.active.control-plane {{ background: var(--rh-blue); border-color: var(--rh-blue); }}
        .filter-btn.active.infra {{ background: var(--rh-purple); border-color: var(--rh-purple); }}
        .filter-btn.active.storage {{ background: var(--rh-cyan); border-color: var(--rh-cyan); }}
        .filter-btn.active.worker {{ background: var(--rh-orange); border-color: var(--rh-orange); }}
        
        .filter-count {{
            background: rgba(255,255,255,0.2);
            padding: 0.1rem 0.5rem;
            border-radius: 100px;
            font-size: 0.7rem;
        }}
        
        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .summary-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        
        .summary-card.highlight {{
            border-color: var(--rh-red);
            background: linear-gradient(135deg, var(--bg-secondary) 0%, rgba(238,0,0,0.1) 100%);
        }}
        
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }}
        
        .card-title {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .card-icon {{
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }}
        
        .card-icon.nodes {{ background: rgba(0,102,204,0.2); color: var(--rh-blue); }}
        .card-icon.cpu {{ background: rgba(62,134,53,0.2); color: var(--rh-green); }}
        .card-icon.memory {{ background: rgba(103,83,172,0.2); color: var(--rh-purple); }}
        .card-icon.pods {{ background: rgba(240,171,0,0.2); color: var(--rh-orange); }}
        .card-icon.storage {{ background: rgba(0,149,150,0.2); color: var(--rh-cyan); }}
        .card-icon.efficiency {{ background: rgba(238,0,0,0.2); color: var(--rh-red); }}
        
        .card-value {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }}
        
        .card-subtitle {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}
        
        .card-detail {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border-color);
        }}
        
        /* Architecture Diagram */
        .architecture-diagram {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }}
        
        .architecture-title {{
            text-align: center;
            margin-bottom: 1.5rem;
        }}
        
        .architecture-title h3 {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            margin-bottom: 0.25rem;
        }}
        
        .architecture-title p {{
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        .architecture-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
        }}
        
        .arch-tier {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }}
        
        .arch-tier-label {{
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        
        .arch-tier-nodes {{
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .arch-connector {{
            width: 2px;
            height: 25px;
            background: linear-gradient(180deg, var(--rh-gray-600) 0%, var(--rh-gray-600) 50%, transparent 50%, transparent 100%);
            background-size: 2px 8px;
        }}
        
        .arch-connector-h {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 70%;
            height: 25px;
            position: relative;
        }}
        
        .arch-connector-h::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 15%;
            right: 15%;
            height: 2px;
            background: var(--rh-gray-600);
        }}
        
        .arch-connector-h::after {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 2px;
            height: 12px;
            background: var(--rh-gray-600);
        }}
        
        .arch-node-group {{
            background: var(--rh-gray-700);
            border-radius: 10px;
            padding: 1rem 1.5rem;
            text-align: center;
            border: 2px solid transparent;
            transition: all 0.2s;
            min-width: 130px;
        }}
        
        .arch-node-group:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }}
        
        .arch-node-group.control-plane {{
            border-color: var(--rh-blue);
            background: linear-gradient(135deg, rgba(0,102,204,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.infra {{
            border-color: var(--rh-purple);
            background: linear-gradient(135deg, rgba(103,83,172,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.storage {{
            border-color: var(--rh-cyan);
            background: linear-gradient(135deg, rgba(0,149,150,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group.worker {{
            border-color: var(--rh-orange);
            background: linear-gradient(135deg, rgba(240,171,0,0.2) 0%, var(--rh-gray-700) 100%);
        }}
        
        .arch-node-group .icon {{
            font-size: 1.75rem;
            margin-bottom: 0.25rem;
        }}
        
        .arch-node-group .role {{
            font-family: 'Red Hat Display', sans-serif;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        
        .arch-node-group .count {{
            font-size: 1.75rem;
            font-weight: 700;
            font-family: 'Red Hat Display', sans-serif;
        }}
        
        .arch-node-group.control-plane .count {{ color: var(--rh-blue); }}
        .arch-node-group.infra .count {{ color: var(--rh-purple); }}
        .arch-node-group.storage .count {{ color: var(--rh-cyan); }}
        .arch-node-group.worker .count {{ color: var(--rh-orange); }}
        
        .arch-node-group .specs {{
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        
        .arch-node-group .node-names {{
            font-size: 0.65rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--rh-gray-600);
            max-width: 150px;
            word-wrap: break-word;
        }}
        
        .arch-middle-tier {{
            display: flex;
            justify-content: center;
            gap: 2rem;
        }}
        
        .arch-legend {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid var(--rh-gray-700);
            flex-wrap: wrap;
        }}
        
        .arch-legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .arch-legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 4px;
        }}
        
        .arch-legend-color.cp {{ background: var(--rh-blue); }}
        .arch-legend-color.infra {{ background: var(--rh-purple); }}
        .arch-legend-color.storage {{ background: var(--rh-cyan); }}
        .arch-legend-color.worker {{ background: var(--rh-orange); }}
        
        /* Charts Section */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .chart-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .chart-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        .chart-container.scrollable {{
            height: auto;
            max-height: 500px;
            overflow-y: auto;
        }}
        
        .chart-container.scrollable canvas {{
            min-height: 400px;
        }}
        
        /* Tables */
        .table-container {{
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}
        
        .table-header {{
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .table-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        
        .table-search {{
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 0.875rem;
            width: 250px;
        }}
        
        .table-search:focus {{
            outline: none;
            border-color: var(--rh-blue);
        }}
        
        .table-scroll {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}
        
        th {{
            background: var(--bg-tertiary);
            padding: 0.875rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
            white-space: nowrap;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        th:hover {{
            background: var(--rh-gray-600);
        }}
        
        td {{
            padding: 0.875rem 1rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-primary);
            white-space: nowrap;
        }}
        
        tr:hover td {{
            background: var(--bg-tertiary);
        }}
        
        tr.filtered-out {{
            display: none;
        }}
        
        /* Status badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        
        .badge-success {{ background: rgba(62,134,53,0.2); color: var(--rh-green-light); }}
        .badge-warning {{ background: rgba(240,171,0,0.2); color: var(--rh-orange); }}
        .badge-danger {{ background: rgba(238,0,0,0.2); color: var(--rh-red-light); }}
        .badge-info {{ background: rgba(0,102,204,0.2); color: var(--rh-blue-light); }}
        .badge-neutral {{ background: var(--bg-tertiary); color: var(--text-secondary); }}
        
        /* Card value colors */
        .text-success {{ color: var(--rh-green-light) !important; }}
        .text-danger {{ color: var(--rh-red-light) !important; }}
        .text-warning {{ color: var(--rh-orange) !important; }}
        .text-info {{ color: var(--rh-blue-light) !important; }}
        
        /* Card advice styles */
        .card-advice {{
            font-size: 0.8rem;
            margin-top: 0.75rem;
            padding: 0.5rem;
            border-radius: 4px;
        }}
        
        .advice-success {{
            background: rgba(62,134,53,0.15);
            color: var(--rh-green-light);
        }}
        
        .advice-danger {{
            background: rgba(238,0,0,0.15);
            color: var(--rh-red-light);
        }}
        
        .advice-warning {{
            background: rgba(240,171,0,0.15);
            color: var(--rh-orange);
        }}
        
        .advice-info {{
            background: rgba(0,102,204,0.15);
            color: var(--rh-blue-light);
        }}
        
        /* Role badges */
        .role-badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-right: 0.25rem;
            text-transform: uppercase;
        }}
        
        .role-control-plane {{ background: var(--rh-blue); color: white; }}
        .role-infra {{ background: var(--rh-purple); color: white; }}
        .role-storage {{ background: var(--rh-cyan); color: white; }}
        .role-worker {{ background: var(--rh-gray-600); color: white; }}
        
        /* Sticky sum footer row */
        tfoot {{
            position: sticky;
            bottom: 0;
            z-index: 10;
        }}
        
        tfoot tr {{
            background: var(--rh-gray-700) !important;
            border-top: 2px solid var(--rh-red);
        }}
        
        tfoot td {{
            padding: 1rem;
            font-weight: 700;
            color: var(--rh-white);
            background: var(--rh-gray-700);
        }}
        
        tfoot td:first-child {{
            color: var(--rh-orange);
        }}
        
        .table-scroll {{
            max-height: 600px;
            overflow-y: auto;
        }}
        
        /* Filter indicator badge */
        .filter-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--rh-gray-700);
            border-radius: 6px;
            font-size: 0.85rem;
            color: var(--rh-orange);
            margin-left: 1rem;
        }}
        
        .filter-indicator.hidden {{
            display: none;
        }}
        
        .filter-indicator .clear-filter {{
            cursor: pointer;
            color: var(--rh-gray-400);
            transition: color 0.2s;
        }}
        
        .filter-indicator .clear-filter:hover {{
            color: var(--rh-red);
        }}
        
        /* Progress bars */
        .progress-bar {{
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.25rem;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .progress-low {{ background: var(--rh-green); }}
        .progress-medium {{ background: var(--rh-orange); }}
        .progress-high {{ background: var(--rh-red); }}
        
        /* Recommendations Section */
        .recommendations-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }}
        
        .rec-card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .rec-card-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .rec-icon {{
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }}
        
        .rec-card-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        .rec-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1rem;
        }}
        
        .rec-column {{
            text-align: center;
        }}
        
        .rec-column-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        
        .rec-column-value {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .rec-column-detail {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .rec-notes {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }}
        
        .rec-note {{
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .rec-note-icon {{
            color: var(--rh-orange);
        }}
        
        /* Warnings & Opportunities */
        .warnings-section {{
            background: rgba(238,0,0,0.1);
            border: 1px solid var(--rh-red);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }}
        
        .warnings-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-red-light);
            margin-bottom: 1rem;
        }}
        
        .warning-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        
        .warning-icon {{
            color: var(--rh-orange);
            font-size: 1.25rem;
        }}
        
        .opportunities-section {{
            background: rgba(62,134,53,0.1);
            border: 1px solid var(--rh-green);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1.5rem;
        }}
        
        .opportunities-title {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-green-light);
            margin-bottom: 1rem;
        }}
        
        .opportunity-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }}
        
        /* Checklist */
        .checklist {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }}
        
        .checklist-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .checklist-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .checklist-item:last-child {{
            border-bottom: none;
        }}
        
        .check-icon {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.875rem;
        }}
        
        .check-icon.pass {{ background: var(--rh-green); color: white; }}
        .check-icon.warn {{ background: var(--rh-orange); color: white; }}
        .check-icon.fail {{ background: var(--rh-red); color: white; }}
        .check-icon.info {{ background: var(--rh-blue); color: white; }}
        
        .check-text {{
            flex: 1;
        }}
        
        .check-label {{
            font-weight: 500;
        }}
        
        .check-detail {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        
        /* Section headers */
        .section-header {{
            margin-bottom: 1.5rem;
        }}
        
        .section-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .section-subtitle {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        /* No Data Available */
        .no-data {{
            text-align: center;
            padding: 4rem 2rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }}
        
        .no-data-icon {{
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }}
        
        .no-data-title {{
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }}
        
        .no-data-text {{
            color: var(--text-muted);
            font-size: 0.95rem;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 3rem;
            padding: 2rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }}
        
        /* Export buttons */
        .export-buttons {{
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }}
        
        .btn {{
            padding: 0.625rem 1.25rem;
            border-radius: 6px;
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .btn-primary {{
            background: var(--rh-red);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: var(--rh-red-dark);
        }}
        
        .btn-secondary {{
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }}
        
        .btn-secondary:hover {{
            background: var(--rh-gray-600);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }}
            
            .header-meta {{
                text-align: center;
            }}
            
            .nav-tabs {{
                padding: 0 1rem;
            }}
            
            .nav-tab {{
                padding: 0.75rem 1rem;
                font-size: 0.8rem;
            }}
            
            .main-content {{
                padding: 1rem;
            }}
            
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            
            .filter-bar {{
                flex-direction: column;
                align-items: flex-start;
            }}
        }}
        
        /* Print-Optimized Styles */
        @media print {{
            /* Hide interactive elements */
            .nav-tabs,
            .filter-bar,
            .export-btn {{
                display: none !important;
            }}
            
            /* Show all tab content for PDF */
            .tab-content {{
                display: block !important;
                page-break-before: always;
            }}
            
            /* First tab shouldn't have page break */
            .tab-content:first-of-type {{
                page-break-before: auto;
            }}
            
            /* Compact spacing for print */
            body {{
                font-size: 10pt;
                line-height: 1.3;
                background: white !important;
            }}
            
            .container {{
                max-width: none;
                padding: 0;
            }}
            
            .main-content {{
                padding: 0.5rem;
            }}
            
            /* Reduce card padding */
            .summary-card {{
                padding: 0.75rem;
                margin-bottom: 0.5rem;
                page-break-inside: avoid;
            }}
            
            /* Compact headers */
            .section-title {{
                font-size: 14pt;
                margin-top: 0.5rem;
                margin-bottom: 0.5rem;
                page-break-after: avoid;
            }}
            
            .section-subtitle {{
                font-size: 9pt;
                margin-bottom: 0.75rem;
            }}
            
            /* Compact summary grid */
            .summary-grid {{
                grid-template-columns: repeat(4, 1fr);
                gap: 0.75rem;
                margin-bottom: 1rem;
            }}
            
            /* Smaller card values */
            .card-value {{
                font-size: 20pt;
            }}
            
            .card-subtitle {{
                font-size: 8pt;
            }}
            
            /* Keep charts with their containers */
            .charts-grid {{
                page-break-inside: avoid;
                gap: 1rem;
                margin-bottom: 1rem;
            }}
            
            .chart-container {{
                page-break-inside: avoid;
                padding: 0.75rem;
                margin-bottom: 0.5rem;
            }}
            
            /* Compact chart titles */
            .chart-title {{
                font-size: 10pt;
                margin-bottom: 0.5rem;
            }}
            
            /* Table optimizations */
            .table-container {{
                page-break-inside: avoid;
                margin-bottom: 1rem;
            }}
            
            table {{
                font-size: 8pt;
                page-break-inside: auto;
            }}
            
            thead {{
                display: table-header-group;
            }}
            
            tr {{
                page-break-inside: avoid;
                page-break-after: auto;
            }}
            
            th {{
                padding: 0.4rem 0.6rem;
            }}
            
            td {{
                padding: 0.4rem 0.6rem;
            }}
            
            /* Compact architecture diagram */
            .architecture-diagram {{
                page-break-inside: avoid;
                padding: 1rem;
                margin-bottom: 1rem;
            }}
            
            .node-box {{
                padding: 0.75rem;
            }}
            
            /* Compact recommendation cards */
            .recommendation-card {{
                padding: 0.75rem;
                margin-bottom: 0.75rem;
                page-break-inside: avoid;
            }}
            
            /* Compact metrics */
            .metric-group {{
                margin-bottom: 0.75rem;
            }}
            
            .metric-card {{
                padding: 0.75rem;
            }}
            
            /* Checklist items */
            .checklist-item {{
                padding: 0.5rem 0;
                page-break-inside: avoid;
            }}
            
            /* Reduce vertical spacing */
            .stats-card {{
                padding: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            
            /* Hide hover effects */
            *:hover {{
                transform: none !important;
                box-shadow: none !important;
            }}
            
            /* Ensure backgrounds print */
            * {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            
            /* Page break controls */
            .page-break-before {{
                page-break-before: always;
            }}
            
            .page-break-after {{
                page-break-after: always;
            }}
            
            .no-page-break {{
                page-break-inside: avoid;
            }}
            
            /* Footer compact */
            .footer {{
                font-size: 7pt;
                padding: 0.5rem;
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div class="title-section">
                    <h1>OCP Sizing Calculator</h1>
                    <p>Kubernetes to OpenShift Migration Assessment</p>
                </div>
            </div>
            <div class="header-meta">
                <div>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                <div>{summary.total_nodes} nodes analyzed</div>
            </div>
        </div>
    </header>
    
    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <div class="nav-tab active" data-tab="overview">Overview</div>
            <div class="nav-tab" data-tab="nodes">Node Inventory</div>
            <div class="nav-tab" data-tab="efficiency">Efficiency Analysis</div>
            <div class="nav-tab" data-tab="workloads">Workload Distribution</div>
            <div class="nav-tab" data-tab="recommendations">OCP Recommendations</div>
            <div class="nav-tab" data-tab="checklist">Migration Checklist</div>
            <div class="nav-tab" data-tab="storage">Persistent Volumes</div>
        </div>
    </nav>
    
    <main class="main-content">
        <!-- Overview Tab -->
        <div class="tab-content active" id="overview">
            <div class="section-header">
                <h2 class="section-title">Cluster Overview</h2>
                <p class="section-subtitle">Summary of your Kubernetes cluster resources and utilization</p>
            </div>
            
            <!-- Architecture Diagram -->
            <div class="architecture-diagram">
                <div class="architecture-title">
                    <h3>🏗️ Cluster Architecture</h3>
                    <p>Kubernetes Cluster • {summary.total_nodes} Nodes • {summary.provider or 'Unknown Platform'}</p>
                </div>
                
                <div class="architecture-container">
                    {'<!-- Control Plane Tier -->' if 'control-plane' in role_summaries else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Control Plane Tier</div>
                        <div class="arch-tier-nodes">
                            <div class="arch-node-group control-plane">
                                <div class="icon">🎛️</div>
                                <div class="role">Control Plane</div>
                                <div class="count">{role_summaries.get('control-plane', {'count': 0}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('control-plane', {'cpu': 0}).get('cpu', 0):.0f} vCPU × {role_summaries.get('control-plane', {'memory': 0}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">{', '.join([n['name'] for n in role_summaries.get('control-plane', {'nodes': []}).get('nodes', [])[:3]])}{' +more' if len(role_summaries.get('control-plane', {'nodes': []}).get('nodes', [])) > 3 else ''}</div>
                            </div>
                        </div>
                    </div>
                    ''' if 'control-plane' in role_summaries else ''}
                    
                    {f'<div class="arch-connector-h"></div>' if ('control-plane' in role_summaries and ('infra' in role_summaries or 'storage' in role_summaries)) else ''}
                    
                    {'<!-- Platform Services Tier -->' if ('infra' in role_summaries or 'storage' in role_summaries) else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Platform Services Tier</div>
                        <div class="arch-middle-tier">
                            {f"""
                            <div class="arch-node-group infra">
                                <div class="icon">🔧</div>
                                <div class="role">Infrastructure</div>
                                <div class="count">{role_summaries.get('infra', {}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('infra', {}).get('cpu', 0):.0f} vCPU × {role_summaries.get('infra', {}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">Logging, Monitoring, Router</div>
                            </div>
                            """ if 'infra' in role_summaries else ''}
                            
                            {f"""
                            <div class="arch-node-group storage">
                                <div class="icon">💾</div>
                                <div class="role">Storage (ODF)</div>
                                <div class="count">{role_summaries.get('storage', {}).get('count', 0)}</div>
                                <div class="specs">{role_summaries.get('storage', {}).get('cpu', 0):.0f} vCPU × {role_summaries.get('storage', {}).get('memory', 0):.0f} GiB</div>
                                <div class="node-names">Ceph MON, MDS, OSD</div>
                            </div>
                            """ if 'storage' in role_summaries else ''}
                        </div>
                    </div>
                    ''' if ('infra' in role_summaries or 'storage' in role_summaries) else ''}
                    
                    {f'<div class="arch-connector-h"></div>' if 'worker' in role_summaries and ('infra' in role_summaries or 'storage' in role_summaries or 'control-plane' in role_summaries) else ''}
                    
                    {'<!-- Worker Tier -->' if 'worker' in role_summaries else ''}
                    {f'''
                    <div class="arch-tier">
                        <div class="arch-tier-label">Application Workload Tier</div>
                        <div class="arch-tier-nodes">
                            <div class="arch-node-group worker">
                                <div class="icon">⚙️</div>
                                <div class="role">Workers</div>
                                <div class="count">{role_summaries.get('worker', {'count': 0}).get('count', 0)}</div>
                                <div class="specs">Application Workloads</div>
                                <div class="node-names">{', '.join([n['name'] for n in role_summaries.get('worker', {'nodes': []}).get('nodes', [])[:4]])}{f" +{len(role_summaries.get('worker', {'nodes': []}).get('nodes', [])) - 4} more" if len(role_summaries.get('worker', {'nodes': []}).get('nodes', [])) > 4 else ''}</div>
                            </div>
                        </div>
                    </div>
                    ''' if 'worker' in role_summaries else ''}
                </div>
                
                <div class="arch-legend">
                    {'<div class="arch-legend-item"><div class="arch-legend-color cp"></div><span>Control Plane (' + str(role_summaries.get("control-plane", {}).get("count", 0)) + ')</span></div>' if 'control-plane' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color infra"></div><span>Infrastructure (' + str(role_summaries.get("infra", {}).get("count", 0)) + ')</span></div>' if 'infra' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color storage"></div><span>Storage (' + str(role_summaries.get("storage", {}).get("count", 0)) + ')</span></div>' if 'storage' in role_summaries else ''}
                    {'<div class="arch-legend-item"><div class="arch-legend-color worker"></div><span>Workers (' + str(role_summaries.get("worker", {}).get("count", 0)) + ')</span></div>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total Nodes</span>
                        <div class="card-icon nodes">🖥️</div>
                    </div>
                    <div class="card-value">{summary.total_nodes}</div>
                    <div class="card-subtitle">
                        {', '.join([f"{v} {k}" for k, v in sorted(summary.nodes_by_role.items())])}
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">CPU Capacity</span>
                        <div class="card-icon cpu">⚡</div>
                    </div>
                    <div class="card-value">{round(summary.total_capacity.cpu / 1000, 0):.0f}</div>
                    <div class="card-subtitle">vCPU cores total</div>
                    <div class="card-detail">
                        {round(summary.total_allocatable.cpu / 1000, 0):.0f} allocatable
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Memory Capacity</span>
                        <div class="card-icon memory">🧠</div>
                    </div>
                    <div class="card-value">{round(summary.total_capacity.memory / 1024, 0):.0f}</div>
                    <div class="card-subtitle">GiB total</div>
                    <div class="card-detail">
                        {round(summary.total_allocatable.memory / 1024, 0):.0f} GiB allocatable
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Running Pods</span>
                        <div class="card-icon pods">📦</div>
                    </div>
                    <div class="card-value">{summary.total_pods}</div>
                    <div class="card-subtitle">across {len(summary.namespaces)} namespaces</div>
                    <div class="card-detail">
                        Capacity: {summary.total_capacity.pods} pods
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Platform</span>
                        <div class="card-icon storage">☁️</div>
                    </div>
                    <div class="card-value" style="font-size: 1.5rem;">{summary.provider or 'Unknown'}</div>
                    <div class="card-subtitle">{summary.kubernetes_version}</div>
                    <div class="card-detail">
                        {summary.container_runtime.split('://')[0] if summary.container_runtime else 'N/A'}
                    </div>
                </div>
            </div>
            
            <div class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">CPU: Capacity vs Requested vs Actual</h3>
                    <div class="chart-container">
                        <canvas id="cpuOverviewChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Memory: Capacity vs Requested vs Actual</h3>
                    <div class="chart-container">
                        <canvas id="memoryOverviewChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title">Nodes by Role</h3>
                    <div class="chart-container">
                        <canvas id="nodesByRoleChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Nodes Tab -->
        <div class="tab-content" id="nodes">
            <div class="section-header">
                <h2 class="section-title">Node Inventory</h2>
                <p class="section-subtitle">Detailed view of all cluster nodes with resource allocation</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="nodesTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="nodesTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="nodesTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="nodesTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="nodesTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="export-buttons">
                <button class="btn btn-primary" onclick="exportTableToCSV('nodesTable', 'nodes_inventory.csv')">
                    📥 Export CSV
                </button>
            </div>
            
            <div class="table-container">
                <div class="table-header">
                    <input type="text" class="table-search" placeholder="Search nodes..." onkeyup="filterTable('nodesTable', this.value)">
                </div>
                <div class="table-scroll">
                    <table id="nodesTable">
                        <thead>
                            <tr>
                                <th onclick="sortTable('nodesTable', 0)">Node Name</th>
                                <th onclick="sortTable('nodesTable', 1)">Role</th>
                                <th onclick="sortTable('nodesTable', 2)">CPU Capacity (cores)</th>
                                <th onclick="sortTable('nodesTable', 3)">CPU Requested</th>
                                <th onclick="sortTable('nodesTable', 4)">CPU Used</th>
                                <th onclick="sortTable('nodesTable', 5)">Memory Capacity (GiB)</th>
                                <th onclick="sortTable('nodesTable', 6)">Mem Requested</th>
                                <th onclick="sortTable('nodesTable', 7)">Memory Used</th>
                                <th onclick="sortTable('nodesTable', 8)">Pods</th>
                                <th onclick="sortTable('nodesTable', 9)">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name']}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['cpu_capacity']}</td>
                                <td>
                                    <div>{n['cpu_requested']} ({n['cpu_req_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill {'progress-high' if n['cpu_req_pct'] > 80 else 'progress-medium' if n['cpu_req_pct'] > 50 else 'progress-low'}" style="width: {min(n['cpu_req_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>
                                    <div>{n['cpu_actual']} ({n['cpu_actual_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['cpu_actual_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>{n['mem_capacity']}</td>
                                <td>
                                    <div>{n['mem_requested']} ({n['mem_req_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill {'progress-high' if n['mem_req_pct'] > 80 else 'progress-medium' if n['mem_req_pct'] > 50 else 'progress-low'}" style="width: {min(n['mem_req_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>
                                    <div>{n['mem_actual']} ({n['mem_actual_pct']}%)</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['mem_actual_pct'], 100)}%"></div>
                                    </div>
                                </td>
                                <td>{n['pod_count']}/{n['pod_capacity']}</td>
                                <td><span class="badge {'badge-success' if n['is_ready'] else 'badge-danger'}">{'Ready' if n['is_ready'] else 'Not Ready'}</span></td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                        <tfoot>
                            <tr id="nodesTableSumRow">
                                <td>Σ Total (Filtered)</td>
                                <td id="sumNodeCount">{len(nodes)} nodes</td>
                                <td id="sumCpuCores">{sum(n['cpu_capacity'] for n in nodes_json):.1f}</td>
                                <td id="sumCpuRequested">{sum(n['cpu_requested'] for n in nodes_json):.2f}</td>
                                <td id="sumCpuActual">{sum(n['cpu_actual'] for n in nodes_json):.2f}</td>
                                <td id="sumMemCapacity">{sum(n['mem_capacity'] for n in nodes_json):.1f}</td>
                                <td id="sumMemRequested">{sum(n['mem_requested'] for n in nodes_json):.1f}</td>
                                <td id="sumMemActual">{sum(n['mem_actual'] for n in nodes_json):.1f}</td>
                                <td id="sumPods">{sum(n['pod_count'] for n in nodes_json)}</td>
                                <td>-</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Efficiency Tab -->
        <div class="tab-content" id="efficiency">
            <div class="section-header">
                <h2 class="section-title">Efficiency Analysis</h2>
                <p class="section-subtitle">Compare requested resources against actual utilization to identify optimization opportunities</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="efficiencyTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="efficiencyTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="efficiencyTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="efficiencyTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="efficiencyTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="summary-grid" id="efficiencyCards">
                <div class="summary-card" id="cpuRequestAccuracyCard">
                    <div class="card-header">
                        <span class="card-title">CPU Request Accuracy</span>
                        <div class="card-icon cpu">📊</div>
                    </div>
                    <div class="card-value {'text-success' if summary.total_actual.cpu <= summary.total_requested.cpu else 'text-danger'}" id="cpuRequestAccuracyValue">{round(summary.total_actual.cpu / max(summary.total_requested.cpu, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle" id="cpuRequestAccuracySubtitle">{'of requested CPU is being used' if summary.total_actual.cpu <= summary.total_requested.cpu else 'of requested CPU is being used (over limit!)'}</div>
                    <div class="card-detail" id="cpuRequestAccuracyDetail">
                        {round(summary.total_requested.cpu / 1000, 1)} cores requested, {round(summary.total_actual.cpu / 1000, 1)} actually used
                    </div>
                    <div class="card-advice {'advice-success' if summary.total_actual.cpu <= summary.total_requested.cpu else 'advice-danger'}" id="cpuRequestAccuracyAdvice">
                        {'💡 Requests well-sized or over-provisioned' if summary.total_actual.cpu <= summary.total_requested.cpu else '⚠️ Usage exceeds requests - set proper limits!'}
                    </div>
                    <div class="filter-indicator hidden" id="cpuRequestAccuracyFilter"></div>
                </div>
                
                <div class="summary-card" id="memRequestAccuracyCard">
                    <div class="card-header">
                        <span class="card-title">Memory Request Accuracy</span>
                        <div class="card-icon memory">📊</div>
                    </div>
                    <div class="card-value {'text-success' if summary.total_actual.memory <= summary.total_requested.memory else 'text-danger'}" id="memRequestAccuracyValue">{round(summary.total_actual.memory / max(summary.total_requested.memory, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle" id="memRequestAccuracySubtitle">{'of requested memory is being used' if summary.total_actual.memory <= summary.total_requested.memory else 'of requested memory is being used (over limit!)'}</div>
                    <div class="card-detail" id="memRequestAccuracyDetail">
                        {round(summary.total_requested.memory / 1024, 1)} GiB requested, {round(summary.total_actual.memory / 1024, 1)} GiB actually used
                    </div>
                    <div class="card-advice {'advice-success' if summary.total_actual.memory <= summary.total_requested.memory else 'advice-danger'}" id="memRequestAccuracyAdvice">
                        {'💡 Requests well-sized or over-provisioned' if summary.total_actual.memory <= summary.total_requested.memory else '⚠️ Usage exceeds requests - set proper limits!'}
                    </div>
                    <div class="filter-indicator hidden" id="memRequestAccuracyFilter"></div>
                </div>
                
                <div class="summary-card" id="cpuCapacityCard">
                    <div class="card-header">
                        <span class="card-title">CPU Capacity Utilization</span>
                        <div class="card-icon cpu">📈</div>
                    </div>
                    <div class="card-value" id="cpuCapacityValue">{round(summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of total CPU capacity is being used</div>
                    <div class="card-detail" id="cpuCapacityDetail">
                        {round(summary.total_capacity.cpu / 1000, 0)} cores capacity, {round(summary.total_actual.cpu / 1000, 1)} actually used
                    </div>
                    <div class="card-advice advice-info" id="cpuCapacityAdvice">
                        {'ℹ️ Low utilization - room to grow' if summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) < 0.5 else '⚡ Moderate utilization' if summary.total_actual.cpu / max(summary.total_capacity.cpu, 1) < 0.8 else '🔥 High utilization - consider scaling'}
                    </div>
                    <div class="filter-indicator hidden" id="cpuCapacityFilter"></div>
                </div>
                
                <div class="summary-card" id="memCapacityCard">
                    <div class="card-header">
                        <span class="card-title">Memory Capacity Utilization</span>
                        <div class="card-icon memory">📈</div>
                    </div>
                    <div class="card-value" id="memCapacityValue">{round(summary.total_actual.memory / max(summary.total_capacity.memory, 1) * 100, 0):.0f}%</div>
                    <div class="card-subtitle">of total memory capacity is being used</div>
                    <div class="card-detail" id="memCapacityDetail">
                        {round(summary.total_capacity.memory / 1024, 0)} GiB capacity, {round(summary.total_actual.memory / 1024, 1)} GiB actually used
                    </div>
                    <div class="card-advice advice-info" id="memCapacityAdvice">
                        {'ℹ️ Low utilization - room to grow' if summary.total_actual.memory / max(summary.total_capacity.memory, 1) < 0.5 else '⚡ Moderate utilization' if summary.total_actual.memory / max(summary.total_capacity.memory, 1) < 0.8 else '🔥 High utilization - consider scaling'}
                    </div>
                    <div class="filter-indicator hidden" id="memCapacityFilter"></div>
                </div>
            </div>
            
            <div class="charts-grid" id="efficiencyCharts">
                <div class="chart-card">
                    <h3 class="chart-title" id="cpuChartTitle">CPU: Requested vs Actual per Node</h3>
                    <div class="chart-container">
                        <canvas id="cpuEfficiencyChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title" id="memChartTitle">Memory: Requested vs Actual per Node</h3>
                    <div class="chart-container">
                        <canvas id="memoryEfficiencyChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-container" style="margin-top: 1.5rem;">
                <div class="table-header">
                    <h3 class="table-title">Per-Node Efficiency Details (<span id="efficiencyTableCount">{len(nodes)}</span>)</h3>
                </div>
                <div class="table-scroll">
                    <table id="efficiencyTable">
                        <thead>
                            <tr>
                                <th>Node</th>
                                <th>Role</th>
                                <th>CPU Requested</th>
                                <th>CPU Actual</th>
                                <th>CPU Efficiency</th>
                                <th>Memory Requested</th>
                                <th>Memory Actual</th>
                                <th>Memory Efficiency</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name'].split('.')[0]}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['cpu_requested']} cores</td>
                                <td>{n['cpu_actual']} cores</td>
                                <td>
                                    <span class="badge {'badge-danger' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 20 else 'badge-warning' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 < 50 else 'badge-success' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 <= 100 else 'badge-warning' if n['cpu_requested'] > 0 and n['cpu_actual']/max(n['cpu_requested'],0.01)*100 <= 150 else 'badge-danger'}">
                                        {round(n['cpu_actual']/max(n['cpu_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                                <td>{n['mem_requested']} GiB</td>
                                <td>{n['mem_actual']} GiB</td>
                                <td>
                                    <span class="badge {'badge-danger' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 20 else 'badge-warning' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 < 50 else 'badge-success' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 <= 100 else 'badge-warning' if n['mem_requested'] > 0 and n['mem_actual']/max(n['mem_requested'],0.01)*100 <= 150 else 'badge-danger'}">
                                        {round(n['mem_actual']/max(n['mem_requested'],0.01)*100, 0):.0f}%
                                    </span>
                                </td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Workloads Tab -->
        <div class="tab-content" id="workloads">
            <div class="section-header">
                <h2 class="section-title">Workload Distribution</h2>
                <p class="section-subtitle">Analysis of pod distribution across namespaces and nodes</p>
            </div>
            
            <!-- Filter Bar -->
            <div class="filter-bar">
                <span class="filter-label">Filter by Role:</span>
                <div class="filter-buttons">
                    <button class="filter-btn active" data-filter="all" data-table="workloadTable">
                        All <span class="filter-count">{len(nodes)}</span>
                    </button>
                    {'<button class="filter-btn control-plane" data-filter="control-plane" data-table="workloadTable">🎛️ Control Plane <span class="filter-count">' + str(role_summaries.get("control-plane", {}).get("count", 0)) + '</span></button>' if 'control-plane' in role_summaries else ''}
                    {'<button class="filter-btn infra" data-filter="infra" data-table="workloadTable">🔧 Infra <span class="filter-count">' + str(role_summaries.get("infra", {}).get("count", 0)) + '</span></button>' if 'infra' in role_summaries else ''}
                    {'<button class="filter-btn storage" data-filter="storage" data-table="workloadTable">💾 Storage <span class="filter-count">' + str(role_summaries.get("storage", {}).get("count", 0)) + '</span></button>' if 'storage' in role_summaries else ''}
                    {'<button class="filter-btn worker" data-filter="worker" data-table="workloadTable">⚙️ Workers <span class="filter-count">' + str(role_summaries.get("worker", {}).get("count", 0)) + '</span></button>' if 'worker' in role_summaries else ''}
                </div>
            </div>
            
            <div class="charts-grid" id="workloadCharts">
                <div class="chart-card">
                    <h3 class="chart-title" id="namespaceChartTitle">Pods by Namespace (All {len(sorted_ns)} namespaces)</h3>
                    <div class="chart-container scrollable" id="namespaceChartContainer">
                        <canvas id="namespaceChart"></canvas>
                    </div>
                </div>
                
                <div class="chart-card">
                    <h3 class="chart-title" id="podsPerNodeChartTitle">Pods per Node</h3>
                    <div class="chart-container">
                        <canvas id="podsPerNodeChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-container" style="margin-top: 1.5rem;">
                <div class="table-header">
                    <h3 class="table-title">Pods per Node (<span id="workloadTableCount">{len(nodes)}</span>)</h3>
                </div>
                <div class="table-scroll">
                    <table id="workloadTable">
                        <thead>
                            <tr>
                                <th>Node</th>
                                <th>Role</th>
                                <th>Pod Count</th>
                                <th>Pod Capacity</th>
                                <th>Utilization</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr data-role="{n['role']}">
                                <td><strong>{n['name'].split('.')[0]}</strong></td>
                                <td><span class="role-badge role-{n['role']}">{n['role']}</span></td>
                                <td>{n['pod_count']}</td>
                                <td>{n['pod_capacity']}</td>
                                <td>
                                    <div>{round(n['pod_count']/max(n['pod_capacity'],1)*100, 1)}%</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill progress-low" style="width: {min(n['pod_count']/max(n['pod_capacity'],1)*100, 100)}%"></div>
                                    </div>
                                </td>
                            </tr>
                            """ for n in nodes_json])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Recommendations Tab -->
        <div class="tab-content" id="recommendations">
            <div class="section-header">
                <h2 class="section-title">OpenShift Sizing Recommendations</h2>
                <p class="section-subtitle">Recommended node configurations for OpenShift based on your current workload</p>
            </div>
            
            <div class="recommendations-grid">
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(0,102,204,0.2); color: var(--rh-blue);">🎛️</div>
                        <div>
                            <h3 class="rec-card-title">Control Plane</h3>
                            <span class="badge badge-info">master nodes</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['control_plane']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['control_plane']['current_cpu']:.0f} vCPU × {recommendations['control_plane']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['control_plane']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['control_plane']['recommended_cpu']} vCPU × {recommendations['control_plane']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["control_plane"]["notes"]]) + '</div>' if recommendations["control_plane"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(103,83,172,0.2); color: var(--rh-purple);">🔧</div>
                        <div>
                            <h3 class="rec-card-title">Infrastructure</h3>
                            <span class="badge badge-info">logging, monitoring, router</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['infra']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['infra']['current_cpu']:.0f} vCPU × {recommendations['infra']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['infra']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['infra']['recommended_cpu']} vCPU × {recommendations['infra']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["infra"]["notes"]]) + '</div>' if recommendations["infra"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(0,149,150,0.2); color: var(--rh-cyan);">💾</div>
                        <div>
                            <h3 class="rec-card-title">Storage (ODF)</h3>
                            <span class="badge badge-info">OpenShift Data Foundation</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['storage']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['storage']['current_cpu']:.0f} vCPU × {recommendations['storage']['current_memory']/1024:.0f} GiB
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Recommended</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['storage']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['storage']['recommended_cpu']} vCPU × {recommendations['storage']['recommended_memory']/1024:.0f} GiB
                            </div>
                        </div>
                    </div>
                    {'<div class="rec-notes">' + ''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["storage"]["notes"]]) + '</div>' if recommendations["storage"]["notes"] else ''}
                </div>
                
                <div class="rec-card">
                    <div class="rec-card-header">
                        <div class="rec-icon" style="background: rgba(240,171,0,0.2); color: var(--rh-orange);">⚙️</div>
                        <div>
                            <h3 class="rec-card-title">Worker Nodes</h3>
                            <span class="badge badge-info">application workloads</span>
                        </div>
                    </div>
                    <div class="rec-comparison">
                        <div class="rec-column">
                            <div class="rec-column-label">Current</div>
                            <div class="rec-column-value">{recommendations['worker']['current_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['worker']['current_cpu']:.0f} vCPU total
                            </div>
                        </div>
                        <div class="rec-column">
                            <div class="rec-column-label">Optimized</div>
                            <div class="rec-column-value" style="color: var(--rh-green);">{recommendations['worker']['recommended_count']}</div>
                            <div class="rec-column-detail">
                                {recommendations['worker']['recommended_cpu']} vCPU × {recommendations['worker']['recommended_memory']/1024:.0f} GiB each
                            </div>
                        </div>
                    </div>
                    <div class="rec-notes">
                        <div class="rec-note">
                            <span class="rec-note-icon">📊</span>
                            Actual CPU used: {recommendations['worker']['actual_cpu_used']:.1f} cores | Memory used: {recommendations['worker']['actual_memory_used']/1024:.1f} GiB
                        </div>
                        {''.join([f'<div class="rec-note"><span class="rec-note-icon">⚠️</span>{note}</div>' for note in recommendations["worker"]["notes"]])}
                    </div>
                </div>
            </div>
            
            {f'''
            <div class="opportunities-section">
                <h3 class="opportunities-title">💡 Optimization Opportunities</h3>
                {"".join([f'<div class="opportunity-item"><span>✅</span><span>{opp}</span></div>' for opp in recommendations["overall"]["opportunities"]])}
            </div>
            ''' if recommendations["overall"]["opportunities"] else ''}
            
            {f'''
            <div class="warnings-section">
                <h3 class="warnings-title">⚠️ Warnings</h3>
                {"".join([f'<div class="warning-item"><span class="warning-icon">⚠️</span><span>{warn}</span></div>' for warn in recommendations["overall"]["warnings"]])}
            </div>
            ''' if recommendations["overall"]["warnings"] else ''}
        </div>
        
        <!-- Checklist Tab -->
        <div class="tab-content" id="checklist">
            <div class="section-header">
                <h2 class="section-title">Migration Checklist</h2>
                <p class="section-subtitle">Pre-migration compatibility checks and considerations</p>
            </div>
            
            <div class="recommendations-grid">
                <div class="checklist">
                    <h3 class="checklist-title">Platform Compatibility</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else 'warn'}">
                            {'✓' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else '!'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Kubernetes Version</div>
                            <div class="check-detail">{summary.kubernetes_version} - {'Compatible with OCP 4.14+' if 'v1.2' in summary.kubernetes_version or 'v1.3' in summary.kubernetes_version else 'Check OCP version compatibility'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if 'cri-o' in summary.container_runtime.lower() else 'info'}">
                            {'✓' if 'cri-o' in summary.container_runtime.lower() else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Container Runtime</div>
                            <div class="check-detail">{summary.container_runtime} - {'Already using CRI-O' if 'cri-o' in summary.container_runtime.lower() else 'OCP uses CRI-O, verify image compatibility'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon pass">✓</div>
                        <div class="check-text">
                            <div class="check-label">Infrastructure Provider</div>
                            <div class="check-detail">{summary.provider} - Supported platform for OpenShift</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else 'warn'}">
                            {'✓' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else '!'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Version Consistency</div>
                            <div class="check-detail">{'All nodes running same kubelet version' if all(n['kubelet_version'] == nodes_json[0]['kubelet_version'] for n in nodes_json) else 'Mixed versions detected - standardize before migration'}</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Resource Considerations</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if recommendations['control_plane']['current_count'] >= 3 else 'warn' if recommendations['control_plane']['current_count'] > 0 else 'info'}">
                            {'✓' if recommendations['control_plane']['current_count'] >= 3 else '!' if recommendations['control_plane']['current_count'] > 0 else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Control Plane HA</div>
                            <div class="check-detail">{recommendations['control_plane']['current_count']} master nodes - {'HA configuration' if recommendations['control_plane']['current_count'] >= 3 else 'Single Node or compact cluster' if recommendations['control_plane']['current_count'] == 1 else 'Recommend 3 for HA'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'pass' if recommendations['infra']['current_count'] >= 3 else 'warn' if recommendations['infra']['current_count'] > 0 else 'info'}">
                            {'✓' if recommendations['infra']['current_count'] >= 3 else '!' if recommendations['infra']['current_count'] > 0 else 'i'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Infrastructure Nodes</div>
                            <div class="check-detail">{recommendations['infra']['current_count']} infra nodes - {'Good for OCP monitoring/logging' if recommendations['infra']['current_count'] >= 3 else 'Consider dedicated infra nodes for larger clusters' if recommendations['infra']['current_count'] == 0 else 'Consider adding more for HA'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon {'warn' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else 'pass'}">
                            {'!' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else '✓'}
                        </div>
                        <div class="check-text">
                            <div class="check-label">Resource Efficiency</div>
                            <div class="check-detail">{recommendations['overall']['efficiency_score']}% efficiency - {'Significant right-sizing opportunity' if recommendations['overall']['efficiency_score'] < 30 and recommendations['overall']['efficiency_score'] > 0 else 'Good utilization'}</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Network Plugin</div>
                            <div class="check-detail">OCP uses OVN-Kubernetes by default - verify network policy compatibility</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Workload Analysis</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon pass">✓</div>
                        <div class="check-text">
                            <div class="check-label">Total Pods</div>
                            <div class="check-detail">{summary.total_pods} pods across {len(summary.namespaces)} namespaces</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Node Taints</div>
                            <div class="check-detail">{len([n for n in nodes_json if n['taints'] != 'None'])} nodes have taints - verify tolerations for OCP workloads</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Security Contexts</div>
                            <div class="check-detail">Review pod security policies - OCP uses Security Context Constraints (SCCs)</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">i</div>
                        <div class="check-text">
                            <div class="check-label">Storage Classes</div>
                            <div class="check-detail">Map existing storage classes to OCP storage provisioners</div>
                        </div>
                    </div>
                </div>
                
                <div class="checklist">
                    <h3 class="checklist-title">Pre-Migration Tasks</h3>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Export YAML Manifests</div>
                            <div class="check-detail">Export deployments, services, configmaps, secrets for migration</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Image Registry</div>
                            <div class="check-detail">Plan container image migration strategy to OCP internal registry</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">Persistent Data</div>
                            <div class="check-detail">Plan PV/PVC migration and data backup strategy</div>
                        </div>
                    </div>
                    
                    <div class="checklist-item">
                        <div class="check-icon info">☐</div>
                        <div class="check-text">
                            <div class="check-label">DNS/Ingress</div>
                            <div class="check-detail">Plan Route migration from Ingress resources</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Storage Tab (Always visible, shows "No Data" if no PVs) -->
        <div class="tab-content" id="storage">
            <div class="section-header">
                <h2 class="section-title">Persistent Volumes</h2>
                <p class="section-subtitle">Storage analysis and migration considerations</p>
            </div>
            
            {f'''
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total PVs</span>
                        <div class="card-icon storage">💾</div>
                    </div>
                    <div class="card-value">{summary.total_pv_count}</div>
                    <div class="card-subtitle">persistent volumes</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Total Capacity</span>
                        <div class="card-icon storage">📊</div>
                    </div>
                    <div class="card-value">{summary.total_pv_capacity:.1f}</div>
                    <div class="card-subtitle">GiB provisioned</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-header">
                        <span class="card-title">Storage Classes</span>
                        <div class="card-icon storage">🏷️</div>
                    </div>
                    <div class="card-value">{len(summary.storage_classes)}</div>
                    <div class="card-subtitle">{", ".join(list(summary.storage_classes)[:3]) if summary.storage_classes else "N/A"}</div>
                </div>
            </div>
            
            <div class="table-container">
                <div class="table-header">
                    <h3 class="table-title">Persistent Volume Details</h3>
                </div>
                <div class="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Capacity</th>
                                <th>Access Modes</th>
                                <th>Reclaim Policy</th>
                                <th>Status</th>
                                <th>Claim</th>
                                <th>Storage Class</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f"""
                            <tr>
                                <td><strong>{pv['name']}</strong></td>
                                <td>{pv['capacity']:.1f} GiB</td>
                                <td>{pv['access_modes']}</td>
                                <td>{pv['reclaim_policy']}</td>
                                <td><span class="badge {'badge-success' if pv['status'] == 'Bound' else 'badge-warning'}">{pv['status']}</span></td>
                                <td>{pv['claim']}</td>
                                <td>{pv['storage_class']}</td>
                            </tr>
                            """ for pv in pvs_json])}
                        </tbody>
                    </table>
                </div>
            </div>
            ''' if pvs else '''
            <div class="no-data">
                <div class="no-data-icon">💾</div>
                <h3 class="no-data-title">No Persistent Volume Data Available</h3>
                <p class="no-data-text">PV information was not provided. To include storage analysis, run:</p>
                <p class="no-data-text" style="margin-top: 1rem; font-family: monospace; background: var(--bg-tertiary); padding: 0.75rem; border-radius: 6px; display: inline-block;">
                    kubectl get pv -o wide &gt; cluster-pv.txt
                </p>
                <p class="no-data-text" style="margin-top: 1rem;">Then re-run the tool with the -p flag to include PV analysis.</p>
            </div>
            '''}
        </div>
    </main>
    
    <footer class="footer">
        <p>OCP Sizing Calculator v1.1 | Generated by Red Hat Solution Architecture</p>
        <p>This assessment is based on point-in-time data. Actual requirements may vary based on workload patterns.</p>
    </footer>
    
    <script>
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
                    }}
                    
                    // Update workloads tab charts
                    if (tableId === 'workloadTable') {{
                        updateWorkloadsTabForFilter(filter);
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
    </script>
</body>
</html>
'''
    
    return html


# =============================================================================
# Main Function
# =============================================================================

