from typing import Literal

from openai import AsyncOpenAI
from pydantic import SecretStr

from tal.core.config import get_settings
from tal.features.resumes.cloudflare_evidence import CloudflareEvidenceClient
from tal.features.resumes.evidence_extraction import EvidenceExtractor
from tal.features.resumes.ollama_evidence import OllamaEvidenceClient
from tal.features.resumes.openai_evidence import OpenAIEvidenceClient
from tal.features.resumes.structured_evidence import (
    EvidenceModelClient,
    StructuredEvidenceExtractor,
)


def create_evidence_model_client(
    *,
    provider: Literal["openai", "ollama", "neon", "cloudflare"],
    model: str,
    ollama_base_url: str,
    openai_api_key: SecretStr | None,
    neon_ai_gateway_base_url: str | None = None,
    neon_ai_gateway_token: SecretStr | None = None,
    cloudflare_account_id: str | None = None,
    cloudflare_ai_api_token: SecretStr | None = None,
) -> EvidenceModelClient:
    if provider == "cloudflare":
        if not cloudflare_account_id or cloudflare_ai_api_token is None:
            raise ValueError("Cloudflare account ID and CLOUDFLARE_AI_API_TOKEN are required")
        client = AsyncOpenAI(
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account_id}/ai/v1",
            api_key=cloudflare_ai_api_token.get_secret_value(),
        )
        return CloudflareEvidenceClient(client=client, model=model)
    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=ollama_base_url,
            api_key="ollama",
        )
        return OllamaEvidenceClient(
            client=client,
            model=model,
        )
    if provider == "neon":
        if not neon_ai_gateway_base_url or neon_ai_gateway_token is None:
            raise ValueError("NEON_AI_GATEWAY_BASE_URL and NEON_AI_GATEWAY_TOKEN are required")
        client = AsyncOpenAI(
            base_url=f"{neon_ai_gateway_base_url.rstrip('/')}/openai/v1",
            api_key=neon_ai_gateway_token.get_secret_value(),
        )
        return OpenAIEvidenceClient(client=client, model=model)
    if openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is required when EVIDENCE_PROVIDER=openai")

    client = AsyncOpenAI(
        api_key=openai_api_key.get_secret_value(),
    )

    return OpenAIEvidenceClient(
        client=client,
        model=model,
    )


def create_configured_evidence_extractor() -> EvidenceExtractor | None:
    settings = get_settings()
    if settings.evidence_provider == "none":
        return None

    client = create_evidence_model_client(
        provider=settings.evidence_provider,
        model=settings.evidence_model,
        ollama_base_url=settings.ollama_base_url,
        openai_api_key=settings.openai_api_key,
        neon_ai_gateway_base_url=settings.neon_ai_gateway_base_url,
        neon_ai_gateway_token=settings.neon_ai_gateway_token,
        cloudflare_account_id=settings.r2_account_id,
        cloudflare_ai_api_token=settings.cloudflare_ai_api_token,
    )

    return StructuredEvidenceExtractor(client=client)
