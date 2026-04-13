#!/usr/bin/env python3
"""
generate_dashboard.py
---------------------
Main orchestrator for Virtualization to OpenShift Migration Dashboard.

Supports multiple source platforms:
  - RHV (Red Hat Virtualization)
  - VMware vSphere (RVTools exports)

Usage:
    python generate_dashboard.py --source rhv <input_excel> [output_html]
    python generate_dashboard.py --source vmware <input_excel> [output_html]
    
Examples:
    python generate_dashboard.py --source rhv RHV-Export.xlsx
    python generate_dashboard.py --source vmware RVTools-Export.xlsx dashboard.html
"""

import sys
import os
import argparse
from datetime import datetime

# Import data processor
from data_processor import process_excel

# Import components
from components import (
    get_base_start,
    get_base_end,
    wrap_tab_content,
    generate_tab_overview,
    get_overview_chart_configs,
    generate_tab_sizing,
    get_sizing_chart_configs,
    generate_tab_migration,
    get_migration_chart_configs,
    generate_tab_trends,
    get_trends_chart_configs,
    generate_tab_forecast,
    get_forecast_base_data,
    generate_tab_inventory,
    generate_tab_hosts,
    get_hosts_chart_configs,
    generate_scripts
)


def generate_dashboard(input_file, output_file=None, source='rhv', hosts_file=None):
    """
    Generate the complete HTML dashboard from an Excel file.
    
    Args:
        input_file: Path to virtualization export file
        output_file: Path for output HTML (optional)
        source: Source platform ('rhv' or 'vmware')
        hosts_file: Optional separate hosts Excel file path
        
    Returns:
        Path to generated HTML file
    """
    
    # Determine output file name
    if output_file is None:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_dashboard.html"
    
    source_names = {'rhv': 'RHV', 'vmware': 'VMware'}
    source_display = source_names.get(source, source.upper())
    
    print(f"Source Platform: {source_display}")
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    print("-" * 50)

    
    # Step 1: Process Excel data
    print("Step 1/4: Processing Excel data...")
    data = process_excel(input_file, source=source, hosts_filepath=hosts_file)
    print(f"  ✓ Loaded {data['stats']['total_vms']} VMs")
    print(f"  ✓ {data['stats']['total_vcpus']} vCPUs, {data['stats']['total_memory_gb']} GB Memory")
    if data.get('has_date_data'):
        print(f"  ✓ Date data available for trends/forecast")
    else:
        print(f"  ⚠ No date data (trends/forecast will be limited)")
    if data.get('host_data', {}).get('has_host_data', False):
        print(f"  ✓ Host data available ({data['host_data']['stats']['total_hosts']} hosts)")
    else:
        print(f"  ⚠ No host data (hosts tab will be limited)")
    
    # Step 2: Generate tab HTML content
    print("Step 2/4: Generating tab content...")
    tabs = {
        'overview': generate_tab_overview(data),
        'sizing': generate_tab_sizing(data),
        'migration': generate_tab_migration(data),
        'trends': generate_tab_trends(data),
        'forecast': generate_tab_forecast(data),
        'inventory': generate_tab_inventory(data),
        'hosts': generate_tab_hosts(data)
    }
    print(f"  ✓ Generated 7 tabs")
    
    # Step 3: Collect chart configurations
    print("Step 3/4: Preparing chart configurations...")
    chart_configs = {
        'overview': get_overview_chart_configs(data),
        'sizing': get_sizing_chart_configs(data),
        'migration': get_migration_chart_configs(data),
        'trends': get_trends_chart_configs(data),
        'forecast': get_forecast_base_data(data),
        'hosts': get_hosts_chart_configs(data)
    }
    print(f"  ✓ Prepared chart data for all tabs")
    
    # Step 4: Assemble final HTML
    print("Step 4/4: Assembling dashboard...")
    
    # Build HTML structure
    html_parts = []
    
    # Base start (head, header, filters, tab nav, content wrapper start)
    html_parts.append(get_base_start(data))
    
    # Tab contents
    html_parts.append(wrap_tab_content('overview', tabs['overview'], active=True))
    html_parts.append(wrap_tab_content('sizing', tabs['sizing']))
    html_parts.append(wrap_tab_content('migration', tabs['migration']))
    html_parts.append(wrap_tab_content('trends', tabs['trends']))
    html_parts.append(wrap_tab_content('forecast', tabs['forecast']))
    html_parts.append(wrap_tab_content('inventory', tabs['inventory']))
    html_parts.append(wrap_tab_content('hosts', tabs['hosts']))
    
    # Generate JavaScript
    scripts = generate_scripts(data, chart_configs)
    
    # Base end (close content wrapper, scripts, close html)
    html_parts.append(get_base_end(scripts))
    
    # Combine all parts
    final_html = ''.join(html_parts)
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    file_size = os.path.getsize(output_file) / 1024
    print(f"  ✓ Dashboard generated: {file_size:.1f} KB")
    print("-" * 50)
    print(f"✅ Success! Dashboard saved to: {output_file}")
    
    return output_file



def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='Generate OpenShift Virtualization Migration Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --source rhv RHV-Export.xlsx
  %(prog)s --source vmware RVTools-Export.xlsx dashboard.html
  %(prog)s -s rhv data.xlsx output.html

Supported Sources:
  rhv     - Red Hat Virtualization exports
  vmware  - VMware vSphere (RVTools vInfo sheet)
'''
    )
    
    parser.add_argument(
        '-s', '--source',
        choices=['rhv', 'vmware'],
        required=True,
        help='Source virtualization platform'
    )
    
    parser.add_argument(
        'input_file',
        help='Path to the Excel export file'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='Output HTML file path (optional, auto-generated if not specified)'
    )
    
    return parser


def main():
    """Command line entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)
    
    try:
        result = generate_dashboard(
            args.input_file,
            args.output_file,
            source=args.source
        )
        return result
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
