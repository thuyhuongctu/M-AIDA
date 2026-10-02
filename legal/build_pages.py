"""Render legal/TERMS.md and legal/PRIVACY.md to frontend/public/legal/*.html.

The Markdown files are the source of truth (reviewed, versioned). Vite copies
frontend/public/ into the build, so the pages are served at /legal/terms.html
and /legal/privacy.html next to the application. No dependency beyond the
standard library: the subset handled is headings, paragraphs, horizontal
rules, inline code, bold, and bare URLs.

    python legal/build_pages.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "legal"

STYLE = """
:root { --ink:#1a202c; --muted:#4a5568; --line:#e2e8f0; --bg:#f7f9fc; --card:#fff; --accent:#1e3a5f; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; line-height:1.6; }
header { background:var(--accent); color:#fff; padding:1rem 2rem; }
header a { color:#fff; text-decoration:none; font-weight:700; font-size:1.2rem; }
header span { opacity:.8; font-size:.85rem; margin-left:.6rem; }
main { max-width:820px; margin:1.5rem auto 3rem; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1.5rem 2rem; }
h1 { font-size:1.5rem; margin:1.2rem 0 .4rem; line-height:1.3; }
h2 { font-size:1.05rem; margin:1.4rem 0 .3rem; color:var(--accent); }
p { margin:.5rem 0; font-size:.95rem; }
hr { border:0; border-top:1px dashed var(--line); margin:2rem 0; }
code { background:#f1f5f9; padding:.1rem .3rem; border-radius:4px; font-size:.88em; }
nav.lang { font-size:.85rem; color:var(--muted); margin:0 0 1rem; }
nav.lang a { color:var(--accent); }
footer { text-align:center; color:var(--muted); font-size:.8rem; padding:0 1rem 2rem; }
@media (max-width:640px){ main { margin:0; border-radius:0; padding:1rem 1rem 2rem; } header { padding:.8rem 1rem; } }
"""

URL_RE = re.compile(r"(https?://[^\s<)]+)")


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = URL_RE.sub(lambda m: f'<a href="{m.group(1)}" rel="noopener">{m.group(1)}</a>', text)
    return text


def render(md: str) -> tuple[str, str]:
    """Return (title, body html)."""
    title = ""
    parts: list[str] = []
    para: list[str] = []
    h1_count = 0

    def flush() -> None:
        if para:
            parts.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line:
            flush()
            continue
        if line.startswith("# "):
            flush()
            h1_count += 1
            text = line[2:].strip()
            if not title:
                title = text
            anchor = "en" if h1_count == 1 else "vi"
            parts.append(f'<h1 id="{anchor}">{inline(text)}</h1>')
            continue
        if line.startswith("## "):
            flush()
            parts.append(f"<h2>{inline(line[3:].strip())}</h2>")
            continue
        if line.strip() == "---":
            flush()
            parts.append("<hr>")
            continue
        para.append(line.strip())
    flush()
    return title, "\n".join(parts)


def page(title: str, body: str, other: tuple[str, str]) -> str:
    other_href, other_label = other
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · M-AIDA</title>
<style>{STYLE}</style>
</head>
<body>
<header><a href="/">M-AIDA</a><span>Meta-Analysis Intelligent Data Assistant</span></header>
<main>
<nav class="lang"><a href="#en">English</a> · <a href="#vi">Tiếng Việt</a> · <a href="{other_href}">{other_label}</a> · <a href="/">Back to the app</a></nav>
{body}
</main>
<footer>Do Thuy Huong &amp; Phan Anh Tu · Can Tho University · source: https://github.com/thuyhuongctu/M-AIDA (AGPL-3.0)</footer>
</body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = {
        "TERMS.md": ("terms.html", ("/legal/privacy.html", "Privacy Policy")),
        "PRIVACY.md": ("privacy.html", ("/legal/terms.html", "Terms of Service")),
    }
    for src, (dest, other) in pairs.items():
        title, body = render((ROOT / "legal" / src).read_text(encoding="utf-8"))
        (OUT / dest).write_text(page(title, body, other), encoding="utf-8")
        print(f"wrote {OUT / dest}")


if __name__ == "__main__":
    main()
