
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tal.features.resumes.models import ResumeStatus


class ResumeRead(BaseModel):
    id:UUID
    original_filename:str
    content_type:str
    size_bytes:int
    status:ResumeStatus
    created_at:datetime
    updated_at:datetime
    model_config=ConfigDict(from_attributes=True)