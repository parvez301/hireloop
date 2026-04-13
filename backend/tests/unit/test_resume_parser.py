from pathlib import Path

import pytest

from hireloop.services.resume_parser import ResumeParseError, parse_resume_bytes

FIXTURES = Path(__file__).parent.parent / "fixtures" / "resumes"


def test_parse_docx_extracts_text() -> None:
    data = (FIXTURES / "sample.docx").read_bytes()
    result = parse_resume_bytes(data, filename="sample.docx")
    assert "Jane Doe" in result["text"]
    assert "Senior Backend Engineer" in result["text"]
    assert result["content_type"] == "docx"


def test_parse_pdf_returns_result_even_if_empty() -> None:
    data = (FIXTURES / "sample.pdf").read_bytes()
    result = parse_resume_bytes(data, filename="sample.pdf")
    assert result["content_type"] == "pdf"
    assert "text" in result


def test_parse_unsupported_filetype_raises() -> None:
    with pytest.raises(ResumeParseError) as exc_info:
        parse_resume_bytes(b"some text", filename="resume.txt")
    assert "unsupported" in str(exc_info.value).lower()


def test_parse_corrupted_bytes_raises() -> None:
    with pytest.raises(ResumeParseError):
        parse_resume_bytes(b"not a real pdf", filename="resume.pdf")
