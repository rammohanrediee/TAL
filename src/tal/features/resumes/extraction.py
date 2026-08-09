from dataclasses import dataclass
from io import BytesIO
from zipfile import BadZipFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from docx import Document as DocxDocument
from tal.features.resumes.errors import (
    ResumeExtractionError,
    ResumeTextNotFoundError,
)

@dataclass(frozen=True, slots=True)
class ExtractedBlock:
    text:str
    page_number:int | None=None
    paragraph_number:int | None=None


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    full_text:str
    blocks:tuple[ExtractedBlock,...]


def extract_pdf(data: bytes) -> ExtractedDocument:
    try:
        reader = PdfReader(BytesIO(data))
        blocks: list[ExtractedBlock] = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()

            if not text:
                continue

            blocks.append(
                ExtractedBlock(
                    text=text,
                    page_number=page_number,
                )
            )

    except PdfReadError as exc:
        raise ResumeExtractionError() from exc

    if not blocks:
        raise ResumeTextNotFoundError()

    extracted_blocks = tuple(blocks)

    return ExtractedDocument(
        full_text="\n\n".join(
            block.text for block in extracted_blocks
        ),
        blocks=extracted_blocks,
    )

def extract_docx(data:bytes)->ExtractedDocument:
    try:
            
        document=DocxDocument(BytesIO(data))
    except BadZipFile as exc:
        raise ResumeExtractionError() from exc
    blocks:list[ExtractedBlock]=[]

    for paragraph_number,paragraph in enumerate(
        document.paragraphs,
        start=1
    ):
        text=paragraph.text.strip()

        if not text:
            continue

        blocks.append(
            ExtractedBlock(
                text=text,
                paragraph_number=paragraph_number,
            )
        )
    if not blocks:
        raise ResumeTextNotFoundError()

    extracted_blocks=tuple(blocks)
    return ExtractedDocument(
        full_text="\n\n".join(
            block.text for block in extracted_blocks
        ),
        blocks=extracted_blocks,
    )