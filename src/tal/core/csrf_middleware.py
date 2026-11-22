from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from tal.features.auth.csrf import csrf_tokens_match, requires_csrf_validation


class CsrfMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        if requires_csrf_validation(request) and not csrf_tokens_match(request):
            response = JSONResponse(
                status_code=403,
                content={
                    "code": "csrf_failed",
                    "message": "CSRF token missing or invalid.",
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)