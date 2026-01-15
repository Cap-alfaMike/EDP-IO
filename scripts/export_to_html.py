"""
Convert markdown files to HTML for PDF export.
Open the HTML files in a browser and use Print > Save as PDF.
"""

import markdown
from pathlib import Path

# Source files
files = [
    ("task.md", "Task"),
    ("implementation_plan.md", "Implementation Plan"),
    ("walkthrough.md", "Walkthrough"),
]

# Artifact directory
artifact_dir = Path(r"C:\Users\tonim\.gemini\antigravity\brain\e9d2f7bb-06cf-4c1c-a2bd-e655ddb5c014")
readme_path = Path(r"d:\EDP-IO\README.md")
output_dir = Path(r"d:\EDP-IO\docs\exports")
output_dir.mkdir(parents=True, exist_ok=True)

# HTML template with styling
html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title} - EDP-IO</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #1e3a5f; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #2c5282; margin-top: 30px; }}
        h3 {{ color: #4a5568; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #1e3a5f; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        code {{ 
            background-color: #f4f4f4; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-family: 'Consolas', monospace;
        }}
        pre {{ 
            background-color: #2d3748; 
            color: #e2e8f0; 
            padding: 20px; 
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{ background: none; color: inherit; }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 20px 0;
            padding: 10px 20px;
            background-color: #f0f7ff;
        }}
        .mermaid-placeholder {{
            background: #f0f0f0;
            border: 2px dashed #999;
            padding: 20px;
            text-align: center;
            color: #666;
            margin: 20px 0;
        }}
        @media print {{
            body {{ padding: 20px; }}
            pre {{ white-space: pre-wrap; }}
        }}
    </style>
</head>
<body>
{content}
<footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 0.9em;">
    <p>EDP-IO - Enterprise Data Platform with Intelligent Observability</p>
    <p>Generated for documentation purposes</p>
</footer>
</body>
</html>
"""

def convert_mermaid_blocks(html_content):
    """Replace mermaid code blocks with placeholders."""
    import re
    pattern = r'<pre><code class="language-mermaid">(.*?)</code></pre>'
    replacement = '<div class="mermaid-placeholder">[Mermaid Diagram - View in GitHub/VS Code]</div>'
    return re.sub(pattern, replacement, html_content, flags=re.DOTALL)

def convert_to_html(md_content, title):
    """Convert markdown to styled HTML."""
    # Convert markdown to HTML
    html = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite', 'toc']
    )
    
    # Handle mermaid blocks
    html = convert_mermaid_blocks(html)
    
    return html_template.format(title=title, content=html)

# Process artifact files
for filename, title in files:
    source_path = artifact_dir / filename
    if source_path.exists():
        with open(source_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html_content = convert_to_html(md_content, title)
        
        output_path = output_dir / f"{filename.replace('.md', '.html')}"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Created: {output_path}")

# Process README
if readme_path.exists():
    with open(readme_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html_content = convert_to_html(md_content, "README")
    
    output_path = output_dir / "README.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created: {output_path}")

print(f"\n📁 All files saved to: {output_dir}")
print("\n📄 To create PDFs:")
print("   1. Open each .html file in Chrome/Edge")
print("   2. Press Ctrl+P (Print)")
print("   3. Select 'Save as PDF'")
print("   4. Save to desired location")
