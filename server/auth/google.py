# backend/auth/google.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests
from typing import Optional
import os
import logging

from .utils import create_access_token
from .models import Token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# Your Google OAuth credentials (set in .env)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # e.g. 123456789-xxxx.apps.googleusercontent.com

request_adapter = requests.Request()

# In-memory "DB" — will auto-create user on first login
fake_users_db: dict = {}

@router.get("/login/google")
async def login_google():
    """Redirect user to Google login"""
    redirect_uri = f"{os.getenv('PUBLIC_URL', 'http://localhost:8000')}/auth/google/callback"
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code&"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        "scope=openid%20email%20profile&"
        "access_type=offline"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(code: str):
    """Google redirects here after login"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth not configured")

    try:
        # Exchange code for ID token
        idinfo = id_token.verify_oauth2_token(
            code,
            request_adapter,
            GOOGLE_CLIENT_ID
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError("Wrong issuer")

        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')

        # Auto-create user if not exists
        if email not in fake_users_db:
            fake_users_db[email] = {
                "email": email,
                "name": name,
                "picture": picture,
                "is_admin": email.endswith("@refugeefirst.org"),  # optional: admin domain
            }
            logger.info(f"New Google user registered: {email}")

        # Create our own JWT
        access_token = create_access_token(data={"sub": email})

        # Redirect to web app with token
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(f"{frontend_url}?token={access_token}")

    except ValueError as e:
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(status_code=400, detail="Invalid Google login")
    except Exception as e:
        logger.error(f"Google auth failed: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")