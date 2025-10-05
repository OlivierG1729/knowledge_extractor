"""Revision sheet generation logic."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .llm_summarizer import LLMSummarizer


@dataclass
class RevisionSheet:
    theme: str
    synthesis: List[str]
    sources: List[str]
    bibliography: List[str]
    essay_topics: List[str]

    def to_markdown(self) -> str:
        lines = [f"# {self.theme}", "", "## 1. Synthèse"]
        if self.synthesis:
            lines.extend(self.synthesis)
        else:
            lines.append("(Synthèse indisponible)")
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
        try:
            self.llm = LLMSummarizer()
        except Exception:  # pragma: no cover - defensive guard
            self.llm = None

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

    def build_synthesis(self, theme: str, docs: Sequence[dict]) -> List[str]:
        contents = [doc["text_content"] for doc in docs]
        if not contents:
            return []

        llm_bullets: List[str] = []
        if getattr(self, "llm", None):
            try:
                llm_bullets = self.llm.generate(theme, contents)
            except Exception:
                llm_bullets = []

        cleaned_llm = [
            bullet if bullet.startswith("- ") else f"- {bullet.lstrip('- ')}"
            for bullet in llm_bullets
            if bullet.strip()
        ]
        if 4 <= len(cleaned_llm) <= 6:
            return cleaned_llm[:6]

        return self._tfidf_synthesis(contents)

    def _tfidf_synthesis(self, contents: Sequence[str]) -> List[str]:
        from .summarization import summarise_documents

        summary = summarise_documents(contents, max_sentences=12).strip()
        if not summary:
            return []

        segments = re.split(r"(?<=[.!?])\s+|\n+", summary)
        cleaned_segments = [segment.strip(" -•\t") for segment in segments if segment.strip(" -•\t")]
        if len(cleaned_segments) < 4:
            expanded: List[str] = []
            for segment in cleaned_segments:
                parts = [part.strip(" -•\t") for part in re.split(r"[;:]", segment) if part.strip(" -•\t")]
                if len(parts) > 1:
                    expanded.extend(parts)
                else:
                    expanded.append(segment)
            cleaned_segments = expanded

        def preserve_sentence_boundary(text: str, limit: int = 160) -> str:
            if len(text) <= limit:
                return text
            last_boundary = None
            for match in re.finditer(r"(?<=[.!?])\s", text):
                if match.start() <= limit:
                    last_boundary = match.start()
                else:
                    break
            if last_boundary is not None:
                return text[:last_boundary].strip()
            return text

        bullets: List[str] = []
        for segment in cleaned_segments:
            sentence = preserve_sentence_boundary(segment)
            if not sentence:
                continue
            if not sentence.endswith(('.', '!', '?')):
                sentence = sentence.rstrip() + '.'
            bullets.append(f"- {sentence}")
            if len(bullets) == 6:
                break

        return bullets[:6]

    def extract_bibliographic_references(self, docs: Sequence[dict]) -> List[str]:
        references: List[str] = []
        for doc in docs:
            lines = re.split(r"[\n\r]", doc["text_content"])
            for line in lines:
                cleaned = line.strip()
                if len(cleaned) < 40:
                    continue
                if re.search(r"(19|20)\d{2}", cleaned) or "doi" in cleaned.lower():
                    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
                    snippet_parts: List[str] = []
                    for sentence in sentences:
                        if not sentence:
                            continue
                        snippet_parts.append(sentence.strip())
                        snippet = " ".join(snippet_parts).strip()
                        if (
                            re.search(r"(19|20)\d{2}", snippet)
                            or "doi" in snippet.lower()
                            or len(snippet_parts) > 1
                        ):
                            break
                    snippet = " ".join(snippet_parts).strip()
                    if len(snippet) > 160:
                        snippet = snippet[:160].rsplit(" ", 1)[0] + "…"
                    references.append(snippet)
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
            minimal_fallbacks = [
                f"{theme} — Encyclopædia Universalis",
                f"{theme} — Cairn.info",
                f"{theme} — OpenEdition Journals",
            ]
            return minimal_fallbacks[:limit]

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

