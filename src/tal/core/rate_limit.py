import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Literal

from tal.core.config import get_settings

logger = logging.getLogger(__name__)

AuthRateScope = Literal["register", "login", "login_email", "oauth"]


@dataclass
class _MemoryWindow:
    count: int
    reset_at: float


_memory_lock = asyncio.Lock()
_memory_windows: dict[str, _MemoryWindow] = {}


async def _memory_increment(key: str, window_seconds: int) -> int:
    now = time.monotonic()
    async with _memory_lock:
        window = _memory_windows.get(key)
        if window is None or window.reset_at <= now:
            window = _MemoryWindow(count=0, reset_at=now + window_seconds)
            _memory_windows[key] = window
        window.count += 1
        return window.count


def _memory_retry_after(key: str, window_seconds: int) -> int:
    window = _memory_windows.get(key)
    if window is None:
        return window_seconds
    return max(1, int(window.reset_at - time.monotonic()))


_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as redis

        _redis_client = redis.from_url(
            get_settings().redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def _redis_increment(key: str, window_seconds: int) -> int:
    client = _get_redis()
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, window_seconds)
    return int(count)


async def _redis_retry_after(key: str) -> int:
    client = _get_redis()
    ttl = await client.ttl(key)
    if ttl is None or ttl < 0:
        return get_settings().auth_rate_limit_window_seconds
    return int(ttl)


async def increment_rate_limit_counter(key: str) -> tuple[int, int]:
    """Return the new count and suggested retry-after seconds when limited."""
    settings = get_settings()
    window = settings.auth_rate_limit_window_seconds
    full_key = f"ratelimit:{key}"
    if settings.auth_rate_limit_backend == "memory":
        count = await _memory_increment(full_key, window)
        retry_after = _memory_retry_after(full_key, window)
        return count, retry_after
    try:
        count = await _redis_increment(full_key, window)
        retry_after = await _redis_retry_after(full_key)
        return count, retry_after
    except Exception as error:
        logger.exception("Auth rate limit Redis error for key %s", key)
        if settings.app_env == "production":
            raise
        count = await _memory_increment(full_key, window)
        retry_after = _memory_retry_after(full_key, window)
        return count, retry_after


def rate_limit_for_scope(scope: AuthRateScope) -> int:
    settings = get_settings()
    if scope == "register":
        return settings.auth_rate_limit_register_per_minute
    if scope == "login":
        return settings.auth_rate_limit_login_per_minute
    if scope == "login_email":
        return settings.auth_rate_limit_login_email_per_minute
    return settings.auth_rate_limit_oauth_per_minute