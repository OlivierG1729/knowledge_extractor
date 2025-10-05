"""Tests for revision sheet generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.revision import RevisionGenerator, RevisionSheet


def test_revision_sheet_markdown_contains_bullet_synthesis(monkeypatch):
    generator = RevisionGenerator()

    def fake_summarise(doc_texts, max_sentences=12):  # pragma: no cover - simple stub
        return (
            "Phrase 1 sur le thème. Phrase 2 apporte un complément; une précision. "
            "Phrase 3 souligne un autre point. Phrase 4 complète. Phrase 5 ajoute un exemple. "
            "Phrase 6 conclut brièvement."
        )

    monkeypatch.setattr("app.revision.summarise_documents", fake_summarise)

    documents = [
        {
            "title": "Document 1",
            "text_content": "Le contenu du document évoque le thème et plusieurs dimensions associées.",
        }
    ]

    sheet = generator.create_revision_sheet("Thème d'étude", documents)

    assert 4 <= len(sheet.synthesis) <= 6
    assert all(item.startswith("- ") for item in sheet.synthesis)

    markdown = sheet.to_markdown()
    synth_section = markdown.split("## 1. Synthèse\n", 1)[1].split("\n## 2.", 1)[0]
    lines = [line for line in synth_section.strip().splitlines() if line]

    assert lines == sheet.synthesis


def test_revision_sheet_markdown_fallback():
    sheet = RevisionSheet(
        theme="Sujet",
        synthesis=[],
        sources=[],
        bibliography=[],
        essay_topics=[],
    )

    markdown = sheet.to_markdown()

    assert "(Synthèse indisponible)" in markdown
