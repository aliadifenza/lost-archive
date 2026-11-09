"""Build report.pdf from report.md (python-markdown + Chromium via Playwright).
    python3 build_pdf.py
"""
import os, markdown
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
md = open(os.path.join(HERE, "report.md"), encoding="utf-8").read()
body = markdown.markdown(md, extensions=["tables", "attr_list", "md_in_html", "fenced_code"])
css = """
@page { size: A4; margin: 18mm 18mm 18mm 18mm; }
body { font-family: 'Bitstream Charter', 'Liberation Serif', serif; font-size: 10.2pt; line-height: 1.38; color: #111; }
h1 { font-family: Inter, 'Liberation Sans', sans-serif; font-size: 17pt; line-height: 1.2; text-align: center; margin: 0 0 6pt; font-weight: 700; }
.authors { text-align: center; font-size: 10.5pt; margin-bottom: 10pt; }
h2 { font-family: Inter, 'Liberation Sans', sans-serif; font-size: 12pt; margin: 12pt 0 4pt; font-weight: 700; }
h3 { font-family: Inter, 'Liberation Sans', sans-serif; font-size: 10.5pt; margin: 8pt 0 3pt; font-weight: 700; }
p { margin: 0 0 6pt; text-align: justify; hyphens: auto; }
ol, ul { margin: 0 0 6pt 16pt; padding: 0; } li { margin: 0 0 2pt; }
table { border-collapse: collapse; width: 100%; font-family: Inter, 'Liberation Sans', sans-serif; font-size: 7.9pt; line-height: 1.3; margin: 3pt 0 8pt; page-break-inside: avoid; }
th, td { border-top: 0.5pt solid #999; border-bottom: 0.5pt solid #999; padding: 2.5pt 4pt; text-align: left; vertical-align: top; }
th { background: #f1f3f2; font-weight: 600; }
img { display: block; margin: 4pt auto 2pt; max-width: 82%; }
em { font-style: italic; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.4pt; }
.pagebreak { page-break-before: always; }
h2, h3 { page-break-after: avoid; break-after: avoid; }
figure { margin: 4pt 0 8pt; page-break-inside: avoid; break-inside: avoid; }
figcaption { font-style: italic; font-size: 9.2pt; text-align: justify; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.8pt; background: #f4f5f4; padding: 5pt 7pt; white-space: pre-wrap; page-break-inside: avoid; }
p:has(+ table) { page-break-after: avoid; break-after: avoid; }
h2 + p em:only-child { }
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><title>The Lost Archive</title><style>{css}</style></head><body>{body}</body></html>"
out_html = os.path.join(HERE, "report.html")
open(out_html, "w", encoding="utf-8").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("file://" + out_html); pg.wait_for_load_state("networkidle")
    pg.pdf(path=os.path.join(HERE, "report.pdf"), format="A4", print_background=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#666'><span class='pageNumber'></span> / <span class='totalPages'></span></div>",
           margin={"top": "16mm", "bottom": "18mm", "left": "18mm", "right": "18mm"})
    b.close()
print("built", os.path.join(HERE, "report.pdf"))
