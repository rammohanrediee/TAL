import os

os.environ.setdefault("AUTH_RATE_LIMIT_BACKEND", "memory")
os.environ.setdefault("AUTH_CSRF_ENABLED", "false")
os.environ.setdefault("CHAT_TOOL_SECRET", "test-chat-tool-secret")
os.environ.setdefault("JOB_SCAN_SECRET", "test-job-scan-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")