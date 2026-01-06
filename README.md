# OCP Sizing Calculator

Kubernetes to OpenShift Migration Assessment Tool - Analyzes vanilla Kubernetes clusters and generates OpenShift sizing recommendations.

## Features

- **Cluster Architecture Visualization** - Hierarchical diagram showing node roles
- **Node Inventory** - Detailed view with CPU/Memory/Pods per node
- **Efficiency Analysis** - Compare requested vs actual resource usage
- **Workload Distribution** - Pod distribution across namespaces and nodes
- **OCP Recommendations** - Sizing recommendations for Control Plane, Infra, Storage, and Workers
- **Migration Checklist** - Pre-migration compatibility checks
- **Persistent Volumes** - Storage analysis (optional)

## Requirements

- Python 3.8+
- No external dependencies (uses only standard library)

## Data Collection

Run these commands on your Kubernetes cluster:

```bash
# REQUIRED
kubectl describe nodes > cluster-nodes.txt
kubectl top nodes > cluster-top.txt

# OPTIONAL (for storage analysis)
kubectl get pv -o wide > cluster-pv.txt
```

## Usage

```bash
# Basic usage (without PVs)
python3 ocp_sizing_calculator.py \
  -d cluster-nodes.txt \
  -t cluster-top.txt

# With PV analysis
python3 ocp_sizing_calculator.py \
  -d cluster-nodes.txt \
  -t cluster-top.txt \
  -p cluster-pv.txt \
  -o my_report.html
```

## Output

Generates an interactive HTML report with:
- Red Hat branded dark theme
- Interactive charts (Chart.js)
- Sortable/filterable tables
- CSV export functionality
- Role-based filtering

## Report Tabs

| Tab | Description |
|-----|-------------|
| Overview | Cluster architecture diagram, summary cards, resource charts |
| Node Inventory | Detailed node table with CPU/Memory requested vs actual |
| Efficiency Analysis | Over-provisioning metrics, per-node efficiency |
| Workload Distribution | Pods by namespace, pods per node |
| OCP Recommendations | Sizing recommendations per role |
| Migration Checklist | Compatibility checks and pre-migration tasks |
| Persistent Volumes | PV details (if data provided) |

## Supported Cluster Configurations

- Single Node clusters (SNO)
- 3-node compact clusters
- Full HA clusters with dedicated infra/storage nodes
- Large multi-worker clusters

## Author

Red Hat Solution Architecture

## Version

1.1.0
