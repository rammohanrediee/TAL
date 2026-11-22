from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from tal.core.rate_limit import AuthRateScope, increment_rate_limit_counter, rate_limit_for_scope
from tal.features.auth.errors import AuthRateLimitedError
def client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


async def _enforce(scope: AuthRateScope, identifier: str) -> None:
    key = f"auth:{scope}:{identifier}"
    limit = rate_limit_for_scope(scope)
    count, retry_after = await increment_rate_limit_counter(key)
    if count > limit:
        raise AuthRateLimitedError(retry_after_seconds=retry_after)


async def rate_limit_register(request: Request) -> None:
    await _enforce("register", client_ip(request))


async def rate_limit_login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> None:
    await _enforce("login", client_ip(request))
    email = form_data.username.strip().lower()
    if email:
        await _enforce("login_email", email)


async def rate_limit_oauth(request: Request) -> None:
    await _enforce("oauth", client_ip(request))