"""Revision sheet generation logic."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Sequence
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .summarization import summarise_documents


@dataclass
class RevisionSheet:
    theme: str
    synthesis: str
    sources: List[str]
    bibliography: List[str]
    essay_topics: List[str]

    def to_markdown(self) -> str:
        lines = [f"# {self.theme}", "", "## 1. Synthèse", self.synthesis or "(Synthèse indisponible)"]
        lines.extend(["", "## 2. Sources du corpus"])
        if self.sources:
            lines.extend([f"- {source}" for source in self.sources])
        else:
            lines.append("- Aucune source identifiée")
        lines.extend(["", "## 3. Références bibliographiques"])
        if self.bibliography:
            lines.extend([f"- {ref}" for ref in self.bibliography])
        else:
            lines.append("- Aucune référence disponible")
        lines.extend(["", "## 4. Sujets possibles"])
        lines.extend([f"- {topic}" for topic in self.essay_topics])
        return "\n".join(lines)


class RevisionGenerator:
    """Generate revision sheets from a corpus."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)

    def select_relevant_documents(
        self, theme: str, documents: Sequence[dict], max_docs: int = 8
    ) -> List[dict]:
        if not documents:
            return []
        corpus_texts = [doc["text_content"] for doc in documents]
        tfidf_matrix = self.vectorizer.fit_transform(corpus_texts + [theme])
        theme_vector = tfidf_matrix[-1]
        doc_vectors = tfidf_matrix[:-1]
        similarities = cosine_similarity(doc_vectors, theme_vector)
        indexed = list(enumerate(similarities.flatten()))
        ranked = sorted(indexed, key=lambda item: item[1], reverse=True)
        selected_indices = [index for index, score in ranked[:max_docs] if score > 0]
        return [documents[i] for i in selected_indices]

    def build_synthesis(self, theme: str, docs: Sequence[dict]) -> str:
        contents = [doc["text_content"] for doc in docs]
        if not contents:
            return ""
        summary = summarise_documents(contents, max_sentences=12)
        return summary or f"Aucune synthèse disponible pour {theme}."

    def extract_bibliographic_references(self, docs: Sequence[dict]) -> List[str]:
        references: List[str] = []
        for doc in docs:
            lines = re.split(r"[\n\r]", doc["text_content"])
            for line in lines:
                cleaned = line.strip()
                if len(cleaned) < 40:
                    continue
                if re.search(r"(19|20)\d{2}", cleaned) or "doi" in cleaned.lower():
                    references.append(cleaned)
        unique_refs = list(dict.fromkeys(references))
        return unique_refs[:6]

    def fetch_external_references(self, theme: str, limit: int = 3) -> List[str]:
        try:
            import wikipedia

            wikipedia.set_lang("fr")
            search_results = wikipedia.search(theme, results=limit)
            external_refs = []
            for result in search_results:
                try:
                    page = wikipedia.page(result, auto_suggest=False)
                    external_refs.append(f"{page.title} — {page.url}")
                except Exception:  # pragma: no cover - best effort
                    continue
            return external_refs
        except Exception:
            templates = [
                f"Exploration complémentaire : encyclopédie ou bases de données académiques sur '{theme}'.",
                f"Articles de revues spécialisées consacrées à '{theme}'.",
                f"Rapports institutionnels récents traitant de '{theme}'.",
            ]
            return templates[:limit]

    def format_bibliography(self, internal_refs: Sequence[str], external_refs: Sequence[str]) -> List[str]:
        bibliography: List[str] = []
        for ref in internal_refs:
            bibliography.append(f"**{ref}** (Corpus)")
        bibliography.extend(ref for ref in external_refs if ref)
        return bibliography[:8]

    def generate_topics(self, theme: str) -> List[str]:
        templates = [
            "Analysez les enjeux historiques, économiques et sociaux liés à {theme}.",
            "Discutez des débats théoriques majeurs entourant {theme}.",
            "Proposez une étude comparative mettant en perspective {theme} et un autre cas d'étude.",
            "Évaluez l'impact des politiques publiques sur {theme}.",
            "Expliquez comment {theme} transforme les pratiques contemporaines.",
        ]
        random.seed(theme)
        selected = random.sample(templates, k=3)
        return [template.format(theme=theme) for template in selected]

    def create_revision_sheet(self, theme: str, documents: Sequence[dict]) -> RevisionSheet:
        selected_docs = self.select_relevant_documents(theme, documents)
        synthesis = self.build_synthesis(theme, selected_docs)
        sources = [doc["title"] for doc in selected_docs]
        internal_refs = self.extract_bibliographic_references(selected_docs)
        external_refs = self.fetch_external_references(theme)
        bibliography = self.format_bibliography(internal_refs, external_refs)
        topics = self.generate_topics(theme)
        return RevisionSheet(theme, synthesis, sources, bibliography, topics)

