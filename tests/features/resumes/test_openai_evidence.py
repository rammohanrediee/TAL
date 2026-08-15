import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from tal.features.resumes.models import EvidenceType
from tal.features.resumes.openai_evidence import (
    EVIDENCE_EXTRACTION_INSTRUCTIONS,
    OpenAIEvidenceClient,
)
from tal.features.resumes.schemas import (
    EvidenceCandidateBatch,
    EvidenceSourceBlock,
    ExtractedEvidenceCandidate,
)


async def test_openai_evidence_client_returns_parsed_candidates() -> None:
    block = EvidenceSourceBlock(
        id=uuid4(),
        text="Built production APIs using Python.",
        page_number=1,
    )
    candidate = ExtractedEvidenceCandidate(
        evidence_type=EvidenceType.SKILL,
        claim_text="python",
        source_block_id=block.id,
        source_quote="Built production APIs using Python.",
        confidence=0.95,
    )
    parsed_batch = EvidenceCandidateBatch(candidates=[candidate])

    openai_client = Mock()
    openai_client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(output_parsed=parsed_batch)
    )
    evidence_client = OpenAIEvidenceClient(
        client=openai_client,
        model="test-evidence-model",
    )

    result = await evidence_client.generate_candidates(blocks=(block,))

    assert result == [candidate.model_dump(mode="json")]
    openai_client.responses.parse.assert_awaited_once_with(
        model="test-evidence-model",
        instructions=EVIDENCE_EXTRACTION_INSTRUCTIONS,
        input=json.dumps([block.model_dump(mode="json")]),
        text_format=EvidenceCandidateBatch,
        store=False,
    )
