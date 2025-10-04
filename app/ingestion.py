"""Document ingestion utilities."""

from __future__ import annotations

import mimetypes
import re
import textwrap
from pathlib import Path
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader


TEXT_EXTENSIONS = {".txt", ".md", ".rtf"}
DOCX_EXTENSIONS = {".docx"}
PDF_EXTENSIONS = {".pdf"}


class IngestionError(RuntimeError):
    """Raised when a document cannot be ingested."""


def normalise_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or "Document sans titre"


def save_uploaded_file(base_dir: Path, file_name: str, data: bytes) -> Path:
    target_dir = base_dir / "data" / "corpus" / "originals"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file_name
    with open(target_path, "wb") as f:
        f.write(data)
    return target_path


def extract_text_from_path(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="ignore")
    if extension in DOCX_EXTENSIONS:
        doc = Document(path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    if extension in PDF_EXTENSIONS:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    raise IngestionError(f"Format de fichier non supporté : {extension}")


def guess_extension_from_mime(mime_type: Optional[str]) -> str:
    if not mime_type:
        return ""
    extension = mimetypes.guess_extension(mime_type)
    return extension or ""


def ingest_uploaded_file(
    base_dir: Path, *, file_name: str, data: bytes, mime_type: Optional[str]
) -> Tuple[str, str, Path]:
    extension = Path(file_name).suffix
    if not extension:
        extension = guess_extension_from_mime(mime_type)
        if extension:
            file_name = f"{file_name}{extension}"
    saved_path = save_uploaded_file(base_dir, file_name, data)
    text_content = extract_text_from_path(saved_path)
    title = normalise_title(Path(file_name).stem.replace("_", " "))
    return title, text_content, saved_path


def ingest_text_input(text: str, *, title: Optional[str] = None) -> Tuple[str, str]:
    cleaned = textwrap.dedent(text).strip()
    if not cleaned:
        raise IngestionError("Le texte fourni est vide.")
    final_title = normalise_title(title or cleaned.splitlines()[0][:80])
    return final_title, cleaned


def ingest_url(base_dir: Path, url: str) -> Tuple[str, str, Path]:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise IngestionError(f"Impossible de récupérer l'URL : {response.status_code}")
    soup = BeautifulSoup(response.content, "html.parser")
    title = soup.title.string if soup.title else url
    texts = [element.get_text(separator=" ", strip=True) for element in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]) ]
    content = "\n".join(filter(None, texts))
    if not content.strip():
        content = BeautifulSoup(response.content, "html.parser").get_text(separator=" ", strip=True)
    if not content.strip():
        raise IngestionError("Le contenu de la page est vide.")
    final_title = normalise_title(title)
    storage_dir = base_dir / "data" / "corpus" / "web"
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", final_title)[:80]
    target_path = storage_dir / f"{safe_name}.html"
    target_path.write_bytes(response.content)
    return final_title, content, target_path

