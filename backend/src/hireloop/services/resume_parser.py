import io
from typing import Any

import pypdf
from docx import Document


class ResumeParseError(Exception):
    pass


def parse_resume_bytes(data: bytes, filename: str) -> dict[str, Any]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _parse_pdf(data)
    if lower.endswith(".docx"):
        return _parse_docx(data)
    raise ResumeParseError(f"Unsupported file type: {filename}")


def _parse_pdf(data: bytes) -> dict[str, Any]:
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception as e:
        raise ResumeParseError(f"Failed to read PDF: {e}") from e

    text_parts: list[str] = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue

    text = "\n".join(text_parts).strip()
    return {
        "text": text,
        "markdown": text,
        "content_type": "pdf",
        "page_count": len(reader.pages),
    }


def _parse_docx(data: bytes) -> dict[str, Any]:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:
        raise ResumeParseError(f"Failed to read DOCX: {e}") from e

    parts: list[str] = []
    md_parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        parts.append(text)
        style_name = paragraph.style.name if paragraph.style is not None else ""
        style = style_name.lower()
        if "heading 1" in style or style == "title":
            md_parts.append(f"# {text}")
        elif "heading 2" in style:
            md_parts.append(f"## {text}")
        elif "heading 3" in style:
            md_parts.append(f"### {text}")
        else:
            md_parts.append(text)

    return {
        "text": "\n".join(parts),
        "markdown": "\n\n".join(md_parts),
        "content_type": "docx",
        "page_count": None,
    }
