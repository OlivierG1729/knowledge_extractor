"""LLM-powered summarisation helper."""

from __future__ import annotations

import os
import re
from typing import List, Sequence


class LLMSummarizer:
    """Generate synthetic revision bullet points with a Hugging Face model."""

    def __init__(
        self,
        model_name: str | None = None,
        *,
        use_4bit: bool = True,
        device_map: str | None = "auto",
        max_input_tokens: int = 8192,
    ) -> None:
        self.model_name = model_name or os.getenv(
            "LLM_SUMMARIZER_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1"
        )
        self.use_4bit = use_4bit
        self.device_map = device_map
        self.max_input_tokens = max_input_tokens

        self.tokenizer = None
        self.model = None
        self.load_error: Exception | None = None
        self._token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._model_factory = AutoModelForCausalLM
            self._tokenizer_factory = AutoTokenizer
        except Exception as exc:  # pragma: no cover - import guards
            self.load_error = exc
            self._model_factory = None
            self._tokenizer_factory = None

    def _load_tokenizer(self, factory, token: str | None):
        kwargs = {"use_fast": True}
        return self._call_from_pretrained(factory, token, **kwargs)

    def _load_model(self, factory, token: str | None):
        kwargs: dict = {"trust_remote_code": True}
        if self.device_map is not None:
            kwargs["device_map"] = self.device_map
        if self.use_4bit:
            try:  # pragma: no cover - depends on optional package
                from transformers import BitsAndBytesConfig

                kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
            except Exception:  # pragma: no cover - fall back to simple flag
                kwargs.setdefault("load_in_4bit", True)
        return self._call_from_pretrained(factory, token, **kwargs)

    def _call_from_pretrained(self, factory, token: str | None, **kwargs):
        if token:
            try:
                return factory.from_pretrained(self.model_name, token=token, **kwargs)
            except TypeError:
                return factory.from_pretrained(
                    self.model_name, use_auth_token=token, **kwargs
                )
        return factory.from_pretrained(self.model_name, **kwargs)

    def generate(
        self,
        theme: str,
        doc_snippets: Sequence[str],
        *,
        max_new_tokens: int = 320,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> List[str]:
        """Generate 4 to 6 bullet points from document snippets."""

        self._ensure_loaded()
        if self.model is None or self.tokenizer is None:
            message = "Le modèle de synthèse n'est pas disponible"
            if self.load_error:
                raise RuntimeError(message) from self.load_error
            raise RuntimeError(message)

        snippets = [snippet.strip() for snippet in doc_snippets if snippet and snippet.strip()]
        if not snippets:
            return []

        prompt = self._build_prompt(theme, snippets, max_new_tokens)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max(self.max_input_tokens - max_new_tokens, 1024),
        )

        try:
            import torch
        except Exception:  # pragma: no cover - torch should be available
            torch = None

        if torch is not None:
            target_device = None
            if hasattr(self.model, "device"):
                target_device = getattr(self.model, "device")
            elif hasattr(self.model, "hf_device_map"):
                device_values = list(getattr(self.model, "hf_device_map").values())
                if device_values:
                    first = device_values[0]
                    if isinstance(first, str):
                        target_device = torch.device(first)
            if target_device is not None:
                inputs = {key: value.to(target_device) for key, value in inputs.items()}

        pad_token_id = self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
        output = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            pad_token_id=pad_token_id,
        )
        generated_ids = output[0][inputs["input_ids"].shape[-1] :]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return self._extract_bullets(text)

    def _ensure_loaded(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return
        if self.load_error and (self._model_factory is None or self._tokenizer_factory is None):
            raise RuntimeError("Impossible de charger le modèle de synthèse") from self.load_error
        if self._model_factory is None or self._tokenizer_factory is None:
            raise RuntimeError("Les bibliothèques Transformers ne sont pas disponibles")
        try:
            self.tokenizer = self._load_tokenizer(self._tokenizer_factory, self._token)
            self.model = self._load_model(self._model_factory, self._token)
        except Exception as exc:  # pragma: no cover - best effort load
            self.load_error = exc
            raise RuntimeError("Impossible de charger le modèle de synthèse") from exc

    def _build_prompt(self, theme: str, snippets: Sequence[str], max_new_tokens: int) -> str:
        instructions = (
            "Tu es un assistant pédagogique francophone chargé de synthétiser un corpus. "
            "Produis une synthèse analytique en français sous forme de 4 à 6 puces. "
            "Chaque puce doit commencer par un tiret, contenir une idée clé en une ou deux phrases. "
            "et faire implicitement référence aux sources (auteur, institution, année) lorsque l'information est disponible. "
            "Chaque phrase doit être complète et terminer par un point."
            "N'invente aucune information et reste fidèle au contenu fourni."
        )
        suffix = (
            "\n\nConsignes :\n"
            "- 4 à 6 puces maximum.\n"
            "- Pas d'introduction ni de conclusion.\n"
            "- Pas de listes imbriquées.\n"
            "- Chaque puce doit rester concise (deux phrases au plus).\n"
            "- Chaque phrase écrite dans une puce doit être complète et se terminer par un point.\n"
            "- Mention implicite des sources lorsqu'elles apparaissent dans les extraits.\n"
            "\nSynthèse attendue :"
        )

        prompt_intro = f"{instructions}\n\nThème : {theme}\n\nExtraits du corpus :\n"
        base_tokens = len(
            self.tokenizer.encode(prompt_intro + suffix, add_special_tokens=False)
        )
        available_for_docs = max(self.max_input_tokens - max_new_tokens - base_tokens, 256)
        selected_docs = self._prepare_snippets(snippets, available_for_docs)

        doc_sections = [
            f"[Document {index}]\n{snippet}"
            for index, snippet in enumerate(selected_docs, start=1)
        ]
        docs = "\n\n".join(doc_sections)
        return f"{prompt_intro}{docs}{suffix}"

    def _prepare_snippets(self, snippets: Sequence[str], token_budget: int) -> List[str]:
        selected: List[str] = []
        accumulated = 0
        for snippet in snippets:
            if not snippet:
                continue
            token_ids = self.tokenizer.encode(snippet, add_special_tokens=False)
            token_count = len(token_ids)
            if accumulated + token_count <= token_budget:
                selected.append(snippet)
                accumulated += token_count
                continue
            remaining = max(token_budget - accumulated, 0)
            if remaining <= 0:
                break
            truncated_ids = token_ids[:remaining]
            truncated_text = self.tokenizer.decode(truncated_ids, skip_special_tokens=True).strip()
            if truncated_text:
                selected.append(truncated_text)
            break
        return selected

    def _extract_bullets(self, text: str) -> List[str]:
        if not text:
            return []
        bullet_candidates: List[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^[\-•*\u2022\t ]+", "", line)
            line = re.sub(r"^\d+[.)\-]\s*", "", line)
            if not line:
                continue
            bullet_candidates.append(f"- {line}")

        if not bullet_candidates:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                cleaned = sentence.strip()
                if cleaned:
                    bullet_candidates.append(f"- {cleaned}")

        cleaned_bullets: List[str] = []
        for bullet in bullet_candidates:
            if bullet not in cleaned_bullets:
                cleaned_bullets.append(bullet)

        return cleaned_bullets[:6]

