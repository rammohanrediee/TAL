import json

from openai import AsyncOpenAI

from tal.features.resumes.errors import EvidenceExtractionOutputError
from tal.features.resumes.openai_evidence import EVIDENCE_EXTRACTION_INSTRUCTIONS
from tal.features.resumes.schemas import EvidenceSourceBlock


class CloudflareEvidenceClient:
    """Extract evidence with a Workers AI chat model through its OpenAI API."""

    def __init__(self, *, client: AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model

    async def generate_candidates(
        self, *, blocks: tuple[EvidenceSourceBlock, ...]
    ) -> object:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": EVIDENCE_EXTRACTION_INSTRUCTIONS
                    + '\nReturn a JSON object with a "candidates" array. Each item must have '
                    'evidence_type, claim_text, source_block_id, source_quote, and confidence.',
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        [block.model_dump(mode="json") for block in blocks]
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else None
        try:
            payload = json.loads(content or "")
            if not isinstance(payload, dict):
                raise ValueError("Expected an object")
            return payload["candidates"]
        except (ValueError, KeyError, TypeError) as error:
            raise EvidenceExtractionOutputError() from error
