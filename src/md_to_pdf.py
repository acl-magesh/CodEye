"""
md_to_pdf.py - Markdown to PDF/HTML Converter with Mermaid Support for CodEye

This module provides functions to convert markdown files (with mermaid diagrams) to HTML and PDF. It includes logic to detect, validate, and fix mermaid code blocks using an LLM, and renders diagrams using Playwright and mermaid.js for accurate PDF output.

Functions:
    md_to_pdf(md_path, pdf_path=None, html_path=None): Convert markdown to HTML and PDF, fixing mermaid diagrams if needed.
    _find_mermaid_blocks(md_content): Find all mermaid code blocks in markdown.
    _is_mermaid_code_invalid(code): Static check for mermaid syntax errors.
    _fix_mermaid_code_with_llm(bad_code, explicit_error=False): Use LLM to fix mermaid code.
    _inject_mermaid_html(html_content, md_content): Inject mermaid.js and CSS into HTML.
    _mermaid_block_has_error(html_content): Detect mermaid rendering errors in HTML.

Typical usage example:
    html_path, pdf_path = md_to_pdf('output.md')
"""

import os
import re
import html
from typing import Tuple
from pathlib import Path

def _find_mermaid_blocks(md_content: str):
    """
    Find all mermaid code blocks in markdown.
    Returns a list of (start, end, code) tuples.
    """
    blocks = []
    for match in re.finditer(r'```mermaid\s*([\s\S]*?)```', md_content):
        blocks.append((match.start(), match.end(), match.group(1)))
    return blocks

def _is_mermaid_code_invalid(code: str) -> bool:
    """
    Basic static check for mermaid syntax errors.
    Returns True if code is likely invalid.
    """
    # Mermaid diagrams should start with a graph type (graph TD, graph LR, flowchart TD, etc.)
    if not re.match(r'^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey)\s', code.strip()):
        return True
    # Check for unclosed brackets or parentheses
    if code.count('(') != code.count(')') or code.count('{') != code.count('}'):
        return True
    # Check for forbidden characters or empty code
    if not code.strip() or 'SYNTAX ERROR' in code.upper():
        return True
    return False

def _fix_mermaid_code_with_llm(bad_code: str, explicit_error: bool = False):
    """
    Use the LLM to fix mermaid code syntax errors.
    Returns the corrected code or the original if no fix.
    """
    import subprocess
    if explicit_error:
        prompt = (
            "The following mermaid diagram has a syntax error (missing graph type, unclosed brackets, or invalid node definitions). Please fix it and return only the corrected mermaid code.\n"
            f"```mermaid\n{bad_code}\n```"
        )
    else:
        prompt = (
            "The following mermaid diagram has a syntax error. Please fix it and return only the corrected mermaid code.\n"
            f"```mermaid\n{bad_code}\n```"
        )
    try:
        result = subprocess.run([
            "llm", "-m", "gemini-2.5-pro", "-s", "Fix mermaid syntax error"
        ], input=prompt, capture_output=True, text=True, check=False)
        fixed = result.stdout.strip()
        # Extract only the mermaid code from the output
        m = re.search(r'```mermaid\s*([\s\S]*?)```', fixed)
        if m:
            return m.group(1)
        return fixed
    except Exception:
        return bad_code

def _inject_mermaid_html(html_content: str, md_content: str) -> str:
    """
    Inject mermaid.js, a minimal GitHub-style CSS, and a script to render diagrams into the HTML content.
    Replace <pre><code class="language-mermaid">...</code></pre> (with any extra classes), <pre><code>mermaid\n...</code></pre>, or <code class="mermaid">...</code> blocks with <div class="mermaid">...</div> in-place.
    As a fallback, replace all ```mermaid code blocks in the original markdown with <div class="mermaid">...</div> before markdown2 conversion, so they appear in the correct place.
    """
    # Fallback: Replace mermaid code blocks in markdown before markdown2 conversion
    def md_mermaid_repl(match):
        code = match.group(1)
        return f'<div class="mermaid">{code}</div>'
    md_content = re.sub(r'```mermaid\s*([\s\S]*?)```', md_mermaid_repl, md_content)
    import markdown2
    html_content = markdown2.markdown(md_content, extras=["fenced-code-blocks", "tables", "code-friendly", "cuddled-lists", "metadata"])
    # In case markdown2 still outputs code blocks, replace them in-place
    def repl(match):
        code = match.group(1)
        code = html.unescape(code)
        return f'<div class="mermaid">{code}</div>'
    html_content = re.sub(
        r'<pre><code[^>]*class="[^"]*language-mermaid[^"]*"[^>]*>([\s\S]*?)</code></pre>',
        repl,
        html_content
    )
    html_content = re.sub(
        r'<pre><code>mermaid\n([\s\S]*?)</code></pre>',
        repl,
        html_content
    )
    html_content = re.sub(
        r'<code[^>]*class="[^"]*mermaid[^"]*"[^>]*>([\s\S]*?)</code>',
        repl,
        html_content
    )
    github_css = '''
    <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #fff; color: #24292e; }
    pre, code { background: #f6f8fa; border-radius: 3px; }
    pre { padding: 8px; overflow-x: auto; }
    code { padding: 2px 4px; }
    h1, h2, h3, h4, h5, h6 { font-weight: 600; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
    </style>
    '''
    mermaid_script = '''
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
    setTimeout(function() {
      if (window.mermaid) {
        mermaid.init(undefined, document.querySelectorAll('.mermaid'));
      }
    }, 500);
    </script>
    '''
    return f"<html><head>{github_css}{mermaid_script}</head><body>{html_content}</body></html>"


def _mermaid_block_has_error(html_content: str) -> bool:
    """
    Detect if the rendered HTML contains a mermaid error (e.g., missing SVG or error message).
    Returns True if error detected, False otherwise.
    """
    # Mermaid errors often result in missing <svg> inside .mermaid divs
    # Or error messages like 'Syntax error in text'
    if 'Syntax error in text' in html_content:
        return True
    # If no <svg> inside .mermaid divs, likely an error
    mermaid_divs = re.findall(r'<div class="mermaid">([\s\S]*?)</div>', html_content)
    for div in mermaid_divs:
        if '<svg' not in div:
            return True
    return False

def _log_mermaid(msg):
    import logging
    logging.info(msg)

def md_to_pdf(md_path, pdf_path=None, html_path=None) -> Tuple[str, str]:
    """
    Convert a markdown file to both HTML and PDF using Playwright (headless browser) for mermaid support.
    The HTML output will closely match the markdown, with mermaid diagrams replacing the code blocks in-place.
    """
    import markdown2
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    if pdf_path is None:
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"
    if html_path is None:
        html_path = os.path.splitext(md_path)[0] + ".html"
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        blocks = _find_mermaid_blocks(md_content)
        for start, end, code in blocks:
            _log_mermaid(f"[Mermaid] Original block:\n{code}\n---")
            fixed_code = _fix_mermaid_code_with_llm(code)
            _log_mermaid(f"[Mermaid] After first LLM fix:\n{fixed_code}\n---")
            if fixed_code != code:
                md_content = md_content[:start] + f'```mermaid\n{fixed_code}\n```' + md_content[end:]
        html_full = _inject_mermaid_html('', md_content)
        max_attempts = 3
        attempt = 1
        while (_mermaid_block_has_error(html_full) or any(_is_mermaid_code_invalid(code) for _, _, code in _find_mermaid_blocks(md_content))) and attempt <= max_attempts:
            blocks = _find_mermaid_blocks(md_content)
            for start, end, code in blocks:
                if _is_mermaid_code_invalid(code):
                    _log_mermaid(f"[Mermaid] Attempt {attempt} - Invalid block:\n{code}\n---")
                    fixed_code = _fix_mermaid_code_with_llm(code, explicit_error=True)
                    _log_mermaid(f"[Mermaid] Attempt {attempt} - After LLM fix:\n{fixed_code}\n---")
                    if fixed_code != code:
                        md_content = md_content[:start] + f'```mermaid\n{fixed_code}\n```' + md_content[end:]
            html_full = _inject_mermaid_html('', md_content)
            attempt += 1
        # If still error after all attempts, add warning to markdown
        if _mermaid_block_has_error(html_full):
            md_content += '\n\n> **Warning:** The architecture diagram could not be fixed and may not render correctly.'
            html_full = _inject_mermaid_html('', md_content)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_full)
        with open(os.path.splitext(html_path)[0] + '_debug.html', 'w', encoding='utf-8') as f:
            f.write(html_full)
        from playwright.sync_api import sync_playwright
        html_abs_path = Path(html_path).absolute().as_uri()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(html_abs_path)
            try:
                page.wait_for_selector('.mermaid svg', timeout=25000)
            except Exception:
                _log_mermaid("Warning: Mermaid SVG not detected after 25s, exporting anyway.")
            page.pdf(path=pdf_path, format="A4")
            browser.close()
    except Exception as e:
        raise RuntimeError(f"Failed to convert markdown to PDF/HTML with mermaid: {e}")
    return html_path, pdf_path
