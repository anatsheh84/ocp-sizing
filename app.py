#!/usr/bin/env python3
"""
app.py - Web interface for OCP Sizing Calculator.
"""

import os
import json
import uuid
from datetime import datetime
from flask import (Flask, request, send_file, render_template_string,
                   flash, redirect, url_for)

from parsers import parse_describe_nodes, parse_top_nodes, parse_pvs
from analyzers import ClusterAnalyzer, RecommendationEngine
from reporters import generate_html_report

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ocp-sizing-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

REPORTS_DIR = '/tmp/ocp-reports'
os.makedirs(REPORTS_DIR, exist_ok=True)


def _save_report_meta(report_id, meta):
    """Save report metadata as JSON file next to the HTML."""
    path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    with open(path, 'w') as f:
        json.dump(meta, f)


def _load_report_meta(report_id):
    """Load report metadata from JSON file."""
    path = os.path.join(REPORTS_DIR, f'{report_id}.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _list_all_reports():
    """List all reports from filesystem, newest first."""
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

UPLOAD_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OCP Sizing Calculator</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
    --rh-red: #EE0000; --rh-red-dark: #A30000;
    --rh-black: #151515; --rh-gray-900: #212427;
    --rh-gray-800: #2D2D2D; --rh-gray-700: #3C3F42;
    --rh-gray-600: #4D5258; --rh-gray-300: #B8BBBE;
    --rh-white: #FFFFFF; --rh-green: #3E8635;
    --rh-green-light: #95D58F;
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
.right-panel {
    flex:1; padding:1.5rem 2rem; overflow-y:auto;
}
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
input[type="text"] {
    width:100%; padding:0.55rem 0.75rem; background:var(--rh-gray-700);
    border:1px solid var(--rh-gray-600); border-radius:8px;
    color:var(--rh-white); font-size:0.85rem; outline:none;
}
input[type="text"]:focus { border-color:var(--rh-red); }
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
.report-item:first-of-type {
    border-color:var(--rh-green);
}
.report-item .r-icon {
    width:38px; height:38px; background:rgba(62,134,53,0.15);
    border-radius:8px; display:flex; align-items:center;
    justify-content:center; font-size:1.1rem; flex-shrink:0;
}
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

@media (max-width:860px) {
    .main-layout { flex-direction:column; }
    .left-panel { width:100%; min-width:unset; border-right:none; border-bottom:1px solid var(--rh-gray-700); }
}
</style>
</head>
<body>
<div class="header">
    <h1>&#9654; OCP Sizing Calculator</h1>
    <p>Upload Kubernetes cluster data &middot; Get OpenShift migration recommendations</p>
</div>
<div class="main-layout">
<div class="left-panel">
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for category, message in messages %}
        <div class="flash-msg flash-{{ category }}">{{ message }}</div>
        {% endfor %}
    {% endif %}
    {% endwith %}

    <form method="POST" enctype="multipart/form-data" action="/generate" id="uploadForm">
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
            <div class="r-icon">&#128196;</div>
            <div class="r-info">
                <div class="r-name">{{ r.name }}</div>
                <div class="r-meta">{{ r.timestamp }} &middot; {{ r.nodes }} nodes</div>
            </div>
            <div class="r-actions">
                <a href="/download/{{ r.id }}" class="btn-dl">&#11015; Download</a>
                <button onclick="printReport('{{ r.id }}')" class="btn-pr">&#128424; Print</button>
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
    btn.disabled = true;
    btn.textContent = '\u23F3 Generating report...';
});
function printReport(reportId) {
    var w = window.open('/view/' + reportId, '_blank');
    w.addEventListener('load', function() {
        setTimeout(function() { w.print(); }, 1500);
    });
}
</script>
</body>
</html>
'''


@app.route('/', methods=['GET'])
def index():
    return render_template_string(UPLOAD_TEMPLATE, reports_list=_list_all_reports())


@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}, 200


@app.route('/view/<report_id>')
def view_report(report_id):
    """Serve report for in-browser viewing (used by print)."""
    meta = _load_report_meta(report_id)
    html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
    if not meta or not os.path.exists(html_path):
        return 'Report not found', 404
    return send_file(html_path, mimetype='text/html')


@app.route('/download/<report_id>')
def download(report_id):
    """Serve report as a file download."""
    meta = _load_report_meta(report_id)
    html_path = os.path.join(REPORTS_DIR, f'{report_id}.html')
    if not meta or not os.path.exists(html_path):
        flash('Report not found or expired.', 'error')
        return redirect(url_for('index'))
    return send_file(html_path, mimetype='text/html',
                     as_attachment=True, download_name=meta['filename'])


@app.route('/generate', methods=['POST'])
def generate():
    """Process uploaded files, save report, redirect back to index."""
    if 'describe_file' not in request.files or 'top_file' not in request.files:
        flash('Both "describe nodes" and "top nodes" files are required.', 'error')
        return redirect(url_for('index'))

    describe_file = request.files['describe_file']
    top_file = request.files['top_file']
    pvs_file = request.files.get('pvs_file')

    if describe_file.filename == '' or top_file.filename == '':
        flash('Please select both required files.', 'error')
        return redirect(url_for('index'))

    try:
        describe_content = describe_file.read().decode('utf-8', errors='replace')
        top_content = top_file.read().decode('utf-8', errors='replace')

        if 'Name:' not in describe_content or 'Capacity:' not in describe_content:
            flash('Invalid "describe nodes" file.', 'error')
            return redirect(url_for('index'))
        if len(top_content.strip().splitlines()) < 2:
            flash('The "top nodes" file appears empty or invalid.', 'error')
            return redirect(url_for('index'))

        pvs = []
        if pvs_file and pvs_file.filename != '':
            pv_content = pvs_file.read().decode('utf-8', errors='replace')
            pvs = parse_pvs(pv_content)

        nodes = parse_describe_nodes(describe_content)
        if not nodes:
            flash('No nodes could be parsed. Check the file format.', 'error')
            return redirect(url_for('index'))

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
        safe = "".join(c if c.isalnum() or c in (' ','-','_') else '_' for c in report_name)
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
        })

        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port,
            debug=os.environ.get('DEBUG', 'false').lower() == 'true')
