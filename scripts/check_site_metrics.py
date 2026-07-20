#!/usr/bin/env python3
"""Guard the public M-AIDA site against research-number drift.

Single source of truth: assets/data/site-metrics.json (canonical P6 locked
corpus). This check fails (exit 1) if any served HTML page carries a known
stale variant of the headline numbers, or if index.html is missing a canonical
display token. Wired into the GitHub Pages workflow so a drifted page can never
be deployed. See the website review (2026-07) that motivated it.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["index.html", "commercial.html", "data_melody.html",
         "songs.html", "huong.html", "privacy.html", "library.html", "asia.html",
         "asia-p1.html", "asia-p2.html", "asia-p3.html", "asia-p4.html", "asia-p5.html", "asia-p6.html", "asia-p7.html", "asia-p8.html", "asia-p9.html", "asia-p10.html", "asia-bookchapter.html", "asia-cd1.html", "asia-cd2.html", "asia-maida-paper.html", "asia-atlas.html"]

with open(os.path.join(ROOT, "assets/data/site-metrics.json"), encoding="utf-8") as f:
    M = json.load(f)

# Known-wrong variants from earlier corpus snapshots. If any of these labelled
# strings reappears on a page, a stat has drifted from the locked corpus.
FORBIDDEN = [
    "145 studies", "145 Studies", "145 nghi",
    "176 effect", "176 Effect", "176 mức",
    "22 economies", "22 Economies", "22 nền",
    "r = .046", "r&#772; = .046",
    "lowers it to .035", "r&#772; = .035",
    "I&#178; = 62%",  # bare 62% (canonical is 62.6%)
]

# Canonical display tokens that MUST be present on the main page.
REQUIRED_INDEX = [
    '236 studies', '286 effect sizes', '35 economies',
    'r&#772; = .074', 'r&#772; = .034', 'I&#178; = 62.6%',
]

errors = []
for page in PAGES:
    path = os.path.join(ROOT, page)
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        html = f.read()
    for bad in FORBIDDEN:
        if bad in html:
            errors.append(f"{page}: forbidden stale token present -> {bad!r}")

idx = os.path.join(ROOT, "index.html")
with open(idx, encoding="utf-8") as f:
    index_html = f.read()
for tok in REQUIRED_INDEX:
    if tok not in index_html:
        errors.append(f"index.html: required canonical token missing -> {tok!r}")

if errors:
    print("SITE METRICS CHECK FAILED:", file=sys.stderr)
    for e in errors:
        print("  -", e, file=sys.stderr)
    print(f"\nCanonical source: assets/data/site-metrics.json "
          f"(studies={M['studies']}, effect_sizes={M['effect_sizes']}, "
          f"economies={M['economies']}, pooled_r={M['pooled_r']}, "
          f"adjusted_r={M['adjusted_r']}, i2={M['i2_percent']}%).", file=sys.stderr)
    sys.exit(1)

print(f"Site metrics OK across {len(PAGES)} pages "
      f"(studies={M['studies']}, K={M['effect_sizes']}, economies={M['economies']}, "
      f"r={M['pooled_r']}, adj={M['adjusted_r']}, I2={M['i2_percent']}%).")
