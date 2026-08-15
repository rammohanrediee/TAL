import json

from openai import AsyncOpenAI

from tal.features.resumes.errors import EvidenceExtractionOutputError
from tal.features.resumes.openai_evidence import EVIDENCE_EXTRACTION_INSTRUCTIONS
from tal.features.resumes.schemas import (
    EvidenceCandidateBatch,
    EvidenceSourceBlock,
)


class OllamaEvidenceClient:
    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise ValueError("model must not be blank")

        self.client = client
        self.model = normalized_model

    async def generate_candidates(
        self,
        *,
        blocks: tuple[EvidenceSourceBlock, ...],
    ) -> object:
        blocks_payload = [block.model_dump(mode="json") for block in blocks]
        response = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": EVIDENCE_EXTRACTION_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": json.dumps(blocks_payload),
                },
            ],
            response_format=EvidenceCandidateBatch,
            temperature=0,
        )

        batch = response.choices[0].message.parsed
        if batch is None:
            raise EvidenceExtractionOutputError()

        return [candidate.model_dump(mode="json") for candidate in batch.candidates]
