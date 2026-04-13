"""
base.py
-------
HTML base structure: doctype, head, header, filters bar, and tab navigation.
Provides the skeleton that wraps all tab content.
Supports multiple source platforms (RHV, VMware, etc.)
"""

try:
    from .styles import get_styles
except ImportError:
    from styles import get_styles


# Source platform display names
SOURCE_DISPLAY_NAMES = {
    'rhv': 'Red Hat Virtualization',
    'vmware': 'VMware vSphere'
}


def get_html_head(data):
    """Return HTML head section with meta tags, title, and Chart.js CDN."""
    source = data.get('source_platform', 'rhv')
    source_display = SOURCE_DISPLAY_NAMES.get(source, source.upper())
    title = f"{source_display} to OpenShift Virtualization Migration Dashboard"
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Migration planning dashboard for {source_display} to OpenShift Virtualization">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
{get_styles()}
    </style>
</head>
'''


def get_header(data):
    """Return the dashboard header with title and generation timestamp."""
    generated_at = data.get('generated_at', '')
    cluster_names = ', '.join(data.get('unique_clusters', ['Unknown']))
    source = data.get('source_platform', 'rhv')
    source_display = SOURCE_DISPLAY_NAMES.get(source, source.upper())
    
    return f'''<body>
    <div class="header">
        <div>
            <h1>{source_display} to OpenShift Virtualization</h1>
            <div class="header-subtitle">{cluster_names}</div>
        </div>
        <div class="header-right">
            <div class="label">Generated</div>
            <div class="value">{generated_at}</div>
        </div>
    </div>
'''


def get_filters_bar(data):
    """Return the filters bar with all filter dropdowns."""
    # Build cluster options
    cluster_options = '<option value="all">All Clusters</option>\n'
    for cluster in data.get('unique_clusters', []):
        cluster_options += f'                <option value="{cluster}">{cluster}</option>\n'
    
    # Build host options
    host_options = '<option value="all">All Hosts</option>\n'
    for host in data.get('unique_hosts', []):
        host_options += f'                <option value="{host}">{host}</option>\n'
    
    return f'''    <div class="filters-bar">
        <div class="filter-group">
            <label>Cluster</label>
            <select id="filter-cluster" onchange="applyFilters()">
                {cluster_options.strip()}
            </select>
        </div>
        <div class="filter-group">
            <label>OS Family</label>
            <select id="filter-os" onchange="applyFilters()">
                <option value="all">All OS</option>
                <option value="Linux">Linux</option>
                <option value="Windows">Windows</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Status</label>
            <select id="filter-status" onchange="applyFilters()">
                <option value="all">All Status</option>
                <option value="On">Running</option>
                <option value="Off">Powered Off</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Migration Complexity</label>
            <select id="filter-complexity" onchange="applyFilters()">
                <option value="all">All Complexity</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Host</label>
            <select id="filter-host" onchange="applyFilters()">
                {host_options.strip()}
            </select>
        </div>
        <button class="reset-btn" onclick="resetFilters()">Reset Filters</button>
    </div>
'''


def get_tab_navigation():
    """Return the tab navigation bar."""
    return '''    <div class="tabs">
        <div class="tab active" data-tab="overview" onclick="switchTab('overview')">Overview</div>
        <div class="tab" data-tab="sizing" onclick="switchTab('sizing')">Sizing Analysis</div>
        <div class="tab" data-tab="migration" onclick="switchTab('migration')">Migration Planning</div>
        <div class="tab" data-tab="trends" onclick="switchTab('trends')">Growth Trends</div>
        <div class="tab" data-tab="forecast" onclick="switchTab('forecast')">Forecasting</div>
        <div class="tab" data-tab="inventory" onclick="switchTab('inventory')">VM Inventory</div>
        <div class="tab" data-tab="hosts" onclick="switchTab('hosts')">Hosts Inventory</div>
    </div>
'''


def get_content_wrapper_start():
    """Return the opening tag for the main content area."""
    return '''    <div class="content">
'''


def get_content_wrapper_end():
    """Return the closing tag for the main content area."""
    return '''    </div>
'''


def get_html_close():
    """Return closing HTML tags."""
    return '''</body>
</html>
'''


def wrap_tab_content(tab_id, content, active=False):
    """Wrap tab content in the appropriate container div."""
    active_class = ' active' if active else ''
    return f'''        <div id="tab-{tab_id}" class="tab-content{active_class}">
{content}
        </div>
'''



# Convenience function to get full base structure
def get_base_start(data):
    """
    Return the complete base HTML up to the content area.
    Call this first, then add tab contents, then call get_base_end().
    """
    return (
        get_html_head(data) +
        get_header(data) +
        get_filters_bar(data) +
        get_tab_navigation() +
        get_content_wrapper_start()
    )


def get_base_end(scripts_content):
    """
    Return the closing HTML including scripts.
    scripts_content: The JavaScript code to embed.
    """
    return (
        get_content_wrapper_end() +
        f'''    <script>
{scripts_content}
    </script>
''' +
        get_html_close()
    )


# For testing
if __name__ == '__main__':
    # Mock data for testing
    mock_data = {
        'generated_at': '2025-12-09 22:00:00',
        'unique_clusters': ['HH-NONPROD-CLU01'],
        'unique_hosts': ['np-f02-hh-sy01', 'np-f02-hh-sy02'],
        'source_platform': 'rhv'
    }
    
    html = get_base_start(mock_data)
    html += "        <!-- Tab contents would go here -->\n"
    html += get_base_end("// JavaScript would go here")
    
    print(f"Base HTML generated: {len(html)} characters ({len(html)/1024:.1f} KB)")
