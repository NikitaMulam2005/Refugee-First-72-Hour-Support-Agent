# backend/auth/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict

from .utils import create_access_token, verify_password, get_password_hash
from .google import router as google_router  # ← Google OAuth routes

# Main auth router
router = APIRouter(prefix="/auth", tags=["auth"])

# Include Google login routes
router.include_router(google_router)

# In-memory user DB (replace with PostgreSQL/MongoDB later)
fake_users_db: Dict[str, dict] = {
    "admin@refugeefirst.org": {
        "email": "admin@refugeefirst.org",
        "hashed_password": get_password_hash("refugee2025!"),
        "name": "Admin",
        "is_admin": True,
    }
}

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

@router.post("/signup")
async def signup(user: UserCreate):
    if user.email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    fake_users_db[user.email] = {
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "name": user.name,
        "is_admin": False,
    }
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}