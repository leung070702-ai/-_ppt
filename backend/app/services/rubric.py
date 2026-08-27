from __future__ import annotations

from pathlib import Path


def extract_rubric_text(path: Path) -> str:
    """Extract a bounded UTF-8/plain text representation from rubric files."""

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore")[:20_000]
    if suffix == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)[:20_000]
    if suffix == ".docx":
        from docx import Document

        return "\n".join(p.text for p in Document(str(path)).paragraphs)[:20_000]
    return ""
