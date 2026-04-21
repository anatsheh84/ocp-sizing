# -*- coding: utf-8 -*-
"""
styles.py
---------
Extracted CSS for the OCP Sizing HTML report.

Phase 1 of the html_reporter.py refactor lifted this block out of the
parent f-string so braces are natural CSS syntax (no {{ }} escaping) and
so the main template stays small and readable.

Do NOT re-introduce f-string interpolation here. If a style value needs
to be dynamic, inject it through a class attribute on the element and
handle the branching in the calling tab module.
"""

STYLES = """\
    <style>
        :root {
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
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Red Hat Text', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, var(--rh-black) 0%, var(--rh-gray-900) 100%);
            border-bottom: 3px solid var(--rh-red);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .header-content {
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        
        .logo {
            width: 50px;
            height: 50px;
            background: var(--rh-red);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .logo svg {
            width: 30px;
            height: 30px;
            fill: white;
        }
        
        .title-section h1 {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        
        .title-section p {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        
        .header-meta {
            text-align: right;
            font-size: 0.875rem;
            color: var(--text-muted);
        }
        
        /* Navigation Tabs */
        .nav-tabs {
            background: var(--bg-secondary);
            padding: 0 2rem;
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }
        
        .nav-tabs-inner {
            max-width: 1800px;
            margin: 0 auto;
            display: flex;
            gap: 0;
        }
        
        .nav-tab {
            padding: 1rem 1.5rem;
            cursor: pointer;
            color: var(--text-secondary);
            font-weight: 500;
            border-bottom: 3px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap;
            font-size: 0.9rem;
        }
        
        .nav-tab:hover {
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }
        
        .nav-tab.active {
            color: var(--rh-red);
            border-bottom-color: var(--rh-red);
        }
        
        /* Main Content */
        .main-content {
            max-width: 1800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* Filter Bar */
        .filter-bar {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
        }
        
        .filter-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }
        
        .filter-buttons {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .filter-btn {
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
        }
        
        .filter-btn:hover {
            background: var(--rh-gray-600);
            color: var(--text-primary);
        }
        
        .filter-btn.active {
            background: var(--rh-red);
            border-color: var(--rh-red);
            color: white;
        }
        
        .filter-btn.active.control-plane { background: var(--rh-blue); border-color: var(--rh-blue); }
        .filter-btn.active.infra { background: var(--rh-purple); border-color: var(--rh-purple); }
        .filter-btn.active.storage { background: var(--rh-cyan); border-color: var(--rh-cyan); }
        .filter-btn.active.worker { background: var(--rh-orange); border-color: var(--rh-orange); }
        
        .filter-count {
            background: rgba(255,255,255,0.2);
            padding: 0.1rem 0.5rem;
            border-radius: 100px;
            font-size: 0.7rem;
        }
        
        /* Summary Cards */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .summary-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .summary-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        
        .summary-card.highlight {
            border-color: var(--rh-red);
            background: linear-gradient(135deg, var(--bg-secondary) 0%, rgba(238,0,0,0.1) 100%);
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }
        
        .card-title {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-icon {
            width: 40px;
            height: 40px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }
        
        .card-icon.nodes { background: rgba(0,102,204,0.2); color: var(--rh-blue); }
        .card-icon.cpu { background: rgba(62,134,53,0.2); color: var(--rh-green); }
        .card-icon.memory { background: rgba(103,83,172,0.2); color: var(--rh-purple); }
        .card-icon.pods { background: rgba(240,171,0,0.2); color: var(--rh-orange); }
        .card-icon.storage { background: rgba(0,149,150,0.2); color: var(--rh-cyan); }
        .card-icon.efficiency { background: rgba(238,0,0,0.2); color: var(--rh-red); }
        
        .card-value {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
        }
        
        .card-subtitle {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .card-detail {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--border-color);
        }
        
        /* Architecture Diagram */
        .architecture-diagram {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }
        
        .architecture-title {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        
        .architecture-title h3 {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            margin-bottom: 0.25rem;
        }
        
        .architecture-title p {
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        .architecture-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
        }
        
        .arch-tier {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        
        .arch-tier-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }
        
        .arch-tier-nodes {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
        }
        
        .arch-connector {
            width: 2px;
            height: 25px;
            background: linear-gradient(180deg, var(--rh-gray-600) 0%, var(--rh-gray-600) 50%, transparent 50%, transparent 100%);
            background-size: 2px 8px;
        }
        
        .arch-connector-h {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 70%;
            height: 25px;
            position: relative;
        }
        
        .arch-connector-h::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 15%;
            right: 15%;
            height: 2px;
            background: var(--rh-gray-600);
        }
        
        .arch-connector-h::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 2px;
            height: 12px;
            background: var(--rh-gray-600);
        }
        
        .arch-node-group {
            background: var(--rh-gray-700);
            border-radius: 10px;
            padding: 1rem 1.5rem;
            text-align: center;
            border: 2px solid transparent;
            transition: all 0.2s;
            min-width: 130px;
        }
        
        .arch-node-group:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        .arch-node-group.control-plane {
            border-color: var(--rh-blue);
            background: linear-gradient(135deg, rgba(0,102,204,0.2) 0%, var(--rh-gray-700) 100%);
        }
        
        .arch-node-group.infra {
            border-color: var(--rh-purple);
            background: linear-gradient(135deg, rgba(103,83,172,0.2) 0%, var(--rh-gray-700) 100%);
        }
        
        .arch-node-group.storage {
            border-color: var(--rh-cyan);
            background: linear-gradient(135deg, rgba(0,149,150,0.2) 0%, var(--rh-gray-700) 100%);
        }
        
        .arch-node-group.worker {
            border-color: var(--rh-orange);
            background: linear-gradient(135deg, rgba(240,171,0,0.2) 0%, var(--rh-gray-700) 100%);
        }
        
        .arch-node-group .icon {
            font-size: 1.75rem;
            margin-bottom: 0.25rem;
        }
        
        .arch-node-group .role {
            font-family: 'Red Hat Display', sans-serif;
            font-weight: 600;
            font-size: 0.85rem;
        }
        
        .arch-node-group .count {
            font-size: 1.75rem;
            font-weight: 700;
            font-family: 'Red Hat Display', sans-serif;
        }
        
        .arch-node-group.control-plane .count { color: var(--rh-blue); }
        .arch-node-group.infra .count { color: var(--rh-purple); }
        .arch-node-group.storage .count { color: var(--rh-cyan); }
        .arch-node-group.worker .count { color: var(--rh-orange); }
        
        .arch-node-group .specs {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }
        
        .arch-node-group .node-names {
            font-size: 0.65rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            padding-top: 0.5rem;
            border-top: 1px solid var(--rh-gray-600);
            max-width: 150px;
            word-wrap: break-word;
        }
        
        .arch-middle-tier {
            display: flex;
            justify-content: center;
            gap: 2rem;
        }
        
        .arch-legend {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid var(--rh-gray-700);
            flex-wrap: wrap;
        }
        
        .arch-legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .arch-legend-color {
            width: 14px;
            height: 14px;
            border-radius: 4px;
        }
        
        .arch-legend-color.cp { background: var(--rh-blue); }
        .arch-legend-color.infra { background: var(--rh-purple); }
        .arch-legend-color.storage { background: var(--rh-cyan); }
        .arch-legend-color.worker { background: var(--rh-orange); }
        
        /* Charts Section */
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .chart-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        
        .chart-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .chart-container.scrollable {
            height: auto;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .chart-container.scrollable canvas {
            min-height: 400px;
        }
        
        /* Tables */
        .table-container {
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }
        
        .table-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .table-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .table-search {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 0.875rem;
            width: 250px;
        }
        
        .table-search:focus {
            outline: none;
            border-color: var(--rh-blue);
        }
        
        .table-scroll {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }
        
        th {
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
        }
        
        th:hover {
            background: var(--rh-gray-600);
        }
        
        td {
            padding: 0.875rem 1rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-primary);
            white-space: nowrap;
        }
        
        tr:hover td {
            background: var(--bg-tertiary);
        }
        
        tr.filtered-out {
            display: none;
        }
        
        /* Status badges */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .badge-success { background: rgba(62,134,53,0.2); color: var(--rh-green-light); }
        .badge-warning { background: rgba(240,171,0,0.2); color: var(--rh-orange); }
        .badge-danger { background: rgba(238,0,0,0.2); color: var(--rh-red-light); }
        .badge-info { background: rgba(0,102,204,0.2); color: var(--rh-blue-light); }
        .badge-neutral { background: var(--bg-tertiary); color: var(--text-secondary); }
        
        /* Card value colors */
        .text-success { color: var(--rh-green-light) !important; }
        .text-danger { color: var(--rh-red-light) !important; }
        .text-warning { color: var(--rh-orange) !important; }
        .text-info { color: var(--rh-blue-light) !important; }
        
        /* Workload Inventory mini cards */
        .stat-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .stat-card-mini {
            background: var(--rh-gray-800);
            border: 1px solid var(--rh-gray-700);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            text-align: center;
        }
        .stat-card-mini.warn-card {
            border-color: var(--rh-orange);
            background: rgba(236, 122, 8, 0.08);
        }
        .stat-mini-value {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--rh-white);
        }
        .warn-card .stat-mini-value { color: var(--rh-orange); }
        .stat-mini-label {
            font-size: 0.78rem;
            color: var(--rh-gray-300);
            margin-top: 0.15rem;
            font-weight: 500;
        }
        .stat-mini-detail {
            font-size: 0.7rem;
            color: var(--rh-gray-500);
            margin-top: 0.25rem;
        }
        
        /* Card advice styles */
        .card-advice {
            font-size: 0.8rem;
            margin-top: 0.75rem;
            padding: 0.5rem;
            border-radius: 4px;
        }
        
        .advice-success {
            background: rgba(62,134,53,0.15);
            color: var(--rh-green-light);
        }
        
        .advice-danger {
            background: rgba(238,0,0,0.15);
            color: var(--rh-red-light);
        }
        
        .advice-warning {
            background: rgba(240,171,0,0.15);
            color: var(--rh-orange);
        }
        
        .advice-info {
            background: rgba(0,102,204,0.15);
            color: var(--rh-blue-light);
        }
        
        /* Role badges */
        .role-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-right: 0.25rem;
            text-transform: uppercase;
        }
        
        .role-control-plane { background: var(--rh-blue); color: white; }
        .role-infra { background: var(--rh-purple); color: white; }
        .role-storage { background: var(--rh-cyan); color: white; }
        .role-worker { background: var(--rh-gray-600); color: white; }
        
        /* Sticky sum footer row */
        tfoot {
            position: sticky;
            bottom: 0;
            z-index: 10;
        }
        
        tfoot tr {
            background: var(--rh-gray-700) !important;
            border-top: 2px solid var(--rh-red);
        }
        
        tfoot td {
            padding: 1rem;
            font-weight: 700;
            color: var(--rh-white);
            background: var(--rh-gray-700);
        }
        
        tfoot td:first-child {
            color: var(--rh-orange);
        }
        
        .table-scroll {
            max-height: 600px;
            overflow-y: auto;
        }
        
        /* Filter indicator badge */
        .filter-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--rh-gray-700);
            border-radius: 6px;
            font-size: 0.85rem;
            color: var(--rh-orange);
            margin-left: 1rem;
        }
        
        .filter-indicator.hidden {
            display: none;
        }
        
        .filter-indicator .clear-filter {
            cursor: pointer;
            color: var(--rh-gray-400);
            transition: color 0.2s;
        }
        
        .filter-indicator .clear-filter:hover {
            color: var(--rh-red);
        }
        
        /* Progress bars */
        .progress-bar {
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.25rem;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .progress-low { background: var(--rh-green); }
        .progress-medium { background: var(--rh-orange); }
        .progress-high { background: var(--rh-red); }
        
        /* Recommendations Section */
        .recommendations-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
        }
        
        .rec-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        
        .rec-card-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .rec-icon {
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .rec-card-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        .rec-comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .rec-column {
            text-align: center;
        }
        
        .rec-column-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        
        .rec-column-value {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 2rem;
            font-weight: 700;
        }
        
        .rec-column-detail {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .rec-notes {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }
        
        .rec-note {
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .rec-note-icon {
            color: var(--rh-orange);
        }
        
        /* Warnings & Opportunities */
        .warnings-section {
            background: rgba(238,0,0,0.1);
            border: 1px solid var(--rh-red);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2rem;
        }
        
        .warnings-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-red-light);
            margin-bottom: 1rem;
        }
        
        .warning-item {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        
        .warning-icon {
            color: var(--rh-orange);
            font-size: 1.25rem;
        }
        
        .opportunities-section {
            background: rgba(62,134,53,0.1);
            border: 1px solid var(--rh-green);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1.5rem;
        }
        
        .opportunities-title {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--rh-green-light);
            margin-bottom: 1rem;
        }
        
        .opportunity-item {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-secondary);
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        
        /* Checklist */
        .checklist {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
        }
        
        .checklist-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .checklist-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .checklist-item:last-child {
            border-bottom: none;
        }
        
        .check-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.875rem;
        }
        
        .check-icon.pass { background: var(--rh-green); color: white; }
        .check-icon.warn { background: var(--rh-orange); color: white; }
        .check-icon.fail { background: var(--rh-red); color: white; }
        .check-icon.info { background: var(--rh-blue); color: white; }
        
        .check-text {
            flex: 1;
        }
        
        .check-label {
            font-weight: 500;
        }
        
        .check-detail {
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        
        /* Section headers */
        .section-header {
            margin-bottom: 1.5rem;
        }
        
        .section-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .section-subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
        
        /* No Data Available */
        .no-data {
            text-align: center;
            padding: 4rem 2rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
        }
        
        .no-data-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
        
        .no-data-title {
            font-family: 'Red Hat Display', sans-serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
        }
        
        .no-data-text {
            color: var(--text-muted);
            font-size: 0.95rem;
        }
        
        /* Footer */
        .footer {
            margin-top: 3rem;
            padding: 2rem;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        /* Export buttons */
        .export-buttons {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        
        .btn {
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
        }
        
        .btn-primary {
            background: var(--rh-red);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--rh-red-dark);
        }
        
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover {
            background: var(--rh-gray-600);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header-content {
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }
            
            .header-meta {
                text-align: center;
            }
            
            .nav-tabs {
                padding: 0 1rem;
            }
            
            .nav-tab {
                padding: 0.75rem 1rem;
                font-size: 0.8rem;
            }
            
            .main-content {
                padding: 1rem;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            .filter-bar {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>"""
