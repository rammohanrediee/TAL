from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal

class UserRegister(BaseModel):
    email:EmailStr
    password:str=Field(min_length=8,max_length=128)

class UserRead(BaseModel):
    id:UUID
    email:EmailStr
    is_active:bool
    created_at:datetime
    updated_at:datetime
    model_config=ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email:EmailStr
    password:str

class TokenResponse(BaseModel):
    access_token:str
    token_type:Literal["bearer"]="bearer"

class GoogleIdentityRead(BaseModel):
    provider: Literal["google"] = "google"
    provider_user_id: str
    email: EmailStr
    name: str | None = None