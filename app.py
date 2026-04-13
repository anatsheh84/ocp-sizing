#!/usr/bin/env python3
"""
app.py - Unified Web Interface for:
  1. OCP Sizing Calculator (Kubernetes cluster analysis)
  2. VM Migration Assessment (RHV/VMware to OpenShift Virtualization)
"""

import os
import json
import uuid
import tempfile
from datetime import datetime
from flask import (Flask, request, send_file, render_template_string,
                   flash, redirect, url_for)

# OCP Sizing imports
from parsers import parse_describe_nodes, parse_top_nodes, parse_pvs
from analyzers import ClusterAnalyzer, RecommendationEngine
from reporters import generate_html_report

# VM Migration imports
from generate_dashboard import generate_dashboard

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ocp-sizing-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

REPORTS_DIR = '/tmp/ocp-reports'
os.makedirs(REPORTS_DIR, exist_ok=True)


def _save_report_meta(report_id, meta):
    path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    with open(path, 'w') as f:
        json.dump(meta, f)


def _load_report_meta(report_id):
    path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _list_all_reports():
    result = []
    for fname in os.listdir(REPORTS_DIR):
        if fname.endswith('.json'):
            rid = fname.replace('.json', '')
            meta = _load_report_meta(rid)
            html_path = os.path.join(REPORTS_DIR, f'{rid}.html')
            if meta and os.path.exists(html_path):
                meta['id'] = rid
                result.append(meta)
    result.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
    return result

# ─────────────────────────────────────────────
# Shared CSS (used by all pages)
# ─────────────────────────────────────────────
SHARED_CSS = r'''
:root {
    --rh-red: #EE0000; --rh-red-dark: #A30000;
    --rh-black: #151515; --rh-gray-900: #212427;
    --rh-gray-800: #2D2D2D; --rh-gray-700: #3C3F42;
    --rh-gray-600: #4D5258; --rh-gray-300: #B8BBBE;
    --rh-white: #FFFFFF; --rh-green: #3E8635;
    --rh-green-light: #95D58F; --rh-blue: #0066CC;
    --rh-purple: #6753AC;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family:'Red Hat Text',-apple-system,sans-serif;
    background:var(--rh-gray-900); color:var(--rh-white);
    min-height:100vh; display:flex; flex-direction:column;
}
.header {
    width:100%; background:linear-gradient(135deg,var(--rh-black) 0%,var(--rh-gray-900) 100%);
    border-bottom:3px solid var(--rh-red); padding:1.25rem 2rem; text-align:center;
}
.header h1 { font-family:'Red Hat Display',sans-serif; font-size:1.6rem; font-weight:700; }
.header p { color:var(--rh-gray-300); font-size:0.85rem; margin-top:0.2rem; }
.main-layout { display:flex; flex:1; }
.left-panel {
    width:420px; min-width:380px; padding:1.5rem;
    border-right:1px solid var(--rh-gray-700); overflow-y:auto;
}
.right-panel { flex:1; padding:1.5rem 2rem; overflow-y:auto; }
.card {
    background:var(--rh-gray-800); border:1px solid var(--rh-gray-700);
    border-radius:12px; padding:1.5rem; margin-bottom:1.25rem;
}
.card h2 {
    font-family:'Red Hat Display',sans-serif; font-size:1rem; font-weight:600;
    margin-bottom:0.75rem; padding-bottom:0.6rem; border-bottom:1px solid var(--rh-gray-700);
}
.file-group { margin-bottom:1rem; }
.file-group label { display:block; font-size:0.82rem; font-weight:500; margin-bottom:0.35rem; color:var(--rh-gray-300); }
.file-group .required { color:var(--rh-red); margin-left:2px; }
.file-group .hint { font-size:0.72rem; color:var(--rh-gray-600); margin-top:0.2rem; }
input[type="file"] {
    width:100%; padding:0.5rem; background:var(--rh-gray-700);
    border:1px dashed var(--rh-gray-600); border-radius:8px;
    color:var(--rh-gray-300); font-size:0.82rem; cursor:pointer;
}
input[type="file"]:hover { border-color:var(--rh-red); background:var(--rh-gray-600); }
input[type="text"], select {
    width:100%; padding:0.55rem 0.75rem; background:var(--rh-gray-700);
    border:1px solid var(--rh-gray-600); border-radius:8px;
    color:var(--rh-white); font-size:0.85rem; outline:none;
}
input[type="text"]:focus, select:focus { border-color:var(--rh-red); }
input[type="text"]::placeholder { color:var(--rh-gray-600); }
.submit-btn {
    width:100%; padding:0.8rem; background:var(--rh-red); color:white;
    border:none; border-radius:8px; font-family:'Red Hat Display',sans-serif;
    font-size:0.95rem; font-weight:600; cursor:pointer; transition:background 0.2s;
}
.submit-btn:hover { background:var(--rh-red-dark); }
.submit-btn:disabled { background:var(--rh-gray-600); cursor:not-allowed; }
.flash-msg { padding:0.6rem 0.85rem; border-radius:8px; margin-bottom:0.75rem; font-size:0.82rem; }
.flash-error { background:rgba(238,0,0,0.15); border:1px solid var(--rh-red); color:#FF5C5C; }
.empty-state { text-align:center; color:var(--rh-gray-600); margin-top:4rem; }
.empty-state .icon { font-size:3rem; margin-bottom:0.75rem; }
.empty-state p { font-size:0.9rem; }
.reports-title {
    font-family:'Red Hat Display',sans-serif; font-size:1.1rem; font-weight:600;
    margin-bottom:1rem; color:var(--rh-gray-300);
}
.report-item {
    display:flex; align-items:center; gap:1rem;
    background:var(--rh-gray-800); border:1px solid var(--rh-gray-700);
    border-radius:10px; padding:1rem 1.25rem; margin-bottom:0.75rem;
    transition: border-color 0.2s;
}
.report-item:first-of-type { border-color:var(--rh-green); }
.report-item .r-icon {
    width:38px; height:38px; border-radius:8px; display:flex;
    align-items:center; justify-content:center; font-size:1.1rem; flex-shrink:0;
}
.r-icon-ocp { background:rgba(62,134,53,0.15); }
.r-icon-vm { background:rgba(103,83,172,0.15); }
.report-item .r-info { flex:1; min-width:0; }
.report-item .r-name {
    font-family:'Red Hat Display',sans-serif; font-size:0.9rem;
    font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.report-item .r-meta { font-size:0.72rem; color:var(--rh-gray-300); margin-top:0.15rem; }
.report-item .r-actions { display:flex; gap:0.5rem; flex-shrink:0; }
.r-actions a, .r-actions button {
    display:flex; align-items:center; justify-content:center;
    gap:0.35rem; padding:0.45rem 0.75rem; border-radius:6px;
    font-size:0.78rem; font-weight:600; text-decoration:none;
    cursor:pointer; transition:background 0.2s; border:none;
    font-family:'Red Hat Display',sans-serif;
}
.btn-dl { background:var(--rh-green); color:white; }
.btn-dl:hover { background:#2d6b28; }
.btn-pr { background:var(--rh-gray-700); color:var(--rh-gray-300); border:1px solid var(--rh-gray-600) !important; }
.btn-pr:hover { background:var(--rh-gray-600); color:white; }
.btn-del { background:transparent; color:var(--rh-gray-600); border:1px solid var(--rh-gray-700) !important; }
.btn-del:hover { background:rgba(238,0,0,0.1); color:var(--rh-red); border-color:var(--rh-red) !important; }
.badge {
    display:inline-block; padding:0.12rem 0.5rem; border-radius:4px;
    font-size:0.65rem; font-weight:600; text-transform:uppercase; letter-spacing:0.03em;
}
.badge-ocp { background:rgba(62,134,53,0.2); color:var(--rh-green-light); }
.badge-vm { background:rgba(103,83,172,0.2); color:#B8A9E0; }
/* Landing page */
.landing { display:flex; flex-direction:column; align-items:center; justify-content:center; flex:1; padding:2rem; }
.tool-grid { display:flex; gap:1.5rem; margin-top:1.5rem; flex-wrap:wrap; justify-content:center; }
.tool-card {
    background:var(--rh-gray-800); border:2px solid var(--rh-gray-700);
    border-radius:16px; padding:2rem 1.75rem; width:300px;
    text-decoration:none; color:var(--rh-white); transition:all 0.2s;
    text-align:center; cursor:pointer; display:block;
}
.tool-card:hover { border-color:var(--rh-red); transform:translateY(-3px); }
.tool-card .tc-icon { font-size:2.5rem; margin-bottom:0.75rem; }
.tool-card h3 { font-family:'Red Hat Display',sans-serif; font-size:1.15rem; font-weight:700; margin-bottom:0.4rem; }
.tool-card p { font-size:0.82rem; color:var(--rh-gray-300); line-height:1.5; }
.tool-card .tc-tag {
    display:inline-block; margin-top:0.75rem; padding:0.2rem 0.65rem;
    border-radius:6px; font-size:0.7rem; font-weight:600;
}
.tc-tag-ocp { background:rgba(62,134,53,0.2); color:var(--rh-green-light); }
.tc-tag-vm { background:rgba(103,83,172,0.2); color:#B8A9E0; }
.back-link {
    display:inline-flex; align-items:center; gap:0.4rem; color:var(--rh-gray-300);
    text-decoration:none; font-size:0.82rem; margin-bottom:1rem;
}
.back-link:hover { color:var(--rh-white); }
@media (max-width:860px) {
    .main-layout { flex-direction:column; }
    .left-panel { width:100%; min-width:unset; border-right:none; border-bottom:1px solid var(--rh-gray-700); }
    .tool-grid { flex-direction:column; align-items:center; }
}
'''

# ─────────────────────────────────────────────
# Landing Page Template
# ─────────────────────────────────────────────
LANDING_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenShift Assessment Tools</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&display=swap" rel="stylesheet">
<style>''' + SHARED_CSS + '''</style>
</head>
<body>
<div class="header">
    <h1>&#9654; OpenShift Assessment Tools</h1>
    <p>Cluster sizing &middot; VM migration analysis &middot; Infrastructure planning</p>
</div>
<div class="landing">
    <div class="tool-grid">
        <a href="/ocp" class="tool-card">
            <div class="tc-icon">&#9881;</div>
            <h3>OCP Sizing Calculator</h3>
            <p>Analyze Kubernetes clusters and generate OpenShift sizing recommendations with node inventory and efficiency analysis.</p>
            <span class="tc-tag tc-tag-ocp">K8s / OCP &rarr; OCP</span>
        </a>
        <a href="/migration" class="tool-card">
            <div class="tc-icon">&#128300;</div>
            <h3>VM Migration Assessment</h3>
            <p>Analyze RHV or VMware environments and generate migration dashboards with complexity scoring and wave planning.</p>
            <span class="tc-tag tc-tag-vm">RHV / VMware &rarr; OCP-V</span>
        </a>
    </div>
</div>
</body>
</html>
'''

# ─────────────────────────────────────────────
# OCP Sizing Template
# ─────────────────────────────────────────────
OCP_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OCP Sizing Calculator</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&display=swap" rel="stylesheet">
<style>''' + SHARED_CSS + '''</style>
</head>
<body>
<div class="header">
    <h1>&#9881; OCP Sizing Calculator</h1>
    <p>Upload Kubernetes cluster data &middot; Get OpenShift migration recommendations</p>
</div>
<div class="main-layout">
<div class="left-panel">
    <a href="/" class="back-link">&larr; Back to tools</a>
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for category, message in messages %}
    <div class="flash-msg flash-{{ category }}">{{ message }}</div>
    {% endfor %}{% endif %}{% endwith %}
    <form method="POST" enctype="multipart/form-data" action="/generate-ocp" id="uploadForm">
        <div class="card">
            <h2>&#128194; Upload Cluster Data</h2>
            <div class="file-group">
                <label>kubectl describe nodes<span class="required">*</span></label>
                <input type="file" name="describe_file" accept=".txt,.log,.out" required>
                <div class="hint">Run: kubectl describe nodes &gt; nodes_describe.txt</div>
            </div>
            <div class="file-group">
                <label>kubectl top nodes<span class="required">*</span></label>
                <input type="file" name="top_file" accept=".txt,.log,.out" required>
                <div class="hint">Run: kubectl top nodes &gt; nodes_top.txt</div>
            </div>
            <div class="file-group">
                <label>kubectl get pv -o wide <span style="color:var(--rh-gray-600)">(optional)</span></label>
                <input type="file" name="pvs_file" accept=".txt,.log,.out">
                <div class="hint">Run: kubectl get pv -o wide &gt; pvs.txt</div>
            </div>
        </div>
        <div class="card">
            <h2>&#9881; Report Options</h2>
            <div class="file-group">
                <label>Report Name</label>
                <input type="text" name="report_name" placeholder="e.g. Production Cluster Assessment">
            </div>
            <label style="display:flex; align-items:center; gap:0.6rem; cursor:pointer; font-size:0.85rem;">
                <input type="checkbox" name="include_recommendations" value="1" style="width:16px; height:16px; accent-color:var(--rh-red); cursor:pointer;">
                Include Migration Recommendations
                <span style="font-size:0.68rem; background:var(--rh-gray-700); color:var(--rh-gray-300); padding:0.12rem 0.45rem; border-radius:4px;">WIP</span>
            </label>
            <div class="hint" style="margin-top:0.3rem; margin-left:1.6rem;">Adds OCP Recommendations &amp; Migration Checklist tabs</div>
        </div>
        <button type="submit" class="submit-btn" id="submitBtn">&#128202; Generate Sizing Report</button>
    </form>
</div>
<div class="right-panel">
    {% if reports_list %}
    <div style="width:100%; max-width:600px;">
        <div class="reports-title">&#128203; Generated Reports ({{ reports_list|length }})</div>
        {% for r in reports_list %}
        <div class="report-item">
            <div class="r-icon {% if r.tool_type == 'ocp' %}r-icon-ocp{% else %}r-icon-vm{% endif %}">
                {% if r.tool_type == 'ocp' %}&#9881;{% else %}&#128300;{% endif %}
            </div>
            <div class="r-info">
                <div class="r-name">{{ r.name }}</div>
                <div class="r-meta">
                    <span class="badge {% if r.tool_type == 'ocp' %}badge-ocp{% else %}badge-vm{% endif %}">{{ r.tool_type_label }}</span>
                    · {{ r.timestamp }} · {{ r.detail }}
                </div>
            </div>
            <div class="r-actions">
                <a href="/download/{{ r.id }}" class="btn-dl">&#11015; Download</a>
                <a href="/view/{{ r.id }}" target="_blank" class="btn-pr">&#128065; View</a>
                <button onclick="deleteReport('{{ r.id }}', '{{ r.name }}')" class="btn-del">&#128465; Delete</button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="empty-state">
        <div class="icon">&#128202;</div>
        <p>Upload cluster data to generate a report</p>
    </div>
    {% endif %}
</div>
</div>
<script>
document.getElementById('uploadForm').addEventListener('submit', function() {
    var btn = document.getElementById('submitBtn');
    btn.disabled = true; btn.textContent = '\u23F3 Generating report...';
});
function deleteReport(id, name) {
    if (confirm('Delete report "' + name + '"?')) {
        fetch('/delete/' + id, { method: 'POST' }).then(function() { location.reload(); });
    }
}
</script>
</body></html>
'''

# ─────────────────────────────────────────────
# VM Migration Assessment Template
# ─────────────────────────────────────────────
MIGRATION_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VM Migration Assessment</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&display=swap" rel="stylesheet">
<style>''' + SHARED_CSS + '''</style>
</head>
<body>
<div class="header">
    <h1>&#128300; VM Migration Assessment</h1>
    <p>Analyze RHV or VMware environments &middot; Plan migration to OpenShift Virtualization</p>
</div>
<div class="main-layout">
<div class="left-panel">
    <a href="/" class="back-link">&larr; Back to tools</a>
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}{% for category, message in messages %}
    <div class="flash-msg flash-{{ category }}">{{ message }}</div>
    {% endfor %}{% endif %}{% endwith %}
    <form method="POST" enctype="multipart/form-data" action="/generate-migration" id="uploadForm">
        <div class="card">
            <h2>&#128194; Upload Virtualization Data</h2>
            <div class="file-group">
                <label>Source Platform<span class="required">*</span></label>
                <select name="source_platform" required>
                    <option value="rhv">Red Hat Virtualization (RHV)</option>
                    <option value="vmware">VMware vSphere (RVTools)</option>
                </select>
                <div class="hint">Select the platform your export file comes from</div>
            </div>
            <div class="file-group">
                <label>Export File (.xlsx)<span class="required">*</span></label>
                <input type="file" name="export_file" accept=".xlsx,.xls,.xlsm" required>
                <div class="hint">RHV: Admin Portal VM export &middot; VMware: RVTools vInfo export</div>
            </div>
            <div class="file-group">
                <label>Hosts File (.xlsx) <span style="color:var(--rh-gray-600)">(optional)</span></label>
                <input type="file" name="hosts_file" accept=".xlsx,.xls,.xlsm">
                <div class="hint">RHV: Separate hosts export &middot; Enables Hosts Inventory tab</div>
            </div>
        </div>
        <div class="card">
            <h2>&#9881; Report Options</h2>
            <div class="file-group">
                <label>Report Name</label>
                <input type="text" name="report_name" placeholder="e.g. Customer RHV Migration Assessment">
            </div>
        </div>
        <button type="submit" class="submit-btn" id="submitBtn">&#128300; Generate Migration Dashboard</button>
    </form>
</div>
<div class="right-panel">
    {% if reports_list %}
    <div style="width:100%; max-width:600px;">
        <div class="reports-title">&#128203; Generated Reports ({{ reports_list|length }})</div>
        {% for r in reports_list %}
        <div class="report-item">
            <div class="r-icon {% if r.tool_type == 'ocp' %}r-icon-ocp{% else %}r-icon-vm{% endif %}">
                {% if r.tool_type == 'ocp' %}&#9881;{% else %}&#128300;{% endif %}
            </div>
            <div class="r-info">
                <div class="r-name">{{ r.name }}</div>
                <div class="r-meta">
                    <span class="badge {% if r.tool_type == 'ocp' %}badge-ocp{% else %}badge-vm{% endif %}">{{ r.tool_type_label }}</span>
                    · {{ r.timestamp }} · {{ r.detail }}
                </div>
            </div>
            <div class="r-actions">
                <a href="/download/{{ r.id }}" class="btn-dl">&#11015; Download</a>
                <a href="/view/{{ r.id }}" target="_blank" class="btn-pr">&#128065; View</a>
                <button onclick="deleteReport('{{ r.id }}', '{{ r.name }}')" class="btn-del">&#128465; Delete</button>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="empty-state">
        <div class="icon">&#128300;</div>
        <p>Upload a virtualization export to generate a migration dashboard</p>
    </div>
    {% endif %}
</div>
</div>
<script>
document.getElementById('uploadForm').addEventListener('submit', function() {
    var btn = document.getElementById('submitBtn');
    btn.disabled = true; btn.textContent = '\u23F3 Generating dashboard...';
});
function deleteReport(id, name) {
    if (confirm('Delete report "' + name + '"?')) {
        fetch('/delete/' + id, { method: 'POST' }).then(function() { location.reload(); });
    }
}
</script>
</body></html>
'''

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/', methods=['GET'])
def index():
    return render_template_string(LANDING_TEMPLATE)


@app.route('/ocp', methods=['GET'])
def ocp_tool():
    reports = [r for r in _list_all_reports() if r.get('tool_type') == 'ocp']
    return render_template_string(OCP_TEMPLATE, reports_list=reports)


@app.route('/migration', methods=['GET'])
def migration_tool():
    reports = [r for r in _list_all_reports() if r.get('tool_type') == 'vm']
    return render_template_string(MIGRATION_TEMPLATE, reports_list=reports)


@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}, 200


@app.route('/view/<report_id>')
def view_report(report_id):
    meta = _load_report_meta(report_id)
    html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
    if not meta or not os.path.exists(html_path):
        return 'Report not found', 404
    return send_file(html_path, mimetype='text/html')

@app.route('/download/<report_id>')
def download(report_id):
    meta = _load_report_meta(report_id)
    html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
    if not meta or not os.path.exists(html_path):
        flash('Report not found or expired.', 'error')
        return redirect(url_for('index'))
    return send_file(html_path, mimetype='text/html',
                     as_attachment=True, download_name=meta['filename'])


@app.route('/delete/<report_id>', methods=['POST'])
def delete_report(report_id):
    html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
    json_path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    if os.path.exists(html_path):
        os.unlink(html_path)
    if os.path.exists(json_path):
        os.unlink(json_path)
    return '', 204


# ─────────────────────────────────────────────
# OCP Sizing - Generate Route
# ─────────────────────────────────────────────
@app.route('/generate-ocp', methods=['POST'])
def generate_ocp():
    if 'describe_file' not in request.files or 'top_file' not in request.files:
        flash('Both "describe nodes" and "top nodes" files are required.', 'error')
        return redirect(url_for('ocp_tool'))

    describe_file = request.files['describe_file']
    top_file = request.files['top_file']
    pvs_file = request.files.get('pvs_file')

    if describe_file.filename == '' or top_file.filename == '':
        flash('Please select both required files.', 'error')
        return redirect(url_for('ocp_tool'))

    try:
        describe_content = describe_file.read().decode('utf-8', errors='replace')
        top_content = top_file.read().decode('utf-8', errors='replace')

        if 'Name:' not in describe_content or 'Capacity:' not in describe_content:
            flash('Invalid "describe nodes" file.', 'error')
            return redirect(url_for('ocp_tool'))
        if len(top_content.strip().splitlines()) < 2:
            flash('The "top nodes" file appears empty or invalid.', 'error')
            return redirect(url_for('ocp_tool'))

        pvs = []
        if pvs_file and pvs_file.filename != '':
            pv_content = pvs_file.read().decode('utf-8', errors='replace')
            pvs = parse_pvs(pv_content)

        nodes = parse_describe_nodes(describe_content)
        if not nodes:
            flash('No nodes could be parsed. Check the file format.', 'error')
            return redirect(url_for('ocp_tool'))

        top_data = parse_top_nodes(top_content)
        analyzer = ClusterAnalyzer(nodes, pvs)
        analyzer.merge_metrics(top_data)
        summary = analyzer.calculate_summary()

        rec_engine = RecommendationEngine(nodes, summary)
        recommendations = rec_engine.generate_recommendations()

        include_recs = request.form.get('include_recommendations') == '1'
        html = generate_html_report(nodes, summary, recommendations, pvs,
                                    include_recommendations=include_recs)

        report_name = request.form.get('report_name', '').strip()
        if not report_name:
            report_name = f'Cluster Report ({len(nodes)} nodes)'
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in report_name)
        filename = f'{safe}_{ts}.html'

        report_id = str(uuid.uuid4())[:8]
        html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        _save_report_meta(report_id, {
            'name': report_name,
            'filename': filename,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'nodes': len(nodes),
            'detail': f'{len(nodes)} nodes',
            'tool_type': 'ocp',
            'tool_type_label': 'OCP Sizing',
        })

        return redirect(url_for('ocp_tool'))

    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('ocp_tool'))


# ─────────────────────────────────────────────
# VM Migration - Generate Route
# ─────────────────────────────────────────────
@app.route('/generate-migration', methods=['POST'])
def generate_migration():
    if 'export_file' not in request.files:
        flash('An export file (.xlsx) is required.', 'error')
        return redirect(url_for('migration_tool'))

    export_file = request.files['export_file']
    source = request.form.get('source_platform', 'rhv')

    if export_file.filename == '':
        flash('Please select an export file.', 'error')
        return redirect(url_for('migration_tool'))

    if not export_file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm')):
        flash('Please upload an Excel file (.xlsx, .xls, .xlsm).', 'error')
        return redirect(url_for('migration_tool'))

    try:
        # Save uploaded file to a temp location for pandas to read
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsx')
        os.close(tmp_fd)
        export_file.save(tmp_path)

        # Save hosts file if provided
        hosts_tmp_path = None
        hosts_file = request.files.get('hosts_file')
        if hosts_file and hosts_file.filename != '':
            hosts_fd, hosts_tmp_path = tempfile.mkstemp(suffix='.xlsx')
            os.close(hosts_fd)
            hosts_file.save(hosts_tmp_path)

        # Generate dashboard HTML to a temp output file
        report_id = str(uuid.uuid4())[:8]
        html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')

        generate_dashboard(tmp_path, output_file=html_path, source=source,
                           hosts_file=hosts_tmp_path)

        # Clean up temp uploads
        os.unlink(tmp_path)
        if hosts_tmp_path and os.path.exists(hosts_tmp_path):
            os.unlink(hosts_tmp_path)

        # Read the generated HTML to extract VM count for metadata
        source_names = {'rhv': 'RHV', 'vmware': 'VMware'}
        source_label = source_names.get(source, source.upper())

        # Get VM count from the generated data
        from data_processor import process_excel
        # Re-process is wasteful but simple; alternatively parse from the HTML
        # For now, just use the file size as a proxy
        file_size_kb = os.path.getsize(html_path) / 1024

        report_name = request.form.get('report_name', '').strip()
        if not report_name:
            report_name = f'{source_label} Migration Assessment'
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in report_name)
        filename = f'{safe}_{ts}.html'

        _save_report_meta(report_id, {
            'name': report_name,
            'filename': filename,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'detail': f'{source_label} · {file_size_kb:.0f} KB',
            'tool_type': 'vm',
            'tool_type_label': f'{source_label} Migration',
        })

        return redirect(url_for('migration_tool'))

    except Exception as e:
        # Clean up temp files on error
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if 'hosts_tmp_path' in locals() and hosts_tmp_path and os.path.exists(hosts_tmp_path):
            os.unlink(hosts_tmp_path)
        flash(f'Error generating dashboard: {str(e)}', 'error')
        return redirect(url_for('migration_tool'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port,
            debug=os.environ.get('DEBUG', 'false').lower() == 'true')
