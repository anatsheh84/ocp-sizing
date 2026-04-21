"""
components package
------------------
Contains all modular components for the Virtualization Migration Dashboard generator.
Supports multiple source platforms: RHV, VMware, and future sources.
"""

from .styles import STYLES, get_styles
from .base import (
    get_html_head,
    get_header,
    get_filters_bar,
    get_tab_navigation,
    get_content_wrapper_start,
    get_content_wrapper_end,
    get_html_close,
    wrap_tab_content,
    get_base_start,
    get_base_end
)
from .tab_overview import generate_tab_overview, get_overview_chart_configs
from .tab_sizing import generate_tab_sizing, get_sizing_chart_configs
from .tab_migration import generate_tab_migration, get_migration_chart_configs
from .tab_trends import generate_tab_trends, get_trends_chart_configs
from .tab_forecast import generate_tab_forecast, get_forecast_base_data
from .tab_inventory import generate_tab_inventory, get_inventory_data
from .tab_hosts import generate_tab_hosts, get_hosts_chart_configs
from .scripts import generate_scripts, collect_chart_configs

__all__ = [
    'get_styles',
    'STYLES',
    'get_base_start',
    'get_base_end',
    'wrap_tab_content',
    'generate_tab_overview',
    'get_overview_chart_configs',
    'generate_tab_sizing',
    'get_sizing_chart_configs',
    'generate_tab_migration',
    'get_migration_chart_configs',
    'generate_tab_trends',
    'get_trends_chart_configs',
    'generate_tab_forecast',
    'get_forecast_base_data',
    'generate_tab_inventory',
    'get_inventory_data',
    'generate_tab_hosts',
    'get_hosts_chart_configs',
    'generate_scripts',
    'collect_chart_configs'
]
