from authlib.integrations.starlette_client import OAuth
from tal.core.config import settings


oauth=OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id.get_secret_value(),
    client_secret=settings.google_client_secret.get_secret_value(),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile",
    },
)