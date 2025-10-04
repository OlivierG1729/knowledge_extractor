"""PDF export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fpdf import FPDF


class PDFDocument(FPDF):
    def header(self) -> None:  # pragma: no cover - layout only
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, self.title, ln=True, align="C")
        self.ln(5)


def write_multiline(pdf: PDFDocument, text: str, *, font_size: int = 11) -> None:
    pdf.set_font("Helvetica", size=font_size)
    pdf.multi_cell(0, 8, txt=text)
    pdf.ln(2)


def save_revision_pdf(base_dir: Path, theme: str, markdown: str) -> Path:
    pdf_dir = base_dir / "data" / "revision_sheets"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_name = theme.replace("/", "-").replace(" ", "_")
    target_path = pdf_dir / f"{safe_name}.pdf"
    pdf = PDFDocument()
    pdf.set_title(theme)
    pdf.add_page()
    for block in markdown.split("\n\n"):
        write_multiline(pdf, block)
    pdf.output(str(target_path))
    return target_path


def save_summary_pdf(base_dir: Path, title: str, content: str) -> Path:
    pdf_dir = base_dir / "data" / "summaries"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_name = title.replace("/", "-").replace(" ", "_")
    target_path = pdf_dir / f"{safe_name}.pdf"
    pdf = PDFDocument()
    pdf.set_title(title)
    pdf.add_page()
    write_multiline(pdf, content)
    pdf.output(str(target_path))
    return target_path

