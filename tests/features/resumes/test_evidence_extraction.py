from uuid import uuid4

import pytest
from pydantic import ValidationError

from tal.features.resumes.models import EvidenceType
from tal.features.resumes.schemas import ExtractedEvidenceCandidate


def test_candidate_rejects_blank_source_quote() -> None:
    candidate = {
        "evidence_type": EvidenceType.SKILL,
        "claim_text": "FastAPI",
        "source_block_id": uuid4(),
        "source_quote": "  ",
        "confidence": 0.9,
    }

    with pytest.raises(ValidationError):
        ExtractedEvidenceCandidate.model_validate(candidate)
