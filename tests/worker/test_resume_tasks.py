from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tal.worker.celery_app import celery_app
from tal.worker.tasks import resumes as resume_tasks


def test_process_resume_task_delegates_using_only_resume_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = uuid4()
    processing_runner = AsyncMock()

    monkeypatch.setattr(
        resume_tasks,
        "run_resume_processing",
        processing_runner,
    )

    resume_tasks.process_resume_task.run(str(resume_id))

    processing_runner.assert_awaited_once_with(resume_id)


def test_resume_task_module_is_included_for_worker_discovery() -> None:
    resume_task_module = "tal.worker.tasks.resumes"
    included_modules = celery_app.conf.include
    assert resume_task_module in included_modules



@pytest.mark.asyncio
async def test_run_resume_processing_injects_configured_evidence_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    resume_id = uuid4()
    session = object()
    storage = object()
    evidence_extractor = object()
    processing = AsyncMock()

    session_scope = AsyncMock()
    session_scope.__aenter__.return_value = session
    session_scope.__aexit__.return_value = None

    fake_engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(resume_tasks, "SessionFactory", lambda: session_scope)
    monkeypatch.setattr(resume_tasks, "get_resume_storage", lambda: storage)
    monkeypatch.setattr(
        resume_tasks,
        "create_configured_evidence_extractor",
        lambda: evidence_extractor,
        raising=False,
    )
    monkeypatch.setattr(resume_tasks, "process_resume", processing)
    monkeypatch.setattr(resume_tasks, "engine", fake_engine)

    # Act
    await resume_tasks.run_resume_processing(resume_id)

    # Assert
    processing.assert_awaited_once_with(
        resume_id=resume_id,
        session=session,
        storage=storage,
        evidence_extractor=evidence_extractor,
    )

