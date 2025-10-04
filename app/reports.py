"""Reporting utilities for revision sheets and summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Mapping

import pandas as pd


REVISION_REPORT = Path("data/reports/revision_sheets_overview.csv")
SUMMARY_REPORT = Path("data/reports/document_summaries_overview.csv")


def ensure_reports_dir(base_dir: Path) -> None:
    report_dir = base_dir / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)


def update_revision_report(base_dir: Path, entries: Iterable[Mapping[str, str]]) -> Path:
    ensure_reports_dir(base_dir)
    report_path = base_dir / REVISION_REPORT
    data = list(entries)
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["theme", "pdf_path", "sources", "last_updated"])
    df.to_csv(report_path, index=False)
    return report_path


def update_summary_report(base_dir: Path, entries: Iterable[Mapping[str, str]]) -> Path:
    ensure_reports_dir(base_dir)
    report_path = base_dir / SUMMARY_REPORT
    data = list(entries)
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["document_id", "document_title", "summary_pdf", "last_updated"])
    df.to_csv(report_path, index=False)
    return report_path

