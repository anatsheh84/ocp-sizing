"""
pdf_exporter.py
---------------
PDF export functionality for OCP Sizing Calculator.

Uses Playwright/Chromium to render HTML report and export as PDF.
This preserves all Chart.js visualizations and styling.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def export_to_pdf(html_file: str, pdf_file: Optional[str] = None, 
                  wait_time: int = 3000) -> str:
    """
    Export HTML report to PDF using headless browser.
    
    Args:
        html_file: Path to HTML file to convert
        pdf_file: Output PDF path (optional, defaults to same name with .pdf)
        wait_time: Milliseconds to wait for charts to render (default: 3000)
        
    Returns:
        Path to generated PDF file
        
    Raises:
        ImportError: If playwright is not installed
        FileNotFoundError: If HTML file doesn't exist
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright is required for PDF export.\n"
            "Install with: pip install playwright && playwright install chromium"
        )
    
    # Validate input file
    html_path = Path(html_file).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")
    
    # Determine output file
    if pdf_file is None:
        pdf_file = str(html_path.with_suffix('.pdf'))
    
    pdf_path = Path(pdf_file).resolve()
    
    print(f"\n📄 Generating PDF export...")
    print(f"   Source: {html_path.name}")
    print(f"   Target: {pdf_path.name}")
    
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Load HTML file
            file_url = f'file://{html_path}'
            page.goto(file_url, wait_until='networkidle')
            
            # Wait for JavaScript charts to render
            page.wait_for_timeout(wait_time)
            
            # Inject CSS to show all tabs for PDF export
            print(f"   Preparing content for PDF...")
            page.evaluate("""
                () => {
                    // Make all tab content visible for PDF
                    const tabContents = document.querySelectorAll('.tab-content');
                    tabContents.forEach(content => {
                        content.style.display = 'block';
                        content.style.pageBreakBefore = 'always';
                    });
                    
                    // Hide tab navigation in PDF
                    const tabNav = document.querySelector('.tab-nav');
                    if (tabNav) {
                        tabNav.style.display = 'none';
                    }
                    
                    // Add print-specific styling
                    const style = document.createElement('style');
                    style.textContent = `
                        @media print {
                            .tab-content {
                                display: block !important;
                                page-break-before: always;
                            }
                            .tab-nav {
                                display: none !important;
                            }
                            body {
                                background: white !important;
                            }
                        }
                    `;
                    document.head.appendChild(style);
                }
            """)
            
            # Wait a bit for the changes to take effect
            page.wait_for_timeout(1000)
            
            # Generate PDF with print settings (landscape for tables)
            print(f"   Generating PDF (A3 landscape)...")
            page.pdf(
                path=str(pdf_path),
                format='A3',
                landscape=True,  # Landscape for better table visibility
                print_background=True,
                margin={
                    'top': '0.25in',
                    'right': '0.25in',
                    'bottom': '0.25in',
                    'left': '0.25in'
                },
                display_header_footer=False,
                prefer_css_page_size=False
            )
            
            browser.close()
        
        # Verify output
        if pdf_path.exists():
            file_size = pdf_path.stat().st_size / 1024
            print(f"   ✓ PDF generated: {file_size:.1f} KB")
            
            # Get page count for feedback
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    page_count = len(pdf_reader.pages)
                    print(f"   ✓ Total pages: {page_count}")
            except:
                pass  # PyPDF2 not available, skip page count
            
            return str(pdf_path)
        else:
            raise RuntimeError("PDF generation failed - file not created")
            
    except Exception as e:
        print(f"   ✗ PDF generation failed: {e}", file=sys.stderr)
        raise


def check_playwright_installed() -> bool:
    """
    Check if Playwright and Chromium are properly installed.
    
    Returns:
        True if Playwright is ready, False otherwise
    """
    try:
        from playwright.sync_api import sync_playwright
        
        # Try to launch browser to verify installation
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except ImportError:
        return False


def print_installation_instructions():
    """Print instructions for installing Playwright."""
    print("\n" + "=" * 80)
    print("PDF Export Setup Required")
    print("=" * 80)
    print("\nTo enable PDF export, install Playwright:")
    print("\n  1. Install Playwright:")
    print("     pip install playwright")
    print("\n  2. Install Chromium browser:")
    print("     playwright install chromium")
    print("\n  3. Re-run with --pdf flag")
    print("\n" + "=" * 80 + "\n")
