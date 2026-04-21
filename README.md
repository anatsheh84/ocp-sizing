# OCP Sizing Calculator

Analyze Kubernetes and OpenShift clusters to generate interactive sizing reports with migration recommendations.

Upload three simple command outputs, get a comprehensive HTML dashboard with resource utilization charts, efficiency analysis, and OpenShift node sizing recommendations.

## Collecting Cluster Data

Run these commands against your source cluster to generate the input files.

**On OpenShift:**

```bash
oc describe nodes > nodes_describe.txt
oc adm top nodes > nodes_top.txt
oc get pv -o wide > pvs.txt               # optional
```

**On Kubernetes:**

```bash
kubectl describe nodes > nodes_describe.txt
kubectl top nodes > nodes_top.txt
kubectl get pv -o wide > pvs.txt          # optional
```

> **Note:** The `top nodes` command requires the metrics-server to be running.
> The PV file is optional — the report will generate without it.

## Web Interface

The tool provides a web UI where users can upload cluster data files, name their reports, and download the generated HTML dashboards. Multiple reports persist in the session and can be downloaded or printed to PDF at any time.

### Run with Podman

```bash
podman build -t ocp-sizing-calculator .
podman run -p 8080:8080 ocp-sizing-calculator
```

Open http://localhost:8080 in your browser.

### Run with Python

```bash
pip install flask gunicorn
python3 app.py
```

Open http://localhost:8080 in your browser.

### Deploy on OpenShift

**Binary build from local directory (recommended for development):**

```bash
oc new-project ocp-sizing
oc new-build --strategy=docker --binary --name=ocp-sizing-calculator
oc start-build ocp-sizing-calculator --from-dir=. --follow
oc new-app ocp-sizing-calculator
oc create route edge ocp-sizing-calculator --service=ocp-sizing-calculator --port=8080
```

**Build from Git repository:**

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

## CLI Usage

The tool can also be used directly from the command line without the web interface:

```bash
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -p pvs.txt
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -o my_report.html
```

## Architecture

```
ocp-sizing-modular/
├── app.py                            # Flask web interface
├── generate_report.py                # CLI orchestrator
├── Dockerfile                        # Container image (Python 3.12, gunicorn)
├── models/
│   └── __init__.py                   # Data classes (NodeData, ClusterSummary, …)
├── parsers/
│   ├── nodes_parser.py               # Parse kubectl describe nodes
│   ├── metrics_parser.py             # Parse kubectl top nodes
│   ├── pods_metrics_parser.py        # Parse kubectl top pods -A (optional)
│   ├── storage_parser.py             # Parse kubectl get pv
│   └── utils.py                      # Unit conversion helpers
├── analyzers/
│   ├── cluster_analyzer.py           # Node categorization, resource aggregation
│   ├── recommendation_engine.py      # OCP sizing recommendations
│   └── workload_analyzer.py          # Workload inventory + pod/namespace stats
├── reporters/
│   ├── html_reporter.py              # Orchestrator (≈90 lines)
│   ├── report_context.py             # ReportContext dataclass + build_context()
│   ├── layout.py                     # Outer HTML shell (DOCTYPE, head, nav, footer)
│   ├── styles.py                     # Static CSS
│   ├── scripts.py                    # Static JS + build_script_body()
│   ├── components.py                 # Shared UI fragments (role_filter_bar)
│   ├── pdf_exporter.py               # Optional PDF export via playwright
│   └── tabs/                         # One module per report tab
│       ├── overview.py
│       ├── nodes.py
│       ├── efficiency.py
│       ├── workloads.py
│       ├── workload_inventory.py
│       ├── recommendations.py
│       ├── checklist.py
│       └── storage.py
├── documentation/
│   ├── reporters-architecture.md     # Developer reference for reporters/
│   └── html-reporter-refactor-plan.md
└── openshift/                        # OpenShift deployment manifests
    ├── buildconfig.yaml
    ├── deployment.yaml
    └── service-route.yaml
```

For developer details on the `reporters/` module layout — call graph, tab contract,
and the "adding a new tab" recipe — see
[`documentation/reporters-architecture.md`](documentation/reporters-architecture.md).

## License

MIT
