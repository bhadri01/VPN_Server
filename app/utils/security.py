from datetime import datetime, timedelta
from time import timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from app.api.users.models import User
from app.logs.logging import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
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


async def authenticate_user(request: Request, db: AsyncSession = Depends(get_session)):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")

        if is_token_blacklisted(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been blacklisted")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        token_type = payload.get("type")

        if token_type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")

        query = await db.execute(select(User).where(User.id == user_id))
        user = query.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return user
    except (JWTError, ValueError):
        logger.error("Invalid token")
        return None, JSONResponse(content={"detail": "Invalid token"}, status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.exception(f"Unexpected authentication error: {e}")
        return None, JSONResponse(content={"detail": "Internal server error"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
