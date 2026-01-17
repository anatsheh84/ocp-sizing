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
    └── html_reporter.py        # Interactive HTML dashboard (2,380 lines)
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
# Generate report
python3 generate_report.py -d nodes_describe.txt -t nodes_top.txt -p pvs.txt

# With custom output
python3 generate_report.py -d describe.txt -t top.txt -o my_report.html
```

## Benefits of Modular Design

1. **Single Responsibility**: Each module has one clear purpose
2. **Testability**: Can unit test parsers/analyzers independently
3. **Maintainability**: HTML changes don't affect parsing logic
4. **Reusability**: Parsers/analyzers can be used by other tools
5. **Scalability**: Easy to add new report formats (JSON, PDF, etc.)

## Migration from v1.1

The old monolithic file is preserved as `ocp_sizing_calculator_v1.1.py.OLD`.
A compatibility wrapper exists at `ocp_sizing_calculator.py` that forwards to `generate_report.py`.

No changes needed to inputs/outputs - all functionality preserved.
