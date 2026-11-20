"""Bounded local document extraction and provenance-preserving storage."""
from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_CHARS = 500_000
MAX_PDF_PAGES = 200
MAX_DOCX_ENTRIES = 100
MAX_DOCX_UNCOMPRESSED = 50 * 1024 * 1024


class DocumentExtractionError(ValueError):
    """An uploaded document is unsupported, unsafe or cannot be extracted."""


def _clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()[:MAX_DOCUMENT_CHARS]


def extract_document(filename: str, payload: bytes) -> dict:
    """Extract text from bounded PDF, DOCX or plain-text uploads."""
    if not filename or len(filename) > 255 or Path(filename).name != filename:
        raise DocumentExtractionError("A simple filename is required")
    if not payload:
        raise DocumentExtractionError("The uploaded document is empty")
    if len(payload) > MAX_DOCUMENT_BYTES:
        raise DocumentExtractionError("Document exceeds the 20 MB upload limit")
    extension = Path(filename).suffix.lower()
    page_count = None
    if extension == ".pdf":
        if not payload.startswith(b"%PDF-"):
            raise DocumentExtractionError("File extension and PDF signature do not match")
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(payload), strict=False)
            if reader.is_encrypted:
                raise DocumentExtractionError("Encrypted PDFs are not supported")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise DocumentExtractionError("PDF exceeds the 200-page extraction limit")
            parts = []
            for page in reader.pages:
                if sum(map(len, parts)) >= MAX_DOCUMENT_CHARS:
                    break
                parts.append(page.extract_text() or "")
            text = _clean_text("\n\n".join(parts))
            page_count = len(reader.pages)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError("PDF extraction failed or the file is malformed") from exc
    elif extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                infos = archive.infolist()
                if len(infos) > MAX_DOCX_ENTRIES:
                    raise DocumentExtractionError("DOCX contains too many archive entries")
                total = sum(info.file_size for info in infos)
                if total > MAX_DOCX_UNCOMPRESSED:
                    raise DocumentExtractionError("DOCX expands beyond the safety limit")
                if any(info.flag_bits & 0x1 for info in infos):
                    raise DocumentExtractionError("Encrypted DOCX files are not supported")
                try:
                    document_xml = archive.read("word/document.xml")
                except KeyError as exc:
                    raise DocumentExtractionError("DOCX document content is missing") from exc
            root = ElementTree.fromstring(document_xml)
            paragraphs = []
            for paragraph in root.iter():
                if paragraph.tag.endswith("}p"):
                    value = "".join(
                        node.text or "" for node in paragraph.iter()
                        if node.tag.endswith("}t")
                    )
                    if value.strip():
                        paragraphs.append(value)
            text = _clean_text("\n".join(paragraphs))
            if not text:
                raise DocumentExtractionError("No extractable text was found in the DOCX")
        except DocumentExtractionError:
            raise
        except (zipfile.BadZipFile, ElementTree.ParseError, OSError) as exc:
            raise DocumentExtractionError("DOCX extraction failed or the file is malformed") from exc
    elif extension in {".txt", ".md", ".csv"}:
        try:
            text = _clean_text(payload.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError("Text documents must use UTF-8 encoding") from exc
    else:
        raise DocumentExtractionError("Supported formats are PDF, DOCX, TXT, MD and CSV")
    if not text:
        raise DocumentExtractionError("No extractable text was found in the document")
    return {
        "filename": filename,
        "file_type": extension[1:],
        "text": text,
        "content_hash": hashlib.sha256(payload).hexdigest(),
        "extracted_chars": len(text),
        "page_count": page_count,
    }


class DocumentStore:
    """SQLite document catalogue using the configured JPAI database."""

    def __init__(self, path=None):
        self.path = Path(path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS research_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    extracted_chars INTEGER NOT NULL,
                    page_count INTEGER,
                    uploaded_at TEXT NOT NULL,
                    memory_id INTEGER
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_documents_uploaded "
                "ON research_documents(uploaded_at DESC)"
            )

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def save(self, document: dict) -> dict:
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO research_documents
                   (filename,file_type,content,content_hash,extracted_chars,page_count,uploaded_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (document["filename"], document["file_type"], document["text"],
                 document["content_hash"], document["extracted_chars"],
                 document["page_count"], now),
            )
            row = db.execute(
                "SELECT * FROM research_documents WHERE content_hash=?",
                (document["content_hash"],),
            ).fetchone()
        return self._public(dict(row))

    @staticmethod
    def _public(item):
        item.pop("content", None)
        return item

    def get(self, document_id: int, include_content=False):
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM research_documents WHERE id=?", (document_id,)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        return item if include_content else self._public(item)

    def list(self, limit=50):
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,filename,file_type,content_hash,extracted_chars,page_count,
                   uploaded_at,memory_id FROM research_documents
                   ORDER BY uploaded_at DESC LIMIT ?""", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit=20):
        terms = [term.lower() for term in re.findall(r"[\w-]{2,}", query)][:12]
        if not terms:
            return []
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,filename,file_type,content,content_hash,extracted_chars,
                   page_count,uploaded_at FROM research_documents
                   ORDER BY uploaded_at DESC LIMIT 1000"""
            ).fetchall()
        ranked = []
        for row in rows:
            item = dict(row)
            content = item["content"].lower()
            filename = item["filename"].lower()
            score = sum(content.count(term) + filename.count(term) * 4 for term in terms)
            if score:
                item["relevance"] = score
                item["excerpt"] = item["content"][:420]
                item.pop("content")
                ranked.append(item)
        return sorted(
            ranked, key=lambda item: (item["relevance"], item["uploaded_at"]), reverse=True
        )[:limit]

    def mark_memory(self, document_id: int, memory_id: int):
        with self._connect() as db:
            db.execute(
                "UPDATE research_documents SET memory_id=? WHERE id=?",
                (memory_id, document_id),
            )

    def stats(self):
        with self._connect() as db:
            return {
                "documents_stored": db.execute(
                    "SELECT COUNT(*) FROM research_documents"
                ).fetchone()[0],
                "document_chars_indexed": db.execute(
                    "SELECT COALESCE(SUM(extracted_chars),0) FROM research_documents"
                ).fetchone()[0],
            }
