# OCP Sizing Calculator - Modular Architecture

Professional tool for analyzing Kubernetes clusters and generating OpenShift migration sizing recommendations.

## Architecture

**✅ COMPLIANT** with modular/microservice principles.

```
ocp-sizing-modular/
├── generate_report.py          # Main orchestrator
├── analyzers/                   # Business logic
│   ├── cluster_analyzer.py     # Node categorization, summary calculation
│   ├── recommendation_engine.py # OCP sizing recommendations
│   └── data_models.py          # Data classes (NodeData, ClusterSummary, etc.)
├── parsers/                     # Input processing
│   ├── nodes_parser.py         # kubectl describe nodes
│   ├── metrics_parser.py       # kubectl top nodes
│   ├── storage_parser.py       # kubectl get pv
│   └── utils.py                # Parsing helpers (CPU, memory, etc.)
└── reporters/                   # Output generation
    ├── html_reporter.py        # Interactive HTML dashboard (2,380 lines)
    └── pdf_exporter.py         # PDF export via Playwright (130 lines)
```

## Modularization Changes

### Before (v1.1 - MONOLITHIC)
- `ocp_sizing_calculator_v1.1.py`: **3,195 lines**
  - Data classes (duplicated)
  - Parsing functions (duplicated)
  - Analysis logic
  - 2,350 lines of HTML generation
  - Main function
  - **Result**: Unmaintainable, violates Single Responsibility Principle

### After (v1.2 - MODULAR)
- `generate_report.py`: **~200 lines** - Orchestration only
- `analyzers/`: **~400 lines** - Pure business logic
- `parsers/`: **~500 lines** - Input handling
- `reporters/html_reporter.py`: **2,380 lines** - Isolated HTML generation
- **Result**: Clean separation of concerns, testable, maintainable

## Usage

```bash
# Generate HTML report
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -p pvs.txt

# Generate HTML + PDF report
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -p pvs.txt --pdf

# With custom output
python3 generate_report.py -d describe.txt -t top.txt -o my_report.html
```

## PDF Export

The tool can export reports to PDF format using Playwright headless browser:

```bash
# First-time setup (one-time only)
pip install playwright
playwright install chromium

# Generate PDF
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt --pdf
```

**Benefits:**
- ✅ Preserves all Chart.js visualizations as vector graphics
- ✅ Maintains full styling and layout
- ✅ Print-ready quality
- ✅ ~80 lines of code using browser print engine

## Benefits of Modular Design

1. **Single Responsibility**: Each module has one clear purpose
2. **Testability**: Can unit test parsers/analyzers independently
3. **Maintainability**: HTML changes don't affect parsing logic
4. **Reusability**: Parsers/analyzers can be used by other tools
5. **Scalability**: Easy to add new report formats (JSON, PDF, etc.)

## Web Interface

The tool includes a web UI for easy access — upload your files and download the report from a browser.

```bash
# Run locally
pip install flask gunicorn
python3 app.py

# Deploy on OpenShift (binary build)
oc new-project ocp-sizing
oc new-build --strategy=docker --binary --name=ocp-sizing-calculator
oc start-build ocp-sizing-calculator --from-dir=. --follow
oc new-app ocp-sizing-calculator
oc create route edge ocp-sizing-calculator --service=ocp-sizing-calculator --port=8080
```
