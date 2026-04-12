#!/usr/bin/env python3
"""
generate_report.py
------------------
Main orchestrator for OCP Sizing Calculator.

Generates OpenShift sizing recommendations from Kubernetes cluster data.

Usage:
    python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt [-p pvs.txt] [-o report.html]
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Import our modular components
from parsers import parse_describe_nodes, parse_top_nodes, parse_pvs
from analyzers import ClusterAnalyzer, RecommendationEngine
from reporters import generate_html_report


def read_file(filepath: str) -> str:
    """Read content from file."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)


def prepare_report_data(nodes, summary, recommendations, pvs):
    """Prepare data for HTML report generation."""
    # Convert nodes to JSON format
    nodes_json = []
    for node in nodes:
        analyzer = ClusterAnalyzer([node])
        role = analyzer.categorize_node_role(node)
        
        cpu_req_pct = (node.allocated_requests.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_req_pct = (node.allocated_requests.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        cpu_actual_pct = (node.actual_usage.cpu / node.allocatable.cpu * 100) if node.allocatable.cpu > 0 else 0
        mem_actual_pct = (node.actual_usage.memory / node.allocatable.memory * 100) if node.allocatable.memory > 0 else 0
        
        nodes_json.append({
            'name': node.name,
            'role': role,
            'roles': ', '.join(node.roles) if node.roles else 'worker',
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
            'is_schedulable': node.is_schedulable
        })
    
    return {
        'nodes': nodes_json,
        'summary': summary,
        'recommendations': recommendations,
        'pvs': pvs,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='OCP Sizing Calculator - Analyze Kubernetes clusters for OpenShift migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -d nodes_describe.txt -t nodes_top.txt
  %(prog)s -d nodes_describe.txt -t nodes_top.txt -p pvs.txt -o report.html
  %(prog)s -d nodes_describe.txt -t nodes_top.txt --pdf
  %(prog)s -d nodes_describe.txt -t nodes_top.txt -p pvs.txt -o report.html --pdf
        '''
    )
    
    parser.add_argument('-d', '--describe', required=True,
                        help='kubectl describe nodes output file (required)')
    parser.add_argument('-t', '--top', required=True,
                        help='kubectl top nodes output file (required)')
    parser.add_argument('-p', '--pvs',
                        help='kubectl get pv -o wide output file (optional)')
    parser.add_argument('-o', '--output', default='ocp_sizing_report.html',
                        help='Output HTML report filename (default: ocp_sizing_report.html)')
    parser.add_argument('--pdf', action='store_true',
                        help='Generate PDF export of the report (requires playwright)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("OCP Sizing Calculator v2.1 (PDF Export)")
    print("=" * 80)
    
    # Step 1: Read input files
    print(f"\n📖 Reading input files...")
    print(f"   Describe: {args.describe}")
    describe_content = read_file(args.describe)
    
    print(f"   Top:      {args.top}")
    top_content = read_file(args.top)
    
    pvs = []
    if args.pvs:
        print(f"   PVs:      {args.pvs}")
        pv_content = read_file(args.pvs)
        pvs = parse_pvs(pv_content)
        print(f"   Found {len(pvs)} persistent volumes")
    else:
        print("   ℹ️  No PV file provided")
    
    # Step 2: Parse data
    print(f"\n🔍 Parsing data...")
    print(f"   Parsing nodes...")
    nodes = parse_describe_nodes(describe_content)
    print(f"   ✓ Found {len(nodes)} nodes")
    
    print(f"   Parsing metrics...")
    top_data = parse_top_nodes(top_content)
    print(f"   ✓ Found metrics for {len(top_data)} nodes")
    
    # Step 3: Analyze cluster
    print(f"\n🔬 Analyzing cluster...")
    analyzer = ClusterAnalyzer(nodes, pvs)
    analyzer.merge_metrics(top_data)
    summary = analyzer.calculate_summary()
    print(f"   ✓ Analysis complete")
    
    # Step 4: Generate recommendations
    print(f"\n💡 Generating recommendations...")
    rec_engine = RecommendationEngine(nodes, summary)
    recommendations = rec_engine.generate_recommendations()
    print(f"   ✓ Recommendations generated")
    
    # Step 5: Generate HTML report
    print(f"\n📝 Generating HTML report...")
    print(f"   Using modular HTML generator...")

    # Use modular HTML reporter
    html = generate_html_report(nodes, summary, recommendations, pvs)
    
    with open(args.output, 'w') as f:
        f.write(html)
    
    file_size = Path(args.output).stat().st_size / 1024
    print(f"   ✓ Report generated: {file_size:.1f} KB")
    
    # Step 6: Generate PDF if requested
    if args.pdf:
        try:
            from reporters import (
                export_to_pdf, 
                check_playwright_installed, 
                check_pillow_installed,
                print_installation_instructions
            )
            
            # Check if dependencies are installed
            playwright_ok = check_playwright_installed()
            pillow_ok = check_pillow_installed()
            
            if not playwright_ok or not pillow_ok:
                print("\n⚠️  Missing dependencies for PDF export")
                if not playwright_ok:
                    print("   - Playwright not installed or Chromium browser missing")
                if not pillow_ok:
                    print("   - Pillow not installed")
                print_installation_instructions()
            else:
                # Generate PDF with same name as HTML
                pdf_output = str(Path(args.output).with_suffix('.pdf'))
                export_to_pdf(args.output, pdf_output)
        except ImportError:
            print("\n⚠️  Playwright not installed")
            print("   Install with: pip install playwright && playwright install chromium")
        except Exception as e:
            print(f"\n⚠️  PDF generation failed: {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Nodes:           {summary.total_nodes}")
    for role, count in sorted(summary.nodes_by_role.items()):
        print(f"  - {role:18s}: {count}")
    print(f"\nCPU Capacity:          {summary.total_capacity.cpu / 1000:.0f} cores")
    print(f"CPU Actual Usage:      {summary.total_actual.cpu / 1000:.1f} cores")
    print(f"Memory Capacity:       {summary.total_capacity.memory / 1024:.0f} GiB")
    print(f"Memory Actual Usage:   {summary.total_actual.memory / 1024:.1f} GiB")
    print(f"Total Pods:            {summary.total_pods}")
    print(f"Efficiency Score:      {recommendations['overall']['efficiency_score']:.1f}%")
    
    print(f"\nRecommended OCP Cluster:")
    print(f"  Control Plane:       {recommendations['control_plane']['recommended_count']} nodes")
    print(f"  Infrastructure:      {recommendations['infra']['recommended_count']} nodes")
    print(f"  Storage (ODF):       {recommendations['storage']['recommended_count']} nodes")
    print(f"  Workers:             {recommendations['worker']['recommended_count']} nodes")
    print(f"  Total:               {recommendations['overall']['total_recommended_nodes']} nodes")
    
    node_diff = summary.total_nodes - recommendations['overall']['total_recommended_nodes']
    if node_diff > 0:
        print(f"\n💰 Potential Savings:  {node_diff} nodes")
    elif node_diff < 0:
        print(f"\n📈 Additional Capacity: {abs(node_diff)} nodes needed")
    
    print("\n" + "=" * 80)
    print(f"✅ Report generated: {args.output}")
    print("=" * 80)


if __name__ == '__main__':
    main()
