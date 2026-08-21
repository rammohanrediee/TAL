from unittest.mock import Mock

import pytest
from pydantic import SecretStr

from tal.features.resumes.evidence_client_factory import (
    create_evidence_model_client,
)
from tal.features.resumes.ollama_evidence import OllamaEvidenceClient
from tal.features.resumes.openai_evidence import OpenAIEvidenceClient


def test_create_evidence_model_client_selects_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    sdk_client = Mock()
    sdk_client_factory = Mock(return_value=sdk_client)
    monkeypatch.setattr(
        "tal.features.resumes.evidence_client_factory.AsyncOpenAI",
        sdk_client_factory,
    )

    # Act
    result = create_evidence_model_client(
        provider="ollama",
        model="qwen3.5:4b",
        ollama_base_url="http://localhost:11434/v1",
        openai_api_key=None,
    )

    # Assert
    assert isinstance(result, OllamaEvidenceClient)
    assert result.client is sdk_client
    assert result.model == "qwen3.5:4b"
    sdk_client_factory.assert_called_once_with(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )


def test_create_evidence_model_client_selects_openai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    credential_value = __name__
    sdk_client = Mock()
    sdk_client_factory = Mock(return_value=sdk_client)
    monkeypatch.setattr(
        "tal.features.resumes.evidence_client_factory.AsyncOpenAI",
        sdk_client_factory,
    )

    # Act
    result = create_evidence_model_client(
        provider="openai",
        model="gpt-5-mini",
        ollama_base_url="http://localhost:11434/v1",
        openai_api_key=SecretStr(credential_value),
    )

    # Assert
    assert isinstance(result, OpenAIEvidenceClient)
    assert result.client is sdk_client
    assert result.model == "gpt-5-mini"
    sdk_client_factory.assert_called_once_with(
        api_key=credential_value,
    )


def test_create_evidence_model_client_rejects_missing_openai_key() -> None:
    # Arrange
    provider = "openai"
    model = "gpt-5-mini"
    ollama_base_url = "http://localhost:11434/v1"

    # Act
    with pytest.raises(ValueError) as captured_error:
        create_evidence_model_client(
            provider=provider,
            model=model,
            ollama_base_url=ollama_base_url,
            openai_api_key=None,
        )

    # Assert
    assert str(captured_error.value) == ("OPENAI_API_KEY is required when EVIDENCE_PROVIDER=openai")
