import os
from collections.abc import Iterator

import pytest

from tal.core.rate_limit import _memory_windows

os.environ.setdefault("AUTH_RATE_LIMIT_BACKEND", "memory")
os.environ.setdefault("AUTH_CSRF_ENABLED", "false")
os.environ.setdefault("CHAT_TOOL_SECRET", "test-chat-tool-secret")
os.environ.setdefault("JOB_SCAN_SECRET", "test-job-scan-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")


@pytest.fixture(autouse=True)
def isolate_auth_rate_limit_memory() -> Iterator[None]:
    _memory_windows.clear()
    yield
    _memory_windows.clear()