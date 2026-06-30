from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, model_validator

class UserRole(str, Enum):
    admin = 'admin'
    customer = 'customer'

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    role: UserRole
    is_active: bool

# customer should be able to update only name by themselves
class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)

# only admins can update a user's role
class UserRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole
 
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime