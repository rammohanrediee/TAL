from unittest.mock import Mock

import pytest

from tal.features.resumes.storage import R2StorageBackend


@pytest.mark.asyncio
async def test_r2_object_to_bucket()->None:
    client=Mock()
    storage=R2StorageBackend(
        client=client,
        bucket_name="test-resumes",
    )
    pdf_bytes=b"%PDF-1.4 test"
    await storage.upload(
        storage_key="users/123/resumes/cv.pdf",
        data=pdf_bytes,
        content_type="application/pdf",
    )

    client.put_object.assert_called_once_with(
        Bucket="test-resumes",
        Key="users/123/resumes/cv.pdf",
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

@pytest.mark.asyncio
async def test_r2_downloads_object_from_bucket() -> None:
    client = Mock()
    body = Mock()
    body.read.return_value = b"%PDF-1.4 resume"
    client.get_object.return_value = {"Body": body}

    storage = R2StorageBackend(
        client=client,
        bucket_name="test-resumes",
    )

    result = await storage.download(
        storage_key="users/123/resumes/cv.pdf",
    )

    assert result == b"%PDF-1.4 resume"
    client.get_object.assert_called_once_with(
        Bucket="test-resumes",
        Key="users/123/resumes/cv.pdf",
    )
    body.read.assert_called_once_with()
