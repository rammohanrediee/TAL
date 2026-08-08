from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        
    )

    app_name: str = "TAL"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str 
    redis_url: str = "redis://localhost:6379/0"
    secret_key: SecretStr = SecretStr("development-only-change-me")
    access_token_expire_minutes: int = 30
    jwt_secret_key:SecretStr
    jwt_algorithm:str="HS256"
    google_client_id: SecretStr
    google_client_secret: SecretStr
    google_redirect_uri: str
    r2_account_id: str
    r2_access_key_id: SecretStr
    r2_secret_access_key: SecretStr
    r2_bucket_name: str
    r2_endpoint_url: str
    oauth_state_secret: SecretStr
    resume_max_upload_bytes: int = 5 * 1024 * 1024



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
