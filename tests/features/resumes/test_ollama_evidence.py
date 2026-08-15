import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from tal.features.resumes.models import EvidenceType
from tal.features.resumes.ollama_evidence import OllamaEvidenceClient
from tal.features.resumes.openai_evidence import EVIDENCE_EXTRACTION_INSTRUCTIONS
from tal.features.resumes.schemas import (
    EvidenceCandidateBatch,
    EvidenceSourceBlock,
    ExtractedEvidenceCandidate,
)


async def test_ollama_evidence_client_returns_parsed_candidates() -> None:
    # Arrange
    block = EvidenceSourceBlock(
        id=uuid4(),
        text="Built production APIs using Python.",
        page_number=1,
    )
    candidate = ExtractedEvidenceCandidate(
        evidence_type=EvidenceType.SKILL,
        claim_text="Python",
        source_block_id=block.id,
        source_quote="Built production APIs using Python.",
        confidence=0.95,
    )
    parsed_batch = EvidenceCandidateBatch(candidates=[candidate])

    ollama_client = Mock()
    ollama_client.chat.completions.parse = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(parsed=parsed_batch),
                )
            ]
        )
    )
    evidence_client = OllamaEvidenceClient(
        client=ollama_client,
        model="test-ollama-model",
    )

    # Act
    result = await evidence_client.generate_candidates(blocks=(block,))

    # Assert
    assert result == [candidate.model_dump(mode="json")]
    ollama_client.chat.completions.parse.assert_awaited_once_with(
        model="test-ollama-model",
        messages=[
            {
                "role": "system",
                "content": EVIDENCE_EXTRACTION_INSTRUCTIONS,
            },
            {
                "role": "user",
                "content": json.dumps([block.model_dump(mode="json")]),
            },
        ],
        response_format=EvidenceCandidateBatch,
        temperature=0,
    )