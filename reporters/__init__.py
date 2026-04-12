"""
reporters package
-----------------
Report generation modules for OCP Sizing Calculator.
"""

from .html_reporter import generate_html_report
from .pdf_exporter import (
    export_to_pdf, 
    check_playwright_installed, 
    check_pillow_installed,
    print_installation_instructions
)

__all__ = [
    'generate_html_report',
    'export_to_pdf',
    'check_playwright_installed',
    'check_pillow_installed',
    'print_installation_instructions'
]
