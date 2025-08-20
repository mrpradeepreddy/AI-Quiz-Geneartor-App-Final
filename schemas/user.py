from pydantic import BaseModel,EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name:str
    role:str
    username:str
    email:EmailStr
    recruiter_code: Optional[str] = None

class UserCreate(UserBase):
    password:str

class UserUpdate(BaseModel):
    name:Optional[str]=None
    email:Optional[EmailStr]=None
    role:Optional[str]=None
    username:Optional[str]=None
    password:Optional[str]=None
    recruiter_code:Optional[str]=None

class User(UserBase):
    id:int 
    created_at:datetime
    updated_at:Optional[datetime]=None

    class Config:
        from_attribute=True

class UserLogin(BaseModel):
    email:EmailStr
    username:str
    password:str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class TokenData(BaseModel):
    username:Optional[str]=None
    id:Optional[int]=None
    role:Optional[str]=None

# New schemas for recruiter code functionality
class RecruiterCodeLink(BaseModel):
    recruiter_code: str

class RecruiterCodeResponse(BaseModel):
    message: str
    recruiter_name: str
    recruiter_id: int
    linked_assessments: list

class RecruiterCodeValidation(BaseModel):
    is_valid: bool
    recruiter_name: Optional[str] = None
    recruiter_id: Optional[int] = None
    message: str