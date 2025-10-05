"""Tests for revision sheet generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.revision import RevisionGenerator, RevisionSheet


def test_revision_sheet_markdown_contains_bullet_synthesis(monkeypatch):
    generator = RevisionGenerator()

    def fake_generate(self, theme, doc_snippets, **kwargs):  # pragma: no cover - stub
        return [
            "- Point clé 1 (Source A, 2023)",
            "- Point clé 2 illustré par un exemple institutionnel",
            "- Point clé 3 reliant deux documents",
            "- Point clé 4 ouvrant sur un débat académique",
        ]

    monkeypatch.setattr("app.llm_summarizer.LLMSummarizer.generate", fake_generate)

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


def test_bibliography_section_shows_concise_entries(monkeypatch):
    generator = RevisionGenerator()

    def fake_generate(self, theme, doc_snippets, **kwargs):
        return [
            "- Point clé 1 (Source A, 2023)",
            "- Point clé 2 illustré par un exemple institutionnel",
            "- Point clé 3 reliant deux documents",
            "- Point clé 4 ouvrant sur un débat académique",
        ]

    monkeypatch.setattr("app.llm_summarizer.LLMSummarizer.generate", fake_generate)

    def fake_external(self, theme, limit=3):
        return [f"{theme} — Encyclopædia Universalis"]

    monkeypatch.setattr(RevisionGenerator, "fetch_external_references", fake_external)

    documents = [
        {
            "title": "Document 1",
            "text_content": (
                "Dupont J. (2020). Analyse du thème : perspective historique. "
                "Disponible sur https://exemple.org."
            ),
        }
    ]

    sheet = generator.create_revision_sheet("Thème", documents)

    markdown = sheet.to_markdown()
    biblio_section = markdown.split("## 3. Références bibliographiques\n", 1)[1].split("\n## 4.", 1)[0]
    lines = [line for line in biblio_section.strip().splitlines() if line]

    assert lines
    for line in lines:
        if line.startswith("- Aucune référence disponible"):
            assert len(lines) == 1
        else:
            assert line.startswith("- ")
            assert len(line) <= 120
