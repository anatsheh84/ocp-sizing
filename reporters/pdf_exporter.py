"""
pdf_exporter.py
---------------
PDF export functionality for OCP Sizing Calculator.

Uses Playwright/Chromium to screenshot each tab and compile into PDF.
This approach is future-proof and layout-agnostic.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
import tempfile


def export_to_pdf(html_file: str, pdf_file: Optional[str] = None, 
                  wait_time: int = 3000) -> str:
    """
    Export HTML report to PDF using tab screenshots.
    
    Takes a screenshot of each tab and compiles them into a single PDF.
    This approach ensures pixel-perfect output regardless of CSS complexity.
    
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
    
    print(f"\n📄 Generating PDF export (screenshot mode)...")
    print(f"   Source: {html_path.name}")
    print(f"   Target: {pdf_path.name}")
    
    # Create temporary directory for screenshots
    temp_dir = tempfile.mkdtemp(prefix='ocp_pdf_')
    screenshot_files = []
    
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            
            # Create page with A3 landscape viewport
            # A3 landscape: 420mm × 297mm = 4961px × 3508px at 300 DPI
            page = browser.new_page(viewport={'width': 1920, 'height': 1357})
            
            # Load HTML file
            file_url = f'file://{html_path}'
            page.goto(file_url, wait_until='networkidle')
            
            # Wait for initial charts to render
            page.wait_for_timeout(wait_time)
            
            print(f"   Capturing tabs...")
            
            # Get all tab buttons
            tab_buttons = page.query_selector_all('.nav-tab')
            tab_count = len(tab_buttons)
            
            print(f"   Found {tab_count} tabs to capture")
            
            # Screenshot each tab
            for i, tab_button in enumerate(tab_buttons):
                tab_name = tab_button.inner_text().strip()
                print(f"   [{i+1}/{tab_count}] Capturing: {tab_name}")
                
                # Click tab to activate it
                tab_button.click()
                
                # Wait for tab content to be visible and charts to render
                page.wait_for_timeout(1500)
                
                # Get the active tab content
                active_tab = page.query_selector('.tab-content.active')
                
                if active_tab:
                    # Screenshot the active tab content
                    screenshot_path = os.path.join(temp_dir, f'tab_{i:02d}.png')
                    active_tab.screenshot(path=screenshot_path)
                    screenshot_files.append(screenshot_path)
            
            browser.close()
        
        # Now compile screenshots into PDF
        print(f"   Compiling {len(screenshot_files)} screenshots into PDF...")
        _compile_images_to_pdf(screenshot_files, pdf_path)
        
        # Verify output
        if pdf_path.exists():
            file_size = pdf_path.stat().st_size / 1024
            print(f"   ✓ PDF generated: {file_size:.1f} KB")
            print(f"   ✓ Total pages: {len(screenshot_files)}")
            return str(pdf_path)
        else:
            raise RuntimeError("PDF generation failed - file not created")
            
    except Exception as e:
        print(f"   ✗ PDF generation failed: {e}", file=sys.stderr)
        raise
    
    finally:
        # Cleanup temporary files
        for screenshot_file in screenshot_files:
            try:
                os.remove(screenshot_file)
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass


def _compile_images_to_pdf(image_files: List[str], output_pdf: str):
    """
    Compile a list of image files into a single PDF.
    
    Args:
        image_files: List of image file paths (in order)
        output_pdf: Output PDF file path
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "Pillow is required for PDF compilation.\n"
            "Install with: pip install Pillow"
        )
    
    if not image_files:
        raise ValueError("No images to compile")
    
    # Open all images
    images = []
    for img_path in image_files:
        img = Image.open(img_path)
        # Convert to RGB if needed (PDF requires RGB)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        images.append(img)
    
    # Save first image as PDF, append rest
    if len(images) == 1:
        images[0].save(output_pdf, 'PDF', resolution=100.0)
    else:
        images[0].save(
            output_pdf,
            'PDF',
            resolution=100.0,
            save_all=True,
            append_images=images[1:]
        )
    
    # Close all images
    for img in images:
        img.close()


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


def check_pillow_installed() -> bool:
    """
    Check if Pillow is installed.
    
    Returns:
        True if Pillow is available, False otherwise
    """
    try:
        import PIL
        return True
    except ImportError:
        return False


def print_installation_instructions():
    """Print instructions for installing required dependencies."""
    print("\n" + "=" * 80)
    print("PDF Export Setup Required")
    print("=" * 80)
    print("\nTo enable PDF export, install required dependencies:")
    print("\n  1. Install Playwright:")
    print("     pip install playwright")
    print("\n  2. Install Chromium browser:")
    print("     playwright install chromium")
    print("\n  3. Install Pillow (for PDF compilation):")
    print("     pip install Pillow")
    print("\n  4. Re-run with --pdf flag")
    print("\n" + "=" * 80 + "\n")
