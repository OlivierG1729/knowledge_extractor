"""High level services orchestrating ingestion, revision sheets and summaries."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import db
from .pdf_utils import save_revision_pdf, save_summary_pdf
from .reports import update_revision_report, update_summary_report
from .revision import RevisionGenerator
from .summarization import summarise_text


class KnowledgeService:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        db.ensure_database(base_dir)
        self.revision_generator = RevisionGenerator()

    # Document operations -------------------------------------------------
    def add_document(self, *, title: str, source_type: str, source_path: Optional[str], url: Optional[str], text_content: str) -> int:
        document_id = db.insert_document(
            self.base_dir,
            title=title,
            source_type=source_type,
            source_path=source_path,
            url=url,
            text_content=text_content,
        )
        # Regenerate previously saved revision sheets to include the new document
        self.regenerate_saved_revision_sheets()
        return document_id

    def list_documents(self) -> List[Dict]:
        return db.fetch_documents(self.base_dir)

    def get_document(self, document_id: int) -> Optional[Dict]:
        return db.fetch_document(self.base_dir, document_id)

    # Summaries -----------------------------------------------------------
    def build_summary(self, document_id: int, max_sentences: int = 12) -> Optional[str]:
        document = self.get_document(document_id)
        if not document:
            return None
        text = document["text_content"]
        summary = summarise_text(text, max_sentences=max_sentences)
        if not summary:
            summary = text[:2000]
        pdf_path = save_summary_pdf(self.base_dir, document["title"], summary)
        db.upsert_summary(self.base_dir, document_id=document_id, summary=summary, pdf_path=str(pdf_path))
        self.refresh_summary_report()
        return summary

    def refresh_summary_report(self) -> None:
        summaries = db.fetch_summaries(self.base_dir)
        documents = {doc["id"]: doc for doc in self.list_documents()}
        entries = []
        for summary in summaries:
            document = documents.get(summary["document_id"])
            if not document:
                continue
            entries.append(
                {
                    "document_id": summary["document_id"],
                    "document_title": document["title"],
                    "summary_pdf": summary["pdf_path"],
                    "last_updated": summary["updated_at"],
                }
            )
        update_summary_report(self.base_dir, entries)

    # Revision sheets -----------------------------------------------------
    def generate_revision_sheet(self, theme: str) -> Optional[str]:
        documents = self.list_documents()
        if not documents:
            return None
        sheet = self.revision_generator.create_revision_sheet(theme, documents)
        markdown = sheet.to_markdown()
        pdf_path = save_revision_pdf(self.base_dir, theme, markdown)
        db.upsert_revision_sheet(
            self.base_dir,
            theme=theme,
            content=markdown,
            pdf_path=str(pdf_path),
            sources=sheet.sources,
        )
        self.refresh_revision_report()
        return markdown

    def regenerate_saved_revision_sheets(self) -> None:
        saved_sheets = db.fetch_revision_sheets(self.base_dir)
        if not saved_sheets:
            return
        for sheet in saved_sheets:
            self.generate_revision_sheet(sheet["theme"])

    def refresh_revision_report(self) -> None:
        sheets = db.fetch_revision_sheets(self.base_dir)
        entries = []
        for sheet in sheets:
            entries.append(
                {
                    "theme": sheet["theme"],
                    "pdf_path": sheet["pdf_path"],
                    "sources": ", ".join(sheet["sources"]),
                    "last_updated": sheet["updated_at"],
                }
            )
        update_revision_report(self.base_dir, entries)

