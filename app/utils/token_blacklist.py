from typing import Dict
from datetime import datetime, timezone, UTC
from jose import jwt
from app.core.config import settings
from app.logs.logging import logger

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

token_blacklist: Dict[str, datetime] = {}


def add_token_to_blacklist(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            expiration = datetime.fromtimestamp(exp_timestamp, tz=UTC)
            token_blacklist[token] = expiration
            logger.info(f"Token '{token}' added to blacklist. Expires at {expiration.strftime('%Y-%m-%d %H:%M:%S')}.")
        else:
            logger.warning("Token does not contain an expiration field.")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired.")
    except jwt.InvalidTokenError:
        logger.error("Invalid token.")


def is_token_blacklisted(token: str) -> bool:
    if token in token_blacklist:
        if datetime.now(timezone.utc) < token_blacklist[token]:
            return True
        else:
            del token_blacklist[token]
    return False


def cleanup_expired_tokens():
    now = datetime.now(timezone.utc)
    tokens_to_remove = [token for token,
                        expiry in token_blacklist.items() if now >= expiry]
    for token in tokens_to_remove:
        del token_blacklist[token]
        logger.info(f"Token '{token}' removed from blacklist.")
