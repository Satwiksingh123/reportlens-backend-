from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt is used directly rather than through passlib: passlib 1.7.4 (unmaintained since
# 2020) crashes on bcrypt >= 4.1 while probing the backend, which made user registration
# fail outright ("password cannot be longer than 72 bytes" raised from passlib's own
# internal self-test). bcrypt's API is small enough that the wrapper bought us nothing.

# bcrypt only considers the first 72 bytes of a password and raises if given more, so the
# input is truncated explicitly. Done on BYTES, not characters, since multi-byte (e.g.
# non-ASCII) passwords would otherwise slip past a character-based limit.
_MAX_BCRYPT_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BCRYPT_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except ValueError:
        # malformed/legacy hash in the DB - treat as a failed login, never a 500
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None
