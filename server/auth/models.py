# backend/auth/models.py
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    is_admin: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None