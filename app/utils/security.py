from datetime import datetime, timedelta
from time import timezone
from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from app.api.users.models import User
from logs.logging import logger
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_session
from app.utils.token_blacklist import is_token_blacklisted

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


'''
-----------------------------------------------------
|         Token generation for authentication       |
-----------------------------------------------------
'''


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + \
            timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


'''
-----------------------------------------------------
|                Decode JWT token                   |
-----------------------------------------------------
'''


def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def authenticate_user(request: Request):
    """
    Extracts JWT token, validates user, and checks their role/status.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, JSONResponse(content={"detail": "Missing authentication token"}, status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        # Validate token format
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            return None, JSONResponse(content={"detail": "Invalid authentication scheme"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # Check if token is blacklisted
        if is_token_blacklisted(token):
            return None, JSONResponse(content={"detail": "Token has been blacklisted"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        token_type = payload.get("type")

        if token_type != "access":
            return None, JSONResponse(content={"detail": "Invalid token type"}, status_code=status.HTTP_401_UNAUTHORIZED)
        if not user_id:
            return None, JSONResponse(content={"detail": "User ID not found in token"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # Retrieve user from database
        async for session in get_session():
            query = await session.execute(select(User).where(User.id == user_id))
            user = query.scalar_one_or_none()

            if not user:
                return None, JSONResponse(content={"detail": "User not found"}, status_code=status.HTTP_401_UNAUTHORIZED)

            return user, None

    except (JWTError, ValueError):
        logger.error("Invalid token")
        return None, JSONResponse(content={"detail": "Invalid token"}, status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.exception(f"Unexpected authentication error: {e}")
        return None, JSONResponse(content={"detail": "Internal server error"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
