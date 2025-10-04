"""Database utilities for the knowledge extractor application."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DB_PATH = Path("data/app.db")


def ensure_database(base_dir: Path) -> None:
    """Ensure that the sqlite database and required tables exist."""
    db_path = base_dir / DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT,
                url TEXT,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS revision_sheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                sources TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection(base_dir: Path):
    """Context manager yielding a sqlite connection."""
    db_path = base_dir / DB_PATH
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def insert_document(
    base_dir: Path,
    *,
    title: str,
    source_type: str,
    source_path: Optional[str],
    url: Optional[str],
    text_content: str,
) -> int:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (title, source_type, source_path, url, text_content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, source_type, source_path, url, text_content),
        )
        conn.commit()
        return cursor.lastrowid


def fetch_documents(base_dir: Path) -> List[Dict[str, Any]]:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, source_type, source_path, url, text_content,
                   created_at, updated_at
            FROM documents
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
    columns = ["id", "title", "source_type", "source_path", "url", "text_content", "created_at", "updated_at"]
    return [dict(zip(columns, row)) for row in rows]


def fetch_document(base_dir: Path, document_id: int) -> Optional[Dict[str, Any]]:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, source_type, source_path, url, text_content,
                   created_at, updated_at
            FROM documents WHERE id = ?
            """,
            (document_id,),
        )
        row = cursor.fetchone()
    if not row:
        return None
    columns = ["id", "title", "source_type", "source_path", "url", "text_content", "created_at", "updated_at"]
    return dict(zip(columns, row))


def upsert_summary(
    base_dir: Path,
    *,
    document_id: int,
    summary: str,
    pdf_path: str,
) -> None:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO summaries (document_id, summary, pdf_path)
            VALUES (?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                summary=excluded.summary,
                pdf_path=excluded.pdf_path,
                updated_at=CURRENT_TIMESTAMP
            """,
            (document_id, summary, pdf_path),
        )
        conn.commit()


def fetch_summaries(base_dir: Path) -> List[Dict[str, Any]]:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT document_id, summary, pdf_path, created_at, updated_at
            FROM summaries
            """
        )
        rows = cursor.fetchall()
    columns = ["document_id", "summary", "pdf_path", "created_at", "updated_at"]
    return [dict(zip(columns, row)) for row in rows]


def upsert_revision_sheet(
    base_dir: Path,
    *,
    theme: str,
    content: str,
    pdf_path: str,
    sources: Iterable[str],
) -> None:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO revision_sheets (theme, content, pdf_path, sources)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(theme) DO UPDATE SET
                content=excluded.content,
                pdf_path=excluded.pdf_path,
                sources=excluded.sources,
                updated_at=CURRENT_TIMESTAMP
            """,
            (theme, content, pdf_path, json.dumps(list(sources))),
        )
        conn.commit()


def fetch_revision_sheets(base_dir: Path) -> List[Dict[str, Any]]:
    with get_connection(base_dir) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT theme, content, pdf_path, sources, created_at, updated_at
            FROM revision_sheets
            ORDER BY updated_at DESC
            """
        )
        rows = cursor.fetchall()
    columns = ["theme", "content", "pdf_path", "sources", "created_at", "updated_at"]
    result = []
    for row in rows:
        record = dict(zip(columns, row))
        record["sources"] = json.loads(record["sources"])
        result.append(record)
    return result


