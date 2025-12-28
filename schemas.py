from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str]
    email: Optional[str]
    password: Optional[str]
    role: Optional[str]

class RequestCreate(BaseModel):
    title: str
    description: Optional[str]

class RequestResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    department: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_verified: int
    created_at: datetime

    class Config:
        orm_mode = True

class ActivityLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    timestamp: datetime

    class Config:
        orm_mode = True
