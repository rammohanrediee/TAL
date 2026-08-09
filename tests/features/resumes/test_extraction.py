from io import BytesIO
from pathlib import Path
from docx import Document
from pypdf import PdfWriter
import pytest

from tal.features.resumes.errors import (
    ResumeExtractionError,
    ResumeTextNotFoundError,
)
from tal.features.resumes.extraction import extract_docx, extract_pdf


FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "resumes"

def test_extract_pdf_preserves_text_by_page()->None:
    pdf_bytes=(
        FIXTURE_DIR / "two_page_resume.pdf"
    ).read_bytes()

    result=extract_pdf(pdf_bytes)

    assert "Built FastAPI services" in result.full_text
    assert "Python and PostgreSQL" in result.full_text

    assert len(result.blocks) == 2
    first_page=result.blocks[0]
    assert first_page.page_number==1
    assert "Built FastAPI services" in first_page.text

    second_page=result.blocks[1]
    assert second_page.page_number == 2
    assert "Python and PostgreSQL" in second_page.text


def test_extract_pdf_rejects_document_without_text()->None:
    buffer=BytesIO()
    writer=PdfWriter()
    writer.add_blank_page(width=612,height=792)
    writer.write(buffer)

    blank_pdf_bytes=buffer.getvalue()

    with pytest.raises(ResumeTextNotFoundError):
        extract_pdf(blank_pdf_bytes)


def test_extract_pdf_rejects_corrupted_pdf() -> None:
    corrupted_pdf_bytes = b"%PDF-1.7\nthis is corrupted\n%%EOF"

    with pytest.raises(ResumeExtractionError):
        extract_pdf(corrupted_pdf_bytes)
        

def test_extract_docx_preserves_text_by_paragraph() -> None:
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("Built FastAPI services")
    document.add_paragraph("")
    document.add_paragraph("Python and PostgreSQL")
    document.save(buffer)

    result = extract_docx(buffer.getvalue())

    assert result.full_text == (
        "Built FastAPI services\n\n"
        "Python and PostgreSQL"
    )
    assert [block.text for block in result.blocks] == [
        "Built FastAPI services",
        "Python and PostgreSQL",
    ]
    assert [block.paragraph_number for block in result.blocks] == [1, 3]


def test_extract_docx_rejects_document_without_text() -> None:
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("   ")
    document.save(buffer)

    blank_docx_bytes = buffer.getvalue()

    with pytest.raises(ResumeTextNotFoundError):
        extract_docx(blank_docx_bytes)


def test_extract_docx_rejects_corrupted_document() -> None:
    corrupted_docx_bytes = b"PK\x03\x04not a real DOCX"

    with pytest.raises(ResumeExtractionError):
        extract_docx(corrupted_docx_bytes)