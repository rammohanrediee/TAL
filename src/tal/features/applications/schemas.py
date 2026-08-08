
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from tal.features.applications.models import ApplicationStatus


class ApplicationCreate(BaseModel):
    company_name:str=Field(min_length=1,max_length=200)
    role_title:str=Field(min_length=1,max_length=200)
    status:ApplicationStatus=ApplicationStatus.SAVED
    job_url:HttpUrl | None=None

class ApplicationRead(BaseModel):
    id:UUID
    role_title:str
    company_name:str
    status:ApplicationStatus
    job_url:str| None
    created_at:datetime
    updated_at:datetime
    model_config=ConfigDict(from_attributes=True)

class ApplicationStatusUpdate(BaseModel):
    status:ApplicationStatus