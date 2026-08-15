from uuid import uuid4

import pytest

from tal.features.resumes.errors import EvidenceExtractionOutputError
from tal.features.resumes.schemas import EvidenceSourceBlock
from tal.features.resumes.structured_evidence import (
    StructuredEvidenceExtractor,
)


class InvalidEvidenceModelClient:
    async def generate_candidates(
        self,
        *,
        blocks: tuple[EvidenceSourceBlock, ...],
    ) -> object:
        return [
            {
                "evidence_type": "skill",
                "claim_text": "Python",
                "source_block_id": str(blocks[0].id),
                "source_quote": "Built APIs using Python",
                "confidence": 4.5,
            }
        ]


async def test_structured_extractor_rejects_invalid_model_output() -> None:
    # Arrange
    block = EvidenceSourceBlock(
        id=uuid4(),
        text="Built APIs using Python",
        page_number=1,
    )
    extractor = StructuredEvidenceExtractor(
        client=InvalidEvidenceModelClient(),
    )

    # Act and assert
    with pytest.raises(EvidenceExtractionOutputError):
        await extractor.extract(blocks=(block,))
