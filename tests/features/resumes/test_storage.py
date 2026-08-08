import pytest
from unittest.mock import Mock

from tal.features.resumes.storage import R2StorageBackend


@pytest.mark.asyncio
async def test_r2_object_to_bucket() -> None:
    client = Mock()
    storage = R2StorageBackend(
        client=client,
        bucket_name="test-resumes",
    )
    pdf_bytes = b"%PDF-1.4 test"

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
