# -*- coding: utf-8 -*-
"""
storage.py
----------
Persistent Volumes tab for the OCP Sizing HTML report.

Always visible; shows a "No Data" placeholder when no PV file was
provided (ctx.pvs is empty), otherwise summary cards + full PV table.

Extracted from html_reporter.py in Phase 5b of the refactor. HTML is
unchanged from pre-phase output; only the wrapping function and
location moved.
"""

from reporters.report_context import ReportContext


def build(ctx: ReportContext) -> str:
    """Render the Persistent Volumes tab (including its <div class=tab-content> wrapper)."""
    summary = ctx.summary
    pvs = ctx.pvs
    pvs_json = ctx.pvs_json
    return f'''        <!-- Storage Tab (Always visible, shows "No Data" if no PVs) -->
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
        </div>'''
