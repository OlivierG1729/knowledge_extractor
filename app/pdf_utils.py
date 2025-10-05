"""PDF export helpers."""

from __future__ import annotations

import base64
import gzip
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from .assets.dejavu_sans_data import DEJAVU_SANS_BOLD, DEJAVU_SANS_REGULAR


LOGGER = logging.getLogger(__name__)


class PDFDocument(FPDF):
    """FPDF document pre-configured with Unicode DejaVu Sans fonts."""

    _FONT_CACHE_DIR = Path(tempfile.gettempdir()) / "knowledge_extractor_fonts"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._unicode_font_family = "DejaVuSans"
        self._register_unicode_fonts()

    def _register_unicode_fonts(self) -> None:
        self._FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fonts = (
            ("DejaVuSans.ttf", "", DEJAVU_SANS_REGULAR),
            ("DejaVuSans-Bold.ttf", "B", DEJAVU_SANS_BOLD),
        )
        for filename, style, encoded in fonts:
            target_path = self._FONT_CACHE_DIR / filename
            if not target_path.exists():
                decoded = base64.b64decode(encoded)
                data = gzip.decompress(decoded)
                target_path.write_bytes(data)
            self.add_font(
                self._unicode_font_family,
                style=style,
                fname=str(target_path),
                uni=True,
            )

    def header(self) -> None:  # pragma: no cover - layout only
        self.set_font(self._unicode_font_family, "B", 12)
        self.cell(0, 10, self.title, ln=True, align="C")
        self.ln(5)


def write_multiline(pdf: PDFDocument, text: str, *, font_size: int = 11) -> None:
    pdf.set_font(pdf._unicode_font_family, size=font_size)
    pdf.multi_cell(0, 8, txt=text)
    pdf.ln(2)


def write_pdf_with_fallback(pdf: FPDF, target: Path) -> Path:
    """Write ``pdf`` to ``target`` with a rename fallback when locked."""

    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix=suffix) as tmp_file:
        temp_path = Path(tmp_file.name)

    try:
        pdf.output(str(temp_path))
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    try:
        temp_path.replace(target)
        return target
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        candidate = target.with_name(f"{target.stem}_{timestamp}{suffix}")
        counter = 1
        while candidate.exists():
            candidate = target.with_name(f"{target.stem}_{timestamp}_{counter}{suffix}")
            counter += 1
        temp_path.replace(candidate)
        return candidate


def save_revision_pdf(
    base_dir: Path, theme: str, markdown: str, previous_path: Path | None = None
) -> Path:
    pdf_dir = base_dir / "data" / "revision_sheets"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_name = theme.replace("/", "-").replace(" ", "_")
    target_path = pdf_dir / f"{safe_name}.pdf"
    previous_target = Path(previous_path) if previous_path else None
    pdf = PDFDocument()
    pdf.set_title(theme)
    pdf.add_page()
    for block in markdown.split("\n\n"):
        write_multiline(pdf, block)
    written_path = write_pdf_with_fallback(pdf, target_path)
    if written_path != target_path:
        LOGGER.warning(
            "Impossible d'écraser le fichier PDF cible %s (ancien fichier %s). Nouveau fichier enregistré sous %s.",
            target_path,
            previous_target or target_path,
            written_path,
        )
    return written_path


def save_summary_pdf(
    base_dir: Path, title: str, content: str, previous_path: Path | None = None
) -> Path:
    pdf_dir = base_dir / "data" / "summaries"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_name = title.replace("/", "-").replace(" ", "_")
    target_path = pdf_dir / f"{safe_name}.pdf"
    previous_target = Path(previous_path) if previous_path else None
    pdf = PDFDocument()
    pdf.set_title(title)
    pdf.add_page()
    write_multiline(pdf, content)
    written_path = write_pdf_with_fallback(pdf, target_path)
    if written_path != target_path:
        LOGGER.warning(
            "Impossible d'écraser le fichier PDF cible %s (ancien fichier %s). Nouveau fichier enregistré sous %s.",
            target_path,
            previous_target or target_path,
            written_path,
        )
    return written_path
