import asyncio
from typing import Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from tal.core.config import Settings, get_settings


class StorageBackend(Protocol):
    async def upload(
        self,
        *,
        storage_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Store one private résumé object."""
        ...

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        """Delete one private résumé object."""
        ...


class R2StorageBackend:
    def __init__(
        self,
        *,
        client: BaseClient,
        bucket_name: str,
    ) -> None:
        self._client = client
        self._bucket_name = bucket_name

    async def upload(
        self,
        *,
        storage_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket_name,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
        )

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket_name,
            Key=storage_key,
        )


def get_resume_storage() -> StorageBackend:
    settings: Settings = get_settings()

    client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=(
            settings.r2_secret_access_key.get_secret_value()
        ),
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )

    return R2StorageBackend(
        client=client,
        bucket_name=settings.r2_bucket_name,
    )
