#!/usr/bin/env python3
"""
ocp_sizing_calculator.py
-----------------------
CLI wrapper for OCP Sizing Calculator (backward compatibility).

This is now just a thin wrapper around the modular generate_report.py.
All functionality has been moved to proper modules:
  - analyzers/: Cluster analysis and recommendations
  - parsers/: Input file parsing
  - reporters/: HTML report generation

For direct usage, use: python3 generate_report.py
"""

import sys
import subprocess

def main():
    """Forward all arguments to generate_report.py"""
    print("⚠️  Notice: ocp_sizing_calculator.py is deprecated")
    print("   Please use: python3 generate_report.py\n")
    
    # Forward to generate_report.py
    cmd = [sys.executable, 'generate_report.py'] + sys.argv[1:]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()
