import secrets
from typing import Final

from fastapi import Request, Response

from tal.core.config import get_settings, settings

ACCESS_COOKIE: Final = "tal_access_token"
CSRF_COOKIE: Final = "tal_csrf"
CSRF_HEADER: Final = "x-csrf-token"

SAFE_METHODS: Final = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PREFIXES: Final = (
    "/api/v1/auth/token",
    "/api/v1/auth/register",
    "/api/v1/auth/google/",
    "/api/v1/jobs/internal/scan",
    "/api/v1/jobs/internal/chat-search",
    "/api/v1/jobs/internal/profile-summary",
)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _cookie_params() -> dict[str, object]:
    secure = settings.app_env == "production"
    return {
        "path": "/",
        "samesite": "lax",
        "secure": secure,
    }


def set_session_cookies(response: Response, *, access_token: str) -> None:
    params = _cookie_params()
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        **params,
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=generate_csrf_token(),
        httponly=False,
        max_age=settings.access_token_expire_minutes * 60,
        **params,
    )


def set_csrf_cookie(response: Response, *, csrf_token: str | None = None) -> None:
    params = _cookie_params()
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token or generate_csrf_token(),
        httponly=False,
        max_age=settings.access_token_expire_minutes * 60,
        **params,
    )


def clear_session_cookies(response: Response) -> None:
    params = _cookie_params()
    for key, httponly in ((ACCESS_COOKIE, True), (CSRF_COOKIE, False)):
        response.delete_cookie(key=key, httponly=httponly, **params)


def csrf_exempt_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in CSRF_EXEMPT_PREFIXES)


def uses_bearer_authorization(request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    return authorization.lower().startswith("bearer ")


def csrf_tokens_match(request: Request) -> bool:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get(CSRF_HEADER)
    if not cookie_token or not header_token:
        return False
    return secrets.compare_digest(cookie_token, header_token)


def requires_csrf_validation(request: Request) -> bool:
    if not get_settings().auth_csrf_enabled:
        return False
    if request.method in SAFE_METHODS:
        return False
    if csrf_exempt_path(request.url.path):
        return False
    if uses_bearer_authorization(request):
        return False
    return ACCESS_COOKIE in request.cookies