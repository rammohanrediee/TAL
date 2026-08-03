from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tal.api.router import api_router
from tal.core.config import settings
from tal.core.errors import DomainError
from starlette.middleware.sessions import SessionMiddleware

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Own application startup and shutdown resources."""
    yield


async def domain_error_handler(_: Request, error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": error.code,
            "message": error.message,
        },
    )


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    application.add_exception_handler(DomainError, domain_error_handler)
    application.add_middleware(
    SessionMiddleware,
    secret_key=settings.oauth_state_secret.get_secret_value(),
    same_site="lax",
    https_only=settings.app_env == "production",
)
    return application


app = create_app()


@app.get("/")
def root():
    return {"message": "Welcome to tal "}
