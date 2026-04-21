# -*- coding: utf-8 -*-
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


from analyzers.cluster_analyzer import ClusterAnalyzer
from reporters.styles import STYLES
from reporters.scripts import build_script_body
from reporters.report_context import build_context
from reporters.layout import build_layout
from reporters.tabs import workload_inventory
from reporters.tabs import storage
from reporters.tabs import overview
from reporters.tabs import workloads as workloads_tab
from reporters.tabs import nodes as nodes_tab
from reporters.tabs import efficiency


def generate_html_report(nodes: List[NodeData], summary: ClusterSummary, 
                        recommendations: Dict, pvs: List[PersistentVolume],
                        include_recommendations: bool = True,
                        workloads: Dict = None) -> str:
    """Generate interactive HTML dashboard"""
    
    # Build typed view-model (Phase 3: ReportContext).
    # The main f-string below still references the old local names;
    # Phase 5 will migrate those to ctx.X as each tab module is extracted.
    ctx = build_context(nodes, summary, recommendations, pvs,
                        include_recommendations=include_recommendations,
                        workloads=workloads)
    nodes_json = ctx.nodes_json
    namespace_pods = ctx.namespace_pods
    sorted_ns = ctx.sorted_ns
    pvs_json = ctx.pvs_json
    nodes_by_role = ctx.nodes_by_role
    role_summaries = ctx.role_summaries
    workload_inventory_html = workload_inventory.build(ctx)
    storage_html = storage.build(ctx)
    overview_html = overview.build(ctx)
    workloads_html = workloads_tab.build(ctx)
    nodes_html = nodes_tab.build(ctx)
    efficiency_html = efficiency.build(ctx)
    script_body_html = ctx.script_body_html
    
    tabs_content_html = f'''{overview_html}
        
{nodes_html}
        
{efficiency_html}
        
{workloads_html}
        
        <!-- Workload Inventory Tab -->
        <div class="tab-content" id="workload-inventory">
{workload_inventory_html}
        </div>
        
        <!-- Recommendations Tab -->
        {'<div class="tab-content" id="recommendations">' if include_recommendations else '<!--'}
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
        {'</div>' if include_recommendations else '-->'}
        
        {'<!-- Checklist Tab -->' if include_recommendations else '<!--'}
        {'<div class="tab-content" id="checklist">' if include_recommendations else ''}
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
        {'</div>' if include_recommendations else '-->'}
        
{storage_html}'''
    html = build_layout(ctx, tabs_content_html, script_body_html)
    
    return html


# =============================================================================
# Main Function
# =============================================================================

