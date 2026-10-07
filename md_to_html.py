"""
Convertit un Markdown en HTML autonome (single-file).
Style ambre/orange sur fond sombre, inspire de qFlipper.

Usage :
  py -3.9 md_to_html.py <source.md> <dest.html> [--title "Titre custom"] [--device "ID"] [--version "v1.0"]

Si appele sans args, utilise GUIDE-UTILISATEUR.md / GUIDE-UTILISATEUR.html par defaut.
"""
import re
import sys
import argparse
from pathlib import Path
import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from pygments.formatters import HtmlFormatter

HERE = Path(__file__).parent


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("src", nargs="?", default=str(HERE / "GUIDE-UTILISATEUR.md"))
    p.add_argument("dst", nargs="?", default=str(HERE / "GUIDE-UTILISATEUR.html"))
    p.add_argument("--title", default=None, help="Titre de page (sinon : H1 du MD)")
    p.add_argument("--device", default="FLIPPER ZERO · mntm-012", help="Texte de la barre du haut")
    p.add_argument("--version", default="Bridge v2", help="Sous-titre sidebar")
    p.add_argument("--logo", default="Flipper Bridge", help="Logo sidebar")
    return p.parse_args()


def build(src_path, dst_path, page_title_override, device_text, version_text, logo_text):
    src_path = Path(src_path)
    dst_path = Path(dst_path)
    md_text = src_path.read_text(encoding="utf-8")

    md = markdown.Markdown(
        extensions=[
            TocExtension(toc_depth="2-3", permalink="¶", title="Sommaire"),
            CodeHiliteExtension(linenums=False, guess_lang=True, css_class="codehilite"),
            "tables",
            "fenced_code",
            "sane_lists",
            "attr_list",
            "footnotes",
            "smarty",
        ],
    )
    body = md.convert(md_text)
    toc = md.toc

    pygments_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite")

    m = re.match(r"^#\s+(.+?)$", md_text, re.MULTILINE)
    page_title = page_title_override or (m.group(1).strip() if m else "Guide")

    CSS = """
:root {
  --bg: #0d0d0d;
  --bg-panel: #161616;
  --bg-elev: #1f1f1f;
  --border: #2a2a2a;
  --border-strong: #3a3a3a;
  --text: #e8e8e8;
  --text-dim: #a0a0a0;
  --text-faint: #707070;
  --accent: #ff8200;
  --accent-dim: #cc6800;
  --accent-glow: rgba(255, 130, 0, 0.15);
  --success: #4ade80;
  --warn: #fbbf24;
  --danger: #f87171;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
.layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 0;
  min-height: 100vh;
}
.sidebar {
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
  padding: 28px 20px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  font-size: 13.5px;
}
.sidebar-logo {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 15px;
  letter-spacing: 0.5px;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.sidebar-sub {
  color: var(--text-faint);
  font-size: 12px;
  margin-bottom: 22px;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
}
.toc { padding: 0; }
.toc > ul { list-style: none; padding-left: 0; margin: 0; }
.toc ul { list-style: none; padding-left: 14px; margin: 4px 0; border-left: 1px solid var(--border); }
.toc li { margin: 5px 0; }
.toc a {
  color: var(--text-dim);
  text-decoration: none;
  display: block;
  padding: 3px 8px;
  border-radius: 3px;
  transition: all 0.15s;
  border-left: 2px solid transparent;
  margin-left: -8px;
}
.toc a:hover { color: var(--accent); background: var(--accent-glow); border-left-color: var(--accent); }
.toc > ul > li > a { color: var(--text); font-weight: 600; font-size: 14px; margin-top: 8px; }
.content { padding: 48px 56px 80px; max-width: 920px; margin: 0 auto; }
h1, h2, h3, h4, h5, h6 { font-family: 'Inter', system-ui, sans-serif; line-height: 1.3; }
h1 {
  font-size: 32px; font-weight: 800; color: var(--accent);
  letter-spacing: -0.5px; margin: 0 0 6px;
  padding-bottom: 16px; border-bottom: 2px solid var(--accent);
}
h2 {
  font-size: 24px; font-weight: 700; color: var(--accent);
  margin-top: 56px; margin-bottom: 14px;
  padding-bottom: 6px; border-bottom: 1px solid var(--border-strong);
}
h3 {
  font-size: 19px; font-weight: 600; color: var(--text);
  margin-top: 32px; margin-bottom: 10px;
}
h3::before { content: '▸ '; color: var(--accent); }
h4 { font-size: 16px; color: var(--text); margin-top: 22px; margin-bottom: 8px; }
h2 .headerlink, h3 .headerlink, h4 .headerlink {
  margin-left: 8px; color: var(--accent-dim); text-decoration: none;
  opacity: 0; transition: opacity 0.15s; font-weight: 400;
}
h2:hover .headerlink, h3:hover .headerlink, h4:hover .headerlink { opacity: 1; }
p { margin: 12px 0; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.15s; }
a:hover { border-bottom-color: var(--accent); }
strong { color: #fff; font-weight: 700; }
em { color: var(--text-dim); font-style: italic; }
ul, ol { padding-left: 24px; margin: 12px 0; }
li { margin: 6px 0; }
hr { border: none; border-top: 1px solid var(--border-strong); margin: 40px 0; }
code {
  font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
  font-size: 13px; background: var(--bg-elev); color: var(--accent);
  padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border);
}
pre {
  background: #1a1a1a; border: 1px solid var(--border-strong);
  border-left: 3px solid var(--accent); border-radius: 4px;
  padding: 16px 20px; overflow-x: auto; margin: 16px 0;
  font-size: 13px; line-height: 1.5;
}
pre code { background: transparent; border: none; padding: 0; color: var(--text); font-size: 13px; }
.codehilite { background: transparent !important; }
.codehilite pre { margin: 0; }
table {
  border-collapse: collapse; width: 100%; margin: 20px 0;
  font-size: 14px; background: var(--bg-panel); border-radius: 4px;
  overflow: hidden; border: 1px solid var(--border-strong);
}
thead { background: #221409; }
th {
  text-align: left; padding: 10px 14px; color: var(--accent);
  font-weight: 600; border-bottom: 1px solid var(--accent-dim);
  font-size: 13px; text-transform: uppercase; letter-spacing: 0.3px;
}
td { padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: rgba(255, 130, 0, 0.04); }
blockquote {
  border-left: 3px solid var(--accent); background: var(--accent-glow);
  margin: 16px 0; padding: 12px 20px; border-radius: 0 4px 4px 0;
  color: var(--text-dim);
}
blockquote p { margin: 4px 0; }
blockquote strong { color: var(--accent); }
.topbar {
  position: sticky; top: 0; z-index: 10;
  background: rgba(13, 13, 13, 0.92); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border); padding: 10px 56px;
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text-faint);
}
.topbar .device { color: var(--accent); letter-spacing: 0.5px; }
.topbar .status { display: inline-flex; align-items: center; gap: 6px; }
.topbar .status::before {
  content: ''; width: 8px; height: 8px;
  background: var(--success); border-radius: 50%;
  box-shadow: 0 0 8px var(--success);
}
footer {
  margin-top: 80px; padding-top: 24px; border-top: 1px solid var(--border);
  color: var(--text-faint); font-size: 12.5px; text-align: center;
}
@media print {
  .sidebar, .topbar { display: none; }
  .layout { display: block; }
  .content { padding: 0; max-width: none; }
  body { background: #fff; color: #000; font-size: 11pt; }
  h1, h2, h3 { color: #c25800; }
  a { color: #c25800; }
  pre, code, table { color: #000; background: #f4f4f4; border-color: #ccc; }
  blockquote { background: #fff8ec; }
}
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: relative; height: auto; }
  .content { padding: 24px 18px 60px; }
  .topbar { padding: 10px 18px; }
  h1 { font-size: 26px; }
  h2 { font-size: 21px; margin-top: 40px; }
  table { font-size: 13px; }
  th, td { padding: 8px 10px; }
}
""" + pygments_css

    HTML = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="topbar">
  <span class="device">{device_text}</span>
  <span class="status">READY</span>
</div>
<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-logo">{logo_text}</div>
    <div class="sidebar-sub">{version_text}</div>
    {toc}
  </aside>
  <main class="content">
    {body}
    <footer>
      Document généré · Style inspiré de qFlipper · HTML/CSS vanilla, single-file.
    </footer>
  </main>
</div>
</body>
</html>
"""
    dst_path.write_text(HTML, encoding="utf-8")
    return dst_path.stat().st_size


if __name__ == "__main__":
    args = parse_args()
    size = build(args.src, args.dst, args.title, args.device, args.version, args.logo)
    print(f"OK : {args.dst}")
    print(f"Taille : {size / 1024:.1f} KB")
