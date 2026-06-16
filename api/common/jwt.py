from datetime import datetime, timedelta, timezone

from api.config.settings import settings
from jose import jwt


def create_access_token(user_id: str) -> str:
    """Create a JWT access token for the given user ID."""
    expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + expires_delta,
        "iat": now,
        "type": "access",
        "jti": _generate_jti(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token for the given user ID."""
    expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": now + expires_delta,
        "iat": now,
        "type": "refresh",
        "jti": _generate_jti(),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Returns the payload dict if valid.
    Raises ExpiredSignatureError if token is expired.
    Raises InvalidTokenError if token is invalid.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def _generate_jti() -> str:
    """Generate a random JWT ID."""
    import secrets

    return secrets.token_hex(16)
