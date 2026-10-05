#!/usr/bin/env python3
"""Build frontend/public/demo/maida-demo-paper.pdf, the sample PDF of the
in-browser demo (8.0: "Try the demo" on the sign-in page).

The document is synthetic on purpose: it is not a study, every number in it
is invented for the demonstration, and the page says so in its header. The
two sentences the demo shows as evidence (frontend/src/demo.ts, QUOTE_R and
QUOTE_N) must appear in this text word for word; the check at the end reads
the PDF back with pypdfium2 (the reader the backend uses) and fails if they
do not.

    pip install reportlab pypdfium2
    python demo/make_demo_paper.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "demo" / "maida-demo-paper.pdf"

QUOTE_R = (
    "Export intensity is positively correlated with return on assets "
    "(r = 0.18, p = 0.005, N = 240)."
)
QUOTE_N = "The synthetic sample contains 240 manufacturing firms observed between 2016 and 2019."


def build() -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=14)
    head = ParagraphStyle("head", parent=body, fontName="Times-Bold", fontSize=11.5, spaceBefore=8, spaceAfter=2)
    title = ParagraphStyle("title", parent=body, fontName="Times-Bold", fontSize=16, leading=20, spaceAfter=4)
    small = ParagraphStyle("small", parent=body, fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#7a5212"))
    byline = ParagraphStyle("byline", parent=body, fontName="Times-Italic", fontSize=10)

    banner = Table(
        [[Paragraph(
            "M-AIDA DEMO DOCUMENT - synthetic text written for the M-AIDA demo. "
            "Not a real study, no real data. Do not cite.", small)]],
        colWidths=[170 * mm],
    )
    banner.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#c0862a")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fbf3e3")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    table = Table(
        [
            ["Variable", "Mean", "SD", "1", "2"],
            ["1. Return on assets", "0.061", "0.042", "", ""],
            ["2. Export intensity", "0.274", "0.211", "0.18", ""],
            ["3. Firm size (log employees)", "4.12", "1.08", "0.11", "0.24"],
        ],
        colWidths=[62 * mm, 22 * mm, 22 * mm, 18 * mm, 18 * mm],
    )
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Times-Roman", 9.5),
        ("FONT", (0, 0), (-1, 0), "Times-Bold", 9.5),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))

    story = [
        banner,
        Spacer(1, 6 * mm),
        Paragraph("Export intensity and firm profitability: a synthetic example", title),
        Paragraph("M-AIDA demo (synthetic document, 2026)", byline),
        Spacer(1, 4 * mm),
        Paragraph("Abstract", head),
        Paragraph(
            "This document is not a study and reports no real data. It was written so that visitors "
            "can watch M-AIDA go from a PDF to a locked record without signing in. Every number in it "
            "is invented for the demonstration.", body),
        Paragraph("1. Data", head),
        Paragraph(
            QUOTE_N + " Export intensity is measured as exports divided by total sales; profitability "
            "is the return on assets.", body),
        Paragraph("2. Results", head),
        Paragraph("Table 2 reports the means, standard deviations and zero-order correlations. " + QUOTE_R, body),
        Spacer(1, 3 * mm),
        Paragraph("Table 2. Descriptive statistics and correlations (synthetic, N = 240)", head),
        table,
        Spacer(1, 3 * mm),
        Paragraph(
            "In a regression with six control variables, the coefficient on export intensity is 0.15 "
            "(t = 2.31, p = 0.022).", body),
        Paragraph("3. What the demo shows", head),
        Paragraph(
            "M-AIDA proposes the correlation and the sample size together with the sentences it read them "
            "from. A person compares both with the text, codes the moderators, approves and locks the "
            "record. Only locked records enter the forest plot and the exports.", body),
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title="M-AIDA demo document (synthetic)", author="M-AIDA demo", subject="Synthetic sample, not a real study",
    ).build(story)


def check() -> None:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(OUT))
    try:
        if len(pdf) != 1:
            sys.exit(f"expected 1 page, got {len(pdf)}")
        text = pdf[0].get_textpage().get_text_range()
    finally:
        pdf.close()
    flat = re.sub(r"\s+", " ", text)
    for quote in (QUOTE_R, QUOTE_N):
        if quote not in flat:
            sys.exit(f"quote not found in the PDF text: {quote!r}")
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size} bytes, both quotes found")


if __name__ == "__main__":
    build()
    check()
