#!/usr/bin/env python3
"""
app.py
------
Web interface for OCP Sizing Calculator.

Simple Flask app that lets users upload kubectl output files
and download the generated HTML sizing report.
"""

import os
import tempfile
from datetime import datetime
from flask import Flask, request, send_file, render_template_string, flash, redirect, url_for

from parsers import parse_describe_nodes, parse_top_nodes, parse_pvs
from analyzers import ClusterAnalyzer, RecommendationEngine
from reporters import generate_html_report

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ocp-sizing-dev-key')

# Max upload size: 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

UPLOAD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OCP Sizing Calculator</title>
<link href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
    --rh-red: #EE0000;
    --rh-red-dark: #A30000;
    --rh-black: #151515;
    --rh-gray-900: #212427;
    --rh-gray-800: #2D2D2D;
    --rh-gray-700: #3C3F42;
    --rh-gray-600: #4D5258;
    --rh-gray-300: #B8BBBE;
    --rh-gray-100: #F0F0F0;
    --rh-white: #FFFFFF;
}
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Red Hat Text', -apple-system, sans-serif;
    background: var(--rh-gray-900);
    color: var(--rh-white);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.header {
    width: 100%;
    background: linear-gradient(135deg, var(--rh-black) 0%, var(--rh-gray-900) 100%);
    border-bottom: 3px solid var(--rh-red);
    padding: 1.5rem 2rem;
    text-align: center;
}

.header h1 {
    font-family: 'Red Hat Display', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
}

.header p {
    color: var(--rh-gray-300);
    font-size: 0.9rem;
    margin-top: 0.25rem;
}
.container {
    width: 100%;
    max-width: 640px;
    padding: 2rem;
}

.card {
    background: var(--rh-gray-800);
    border: 1px solid var(--rh-gray-700);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 1.5rem;
}

.card h2 {
    font-family: 'Red Hat Display', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--rh-gray-700);
}

.file-group {
    margin-bottom: 1.25rem;
}

.file-group label {
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 0.4rem;
    color: var(--rh-gray-300);
}
.file-group .required {
    color: var(--rh-red);
    margin-left: 2px;
}

.file-group .hint {
    font-size: 0.75rem;
    color: var(--rh-gray-600);
    margin-top: 0.25rem;
}

input[type="file"] {
    width: 100%;
    padding: 0.6rem;
    background: var(--rh-gray-700);
    border: 1px dashed var(--rh-gray-600);
    border-radius: 8px;
    color: var(--rh-gray-300);
    font-size: 0.85rem;
    cursor: pointer;
}

input[type="file"]:hover {
    border-color: var(--rh-red);
    background: var(--rh-gray-600);
}

.submit-btn {
    width: 100%;
    padding: 0.9rem;
    background: var(--rh-red);
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Red Hat Display', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
    margin-top: 0.5rem;
}
.submit-btn:hover {
    background: var(--rh-red-dark);
}

.submit-btn:disabled {
    background: var(--rh-gray-600);
    cursor: not-allowed;
}

.flash-msg {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
}

.flash-error {
    background: rgba(238,0,0,0.15);
    border: 1px solid var(--rh-red);
    color: #FF5C5C;
}

.flash-success {
    background: rgba(62,134,53,0.15);
    border: 1px solid #3E8635;
    color: #95D58F;
}

.footer {
    margin-top: auto;
    padding: 1.5rem;
    text-align: center;
    font-size: 0.75rem;
    color: var(--rh-gray-600);
}
</style>
</head>
<body>
<div class="header">
    <h1>&#9654; OCP Sizing Calculator</h1>
    <p>Upload Kubernetes cluster data &middot; Get OpenShift migration recommendations</p>
</div>

<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        {% for category, message in messages %}
        <div class="flash-msg flash-{{ category }}">{{ message }}</div>
        {% endfor %}
    {% endif %}
    {% endwith %}

    <form method="POST" enctype="multipart/form-data" action="/generate">
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

        <button type="submit" class="submit-btn" id="submitBtn">
            &#128202; Generate Sizing Report
        </button>
    </form>
</div>

<div class="footer">
    OCP Sizing Calculator v2.2 &middot; Powered by Python
</div>

<script>
document.querySelector('form').addEventListener('submit', function() {
    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Generating report...';
});
</script>
</body>
</html>
'''


@app.route('/', methods=['GET'])
def index():
    """Render the upload form."""
    return render_template_string(UPLOAD_TEMPLATE)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for OpenShift probes."""
    return {'status': 'ok'}, 200


@app.route('/generate', methods=['POST'])
def generate():
    """Process uploaded files and return the HTML report."""
    # Validate required files
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
        # Read file contents
        describe_content = describe_file.read().decode('utf-8', errors='replace')
        top_content = top_file.read().decode('utf-8', errors='replace')

        # Basic validation
        if 'Name:' not in describe_content or 'Capacity:' not in describe_content:
            flash('The "describe nodes" file does not appear to contain valid kubectl describe nodes output.', 'error')
            return redirect(url_for('index'))

        if len(top_content.strip().splitlines()) < 2:
            flash('The "top nodes" file appears to be empty or invalid.', 'error')
            return redirect(url_for('index'))

        # Parse PVs if provided
        pvs = []
        if pvs_file and pvs_file.filename != '':
            pv_content = pvs_file.read().decode('utf-8', errors='replace')
            pvs = parse_pvs(pv_content)

        # Step 1: Parse data
        nodes = parse_describe_nodes(describe_content)
        if not nodes:
            flash('No nodes could be parsed from the describe file. Check the file format.', 'error')
            return redirect(url_for('index'))

        top_data = parse_top_nodes(top_content)

        # Step 2: Analyze
        analyzer = ClusterAnalyzer(nodes, pvs)
        analyzer.merge_metrics(top_data)
        summary = analyzer.calculate_summary()

        # Step 3: Recommendations
        rec_engine = RecommendationEngine(nodes, summary)
        recommendations = rec_engine.generate_recommendations()

        # Step 4: Generate HTML report
        html = generate_html_report(nodes, summary, recommendations, pvs)

        # Write to temp file and send as download
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.html',
            prefix='ocp_sizing_report_',
            dir=tempfile.gettempdir()
        )
        tmp.write(html.encode('utf-8'))
        tmp.close()

        return send_file(
            tmp.name,
            mimetype='text/html',
            as_attachment=True,
            download_name=f'ocp_sizing_report_{datetime.now().strftime("%Y%m%d_%H%M")}.html'
        )

    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'false').lower() == 'true')
