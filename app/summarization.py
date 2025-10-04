"""Text summarisation helpers."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List

import nltk


def ensure_nltk_resources() -> None:
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords")


def sentence_tokenize(text: str) -> List[str]:
    ensure_nltk_resources()
    sentences = nltk.sent_tokenize(text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def word_tokenize(text: str) -> List[str]:
    ensure_nltk_resources()
    tokens = nltk.word_tokenize(text)
    return [token.lower() for token in tokens if re.search(r"[\wÀ-ÿ]", token)]


def summarise_text(text: str, max_sentences: int = 10) -> str:
    sentences = sentence_tokenize(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    words = word_tokenize(text)
    if not words:
        return ""
    stopwords = set(nltk.corpus.stopwords.words("french")) | set(nltk.corpus.stopwords.words("english"))
    word_freq = Counter(word for word in words if word not in stopwords)
    if not word_freq:
        return ""
    max_freq = max(word_freq.values())
    for word in list(word_freq):
        word_freq[word] /= max_freq
    sentence_scores = {}
    for sentence in sentences:
        sentence_words = word_tokenize(sentence)
        if not sentence_words:
            continue
        score = sum(word_freq.get(word, 0.0) for word in sentence_words)
        sentence_scores[sentence] = score / math.sqrt(len(sentence_words))
    ranked_sentences = sorted(sentence_scores.items(), key=lambda item: item[1], reverse=True)
    selected = sorted((sentence for sentence, _ in ranked_sentences[:max_sentences]), key=lambda s: sentences.index(s))
    return " ".join(selected)


def summarise_documents(doc_texts: Iterable[str], max_sentences: int = 10) -> str:
    combined = "\n".join(text.strip() for text in doc_texts if text.strip())
    if not combined:
        return ""
    return summarise_text(combined, max_sentences=max_sentences)

