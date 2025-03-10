from datetime import date
import datetime
from turtle import update
from typing import Optional
from venv import create
from click import Option
from pydantic import BaseModel


class UserLoginSchema(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password : str
    role_id: str

class UserResponse(BaseModel):
    id: str
    username: str
    role_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    class Config:
        from_attributes = True

class EditUserRequest(BaseModel):
    username: Optional[str] = None
    password : Optional[str] = None
    role_id: Optional[str] = None
