# OCP Sizing Calculator

Analyze Kubernetes and OpenShift clusters to generate interactive sizing reports with migration recommendations.

Upload three simple command outputs, get a comprehensive HTML dashboard with resource utilization charts, efficiency analysis, and OpenShift node sizing recommendations.

## Collecting Cluster Data

Run these commands against your source cluster to generate the input files.

**On Kubernetes:**

```bash
kubectl describe nodes > nodes_describe.txt
kubectl top nodes > nodes_top.txt
kubectl get pv -o wide > pvs.txt          # optional
```

**On OpenShift:**

```bash
oc describe nodes > nodes_describe.txt
oc adm top nodes > nodes_top.txt
oc get pv -o wide > pvs.txt               # optional
```

> **Note:** The `top nodes` command requires the metrics-server to be running.
> The PV file is optional — the report will generate without it.

## Web Interface

The tool provides a web UI where users can upload cluster data files, name their reports, and download the generated HTML dashboards. Multiple reports persist in the session and can be downloaded or printed to PDF at any time.

### Run Locally with Podman

```bash
# Build the image
podman build -t ocp-sizing-calculator .

# Run the container
podman run -p 8080:8080 ocp-sizing-calculator
```

Open http://localhost:8080 in your browser.

### Run Locally with Python

```bash
pip install flask gunicorn
python3 app.py
```

Open http://localhost:8080 in your browser.

### Deploy on OpenShift

**Option A — Binary build from local directory (recommended for development):**

```bash
oc new-project ocp-sizing
oc new-build --strategy=docker --binary --name=ocp-sizing-calculator
oc start-build ocp-sizing-calculator --from-dir=. --follow
oc new-app ocp-sizing-calculator
oc create route edge ocp-sizing-calculator --service=ocp-sizing-calculator --port=8080
```

**Option B — Build from Git repository:**

```bash
oc new-project ocp-sizing
oc apply -f openshift/buildconfig.yaml
oc apply -f openshift/deployment.yaml
oc apply -f openshift/service-route.yaml
oc start-build ocp-sizing-calculator --follow
```

**Rebuild after code changes:**

```bash
oc start-build ocp-sizing-calculator --from-dir=. --follow
```

The build uploads the local directory, builds the container image on-cluster, pushes it to the internal registry, and triggers a rolling deployment automatically.

## CLI Usage

The tool can also be used directly from the command line without the web interface:

```bash
# Generate HTML report
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -p pvs.txt

# Custom output filename
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -o my_report.html

# With PDF export (requires playwright and Pillow)
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt --pdf
```

## Architecture

```
ocp-sizing-modular/
├── app.py                       # Flask web interface
├── generate_report.py           # CLI orchestrator
├── Dockerfile                   # Container image (Python 3.12, gunicorn)
├── models/
│   └── __init__.py              # Data classes (NodeData, ClusterSummary, etc.)
├── parsers/
│   ├── nodes_parser.py          # Parse kubectl describe nodes
│   ├── metrics_parser.py        # Parse kubectl top nodes
│   ├── storage_parser.py        # Parse kubectl get pv
│   └── utils.py                 # Unit conversion helpers
├── analyzers/
│   ├── cluster_analyzer.py      # Node categorization, resource aggregation
│   └── recommendation_engine.py # OCP sizing recommendations
├── reporters/
│   ├── html_reporter.py         # Interactive HTML dashboard
│   └── pdf_exporter.py          # PDF export via Playwright (CLI only)
└── openshift/                   # OpenShift deployment manifests
    ├── buildconfig.yaml
    ├── deployment.yaml
    └── service-route.yaml
```

## License

MIT
