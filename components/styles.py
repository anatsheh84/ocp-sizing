"""
styles.py
---------
All CSS styles for the RHV Migration Dashboard.
Returns CSS as a string to be embedded in the HTML.
"""


def get_styles():
    """Return complete CSS stylesheet as string."""
    return '''
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background-color: #f5f5f5;
    color: #333;
    line-height: 1.6;
}

/* ============================================
   HEADER
   ============================================ */
.header {
    background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
    color: white;
    padding: 20px 30px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

.header h1 {
    font-size: 24px;
    font-weight: 600;
}

.header-subtitle {
    font-size: 14px;
    opacity: 0.9;
    margin-top: 4px;
}

.header-right {
    text-align: right;
}

.header-right .label {
    font-size: 12px;
    opacity: 0.8;
}

.header-right .value {
    font-size: 14px;
}

/* ============================================
   FILTERS BAR
   ============================================ */
.filters-bar {
    background: white;
    padding: 15px 30px;
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    align-items: flex-end;
    border-bottom: 1px solid #e0e0e0;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.filter-group label {
    font-size: 11px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
}

.filter-group select {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    min-width: 150px;
    background: white;
    cursor: pointer;
    transition: border-color 0.2s;
}

.filter-group select:focus {
    outline: none;
    border-color: #CC0000;
}

.reset-btn {
    background: #CC0000;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-left: auto;
    transition: background 0.2s;
}

.reset-btn:hover {
    background: #990000;
}

/* ============================================
   TABS NAVIGATION
   ============================================ */
.tabs {
    display: flex;
    background: white;
    border-bottom: 2px solid #e0e0e0;
    position: sticky;
    top: 62px;
    z-index: 99;
    overflow-x: auto;
}

.tab {
    padding: 15px 25px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #666;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
    white-space: nowrap;
    user-select: none;
}

.tab:hover {
    color: #CC0000;
    background: #fafafa;
}

.tab.active {
    color: #CC0000;
    border-bottom-color: #CC0000;
    background: white;
}

/* ============================================
   CONTENT AREA
   ============================================ */
.content {
    padding: 25px 30px;
    max-width: 1600px;
    margin: 0 auto;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

/* ============================================
   STAT CARDS
   ============================================ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #CC0000;
}

.stat-card.blue {
    border-left-color: #2196F3;
}

.stat-card.green {
    border-left-color: #4CAF50;
}

.stat-card.orange {
    border-left-color: #FF9800;
}

.stat-card.purple {
    border-left-color: #9C27B0;
}

.stat-card.teal {
    border-left-color: #009688;
}

.stat-label {
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
    font-weight: 600;
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: #333;
    margin: 5px 0;
}

.stat-detail {
    font-size: 13px;
    color: #888;
}

/* ============================================
   CHART CARDS
   ============================================ */
.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 25px;
    margin-bottom: 30px;
}

.chart-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.chart-card.full-width {
    grid-column: 1 / -1;
}

.chart-card.half-width {
    grid-column: span 1;
}

.chart-title {
    font-size: 16px;
    font-weight: 600;
    color: #333;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

.chart-container {
    position: relative;
    height: 300px;
}

.chart-container.small {
    height: 250px;
}

.chart-container.tall {
    height: 400px;
}

/* ============================================
   LEGEND BOX
   ============================================ */
.legend-box {
    background: #f8f9fa;
    border-radius: 6px;
    padding: 12px 15px;
    margin-top: 10px;
    font-size: 12px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 5px 0;
}

.legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex-shrink: 0;
}

/* ============================================
   TABLES
   ============================================ */
.table-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    overflow: hidden;
    margin-bottom: 30px;
}

.table-header {
    padding: 15px 20px;
    background: #fafafa;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.table-title {
    font-size: 16px;
    font-weight: 600;
    color: #333;
}

.table-wrapper {
    overflow-x: auto;
}

.table-wrapper.scrollable {
    max-height: 500px;
    overflow-y: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

thead {
    background: #f8f8f8;
    position: sticky;
    top: 0;
    z-index: 10;
}

th {
    padding: 12px 15px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    border-bottom: 2px solid #e0e0e0;
    white-space: nowrap;
}

td {
    padding: 12px 15px;
    border-bottom: 1px solid #eee;
    font-size: 14px;
}

tr:hover {
    background: #fafafa;
}

.table-footer {
    padding: 12px 20px;
    background: #fafafa;
    border-top: 1px solid #eee;
    font-size: 13px;
    color: #666;
}

/* ============================================
   BADGES
   ============================================ */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}

/* Status badges */
.badge-on, .badge-running {
    background: #e8f5e9;
    color: #2e7d32;
}

.badge-off, .badge-stopped {
    background: #f5f5f5;
    color: #757575;
}

/* Complexity badges */
.badge-low {
    background: #e8f5e9;
    color: #2e7d32;
}

.badge-medium {
    background: #fff3e0;
    color: #e65100;
}

.badge-high {
    background: #ffebee;
    color: #c62828;
}

/* Size category badges */
.badge-small {
    background: #e8f5e9;
    color: #2e7d32;
}

.badge-size-medium {
    background: #e3f2fd;
    color: #1565c0;
}

.badge-large {
    background: #fff3e0;
    color: #e65100;
}

.badge-xlarge {
    background: #ffebee;
    color: #c62828;
}

/* Cluster/Tag badges */
.badge-cluster {
    background: #e3f2fd;
    color: #1565c0;
}

/* Utilization badges */
.badge-util-low {
    background: #e8f5e9;
    color: #2e7d32;
}

.badge-util-medium {
    background: #fff3e0;
    color: #e65100;
}

.badge-util-high {
    background: #ffebee;
    color: #c62828;
}

/* ============================================
   COMPLEXITY CARDS (Migration Tab)
   ============================================ */
.complexity-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-bottom: 30px;
}

.complexity-card {
    background: white;
    border-radius: 8px;
    padding: 25px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}

.complexity-card.low {
    border-top: 4px solid #4CAF50;
}

.complexity-card.medium {
    border-top: 4px solid #FF9800;
}

.complexity-card.high {
    border-top: 4px solid #f44336;
}

.complexity-count {
    font-size: 48px;
    font-weight: 700;
}

.complexity-card.low .complexity-count {
    color: #4CAF50;
}

.complexity-card.medium .complexity-count {
    color: #FF9800;
}

.complexity-card.high .complexity-count {
    color: #f44336;
}

.complexity-label {
    font-size: 18px;
    font-weight: 600;
    color: #333;
    margin: 10px 0;
}

.complexity-desc {
    font-size: 13px;
    color: #666;
    line-height: 1.5;
}

/* ============================================
   CHECKLIST (Migration Tab)
   ============================================ */
.checklist {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.checklist-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 15px;
    color: #333;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

.checklist-item {
    display: flex;
    align-items: flex-start;
    padding: 12px 0;
    border-bottom: 1px solid #eee;
}

.checklist-item:last-child {
    border-bottom: none;
}

.checklist-checkbox {
    width: 20px;
    height: 20px;
    margin-right: 12px;
    margin-top: 2px;
    cursor: pointer;
    accent-color: #CC0000;
}

.checklist-text {
    flex: 1;
}

.checklist-text strong {
    display: block;
    color: #333;
    margin-bottom: 2px;
}

.checklist-text span {
    font-size: 13px;
    color: #666;
}

/* ============================================
   CONFIG PANEL (Forecast Tab)
   ============================================ */
.config-panel {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 25px;
    color: white;
}

.config-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
}

.config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.config-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.config-group label {
    font-size: 12px;
    opacity: 0.9;
    text-transform: uppercase;
    font-weight: 500;
}

.config-group select,
.config-group input {
    padding: 10px 12px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    background: rgba(255,255,255,0.95);
    color: #333;
}

.config-group input:disabled {
    background: rgba(255,255,255,0.5);
    color: #666;
}

.apply-btn {
    background: white;
    color: #1565c0;
    border: none;
    padding: 12px 28px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
}

.apply-btn:hover {
    background: #f0f0f0;
    transform: translateY(-1px);
}

/* ============================================
   YEAR PROJECTION CARDS (Forecast Tab)
   ============================================ */
.year-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-bottom: 30px;
}

.year-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}

.year-card.current {
    border: 2px solid #CC0000;
}

.year-card.projected {
    border: 2px dashed #1565c0;
}

.year-label {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.year-title {
    font-size: 20px;
    font-weight: 700;
    color: #333;
    margin-bottom: 15px;
}

.year-stat {
    margin: 10px 0;
}

.year-stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #333;
}

.year-stat-label {
    font-size: 12px;
    color: #888;
}

/* ============================================
   ASSUMPTIONS TABLE
   ============================================ */
.assumptions-note {
    font-size: 13px;
    color: #666;
    font-style: italic;
}

/* ============================================
   RESPONSIVE DESIGN
   ============================================ */
@media (max-width: 1200px) {
    .charts-grid {
        grid-template-columns: 1fr;
    }
    
    .year-cards {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .header {
        flex-direction: column;
        text-align: center;
        gap: 10px;
    }
    
    .header-right {
        text-align: center;
    }
    
    .filters-bar {
        flex-direction: column;
        align-items: stretch;
    }
    
    .filter-group {
        width: 100%;
    }
    
    .filter-group select {
        width: 100%;
    }
    
    .reset-btn {
        margin-left: 0;
        width: 100%;
    }
    
    .tabs {
        top: 0;
    }
    
    .tab {
        padding: 12px 15px;
        font-size: 13px;
    }
    
    .content {
        padding: 15px;
    }
    
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .stat-value {
        font-size: 24px;
    }
    
    .complexity-cards {
        grid-template-columns: 1fr;
    }
    
    .year-cards {
        grid-template-columns: 1fr;
    }
    
    .config-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 480px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .header h1 {
        font-size: 18px;
    }
}

/* ============================================
   UTILITY CLASSES
   ============================================ */
.text-center {
    text-align: center;
}

.text-right {
    text-align: right;
}

.text-muted {
    color: #888;
}

.text-success {
    color: #4CAF50;
}

.text-warning {
    color: #FF9800;
}

.text-danger {
    color: #f44336;
}

.mt-1 { margin-top: 10px; }
.mt-2 { margin-top: 20px; }
.mt-3 { margin-top: 30px; }
.mb-1 { margin-bottom: 10px; }
.mb-2 { margin-bottom: 20px; }
.mb-3 { margin-bottom: 30px; }

.hidden {
    display: none !important;
}

/* ============================================
   PRINT STYLES
   ============================================ */
@media print {
    .filters-bar,
    .tabs,
    .reset-btn,
    .apply-btn,
    .config-panel {
        display: none;
    }
    
    .tab-content {
        display: block !important;
        page-break-after: always;
    }
    
    .chart-card,
    .stat-card,
    .table-container {
        box-shadow: none;
        border: 1px solid #ddd;
    }
}

/* ============================================
   NO DATA MESSAGE (for unavailable tabs)
   ============================================ */
.no-data-message {
    background: white;
    border-radius: 8px;
    padding: 60px 40px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin: 40px auto;
    max-width: 600px;
}

.no-data-message h3 {
    font-size: 24px;
    color: #666;
    margin-bottom: 20px;
}

.no-data-message p {
    font-size: 16px;
    color: #888;
    line-height: 1.6;
    margin-bottom: 10px;
}

.no-data-message .icon {
    font-size: 48px;
    margin-bottom: 20px;
}

/* ============================================
   DATA TABLE WITH MINI BARS
   ============================================ */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.data-table th {
    background: #f8f8f8;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    color: #666;
    border-bottom: 2px solid #e0e0e0;
    white-space: nowrap;
    position: sticky;
    top: 0;
    z-index: 10;
}

.data-table th:hover {
    background: #f0f0f0;
}

.data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #eee;
}

.data-table tr:hover {
    background: #fafafa;
}

.mini-bar {
    height: 10px;
    background: #e8e8e8;
    border-radius: 5px;
    overflow: hidden;
    min-width: 100px;
}

.mini-bar-fill {
    height: 100%;
    border-radius: 5px;
    transition: width 0.3s ease;
}

.mini-bar-fill.vms {
    background: linear-gradient(90deg, #2196F3, #1976D2);
}

.mini-bar-fill.vcpus {
    background: linear-gradient(90deg, #4CAF50, #388E3C);
}

.mini-bar-fill.memory {
    background: linear-gradient(90deg, #FF9800, #F57C00);
}
'''


# For testing
if __name__ == '__main__':
    css = get_styles()
    print(f"CSS generated: {len(css)} characters")
    print(f"Approximate size: {len(css) / 1024:.1f} KB")
