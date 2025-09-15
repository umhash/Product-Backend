from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class StudentBase(BaseModel):
    full_name: str
    email: EmailStr


class StudentCreate(StudentBase):
    password: str


class StudentResponse(StudentBase):
    id: int
    is_active: bool
    created_at: datetime
    phone_number: Optional[str] = None
    country_of_origin: Optional[str] = None
    academic_level: Optional[str] = None

    class Config:
        from_attributes = True


class StudentLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: StudentResponse


class TokenData(BaseModel):
    email: Optional[str] = None
