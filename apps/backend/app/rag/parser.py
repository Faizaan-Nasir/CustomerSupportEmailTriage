"""File parsing utilities for the RAG pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ParserError(RuntimeError):
    """Raised when a file cannot be parsed into text."""


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".tsv",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
    ".webp",
}


def _read_text_file(file_path: Path) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ParserError(f"Unable to decode text file: {file_path}")


def _extract_pdf_with_pymupdf(file_path: Path) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ParserError("PyMuPDF is not installed.") from exc

    text_parts: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            extracted = page.get_text("text")
            if extracted:
                text_parts.append(extracted)
    return "\n".join(text_parts).strip()


def _extract_pdf_with_pdfplumber(file_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ParserError("pdfplumber is not installed.") from exc

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    return "\n".join(text_parts).strip()


def _extract_text_from_pdf(file_path: Path) -> str:
    errors: list[str] = []
    for extractor in (_extract_pdf_with_pymupdf, _extract_pdf_with_pdfplumber):
        try:
            text = extractor(file_path)
            if text:
                return text
        except ParserError as exc:
            errors.append(str(exc))

    message = (
        f"Unable to extract text from PDF {file_path}. "
        "Install 'pymupdf' or 'pdfplumber' to enable PDF parsing."
    )
    if errors:
        message += f" Backends tried: {', '.join(errors)}."
    raise ParserError(message)


def _extract_text_from_image(file_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ParserError("Pillow is not installed.") from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise ParserError("pytesseract is not installed.") from exc

    with Image.open(file_path) as image:
        text = pytesseract.image_to_string(image)
    return text.strip()


def parse_file(file_path: str) -> dict[str, str]:
    """Parse a supported file into plain text for downstream RAG indexing."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ParserError(f"Expected a file path, received: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_text_from_pdf(path)
    elif suffix in IMAGE_EXTENSIONS:
        text = _extract_text_from_image(path)
    elif suffix in TEXT_EXTENSIONS or suffix == "":
        text = _read_text_file(path)
    else:
        raise ParserError(
            f"Unsupported file type: {suffix or '<no extension>'}. "
            "Supported types include PDF, common images, and plain-text files."
        )

    cleaned = text.strip()
    if not cleaned:
        raise ParserError(f"No text could be extracted from file: {path}")

    return {"text": cleaned}


def parse_bytes(_content: bytes, _metadata: dict[str, Any] | None = None) -> dict[str, str]:
    """Placeholder for future in-memory parsing workflows."""
    raise ParserError("In-memory parsing is not implemented yet. Use parse_file instead.")

