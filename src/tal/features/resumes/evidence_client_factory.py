from typing import Literal

from openai import AsyncOpenAI
from pydantic import SecretStr

from tal.core.config import get_settings
from tal.features.resumes.evidence_extraction import EvidenceExtractor
from tal.features.resumes.ollama_evidence import OllamaEvidenceClient
from tal.features.resumes.openai_evidence import OpenAIEvidenceClient
from tal.features.resumes.structured_evidence import (
    EvidenceModelClient,
    StructuredEvidenceExtractor,
)


def create_evidence_model_client(
    *,
    provider: Literal["openai", "ollama"],
    model: str,
    ollama_base_url: str,
    openai_api_key: SecretStr | None,
) -> EvidenceModelClient:
    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=ollama_base_url,
            api_key="ollama",
        )
        return OllamaEvidenceClient(
            client=client,
            model=model,
        )
    if openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is required when EVIDENCE_PROVIDER=openai")

    client = AsyncOpenAI(
        api_key=openai_api_key.get_secret_value(),
    )

    return OpenAIEvidenceClient(
        client=client,
        model=model,
    )


def create_configured_evidence_extractor() -> EvidenceExtractor:
    settings = get_settings()

    client = create_evidence_model_client(
        provider=settings.evidence_provider,
        model=settings.evidence_model,
        ollama_base_url=settings.ollama_base_url,
        openai_api_key=settings.openai_api_key,
    )

    return StructuredEvidenceExtractor(client=client)
