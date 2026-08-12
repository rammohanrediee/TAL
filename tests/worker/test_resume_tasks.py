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


