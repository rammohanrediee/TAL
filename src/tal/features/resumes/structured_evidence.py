from typing import Protocol

from pydantic import ValidationError

from tal.features.resumes.errors import EvidenceExtractionOutputError
from tal.features.resumes.schemas import (
    EvidenceSourceBlock,
    ExtractedEvidenceCandidate,
)

DEFAULT_MAX_EVIDENCE_CANDIDATES = 100


class EvidenceModelClient(Protocol):
    async def generate_candidates(self, *, blocks: tuple[EvidenceSourceBlock, ...]) -> object: ...


class StructuredEvidenceExtractor:
    def __init__(
        self,
        *,
        client: EvidenceModelClient,
        max_candidates: int = DEFAULT_MAX_EVIDENCE_CANDIDATES,
    ) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")

        self.client = client
        self.max_candidates = max_candidates

    async def extract(
        self,
        *,
        blocks: tuple[EvidenceSourceBlock, ...],
    ) -> tuple[ExtractedEvidenceCandidate, ...]:
        raw_candidates = await self.client.generate_candidates(
            blocks=blocks,
        )
        if not isinstance(raw_candidates, list) or len(raw_candidates) > self.max_candidates:
            raise EvidenceExtractionOutputError()

        try:
            return tuple(
                ExtractedEvidenceCandidate.model_validate(candidate) for candidate in raw_candidates
            )
        except ValidationError as error:
            raise EvidenceExtractionOutputError() from error
