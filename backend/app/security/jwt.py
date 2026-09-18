import datetime as dt

import jwt

from app.config import settings


def create_access_token(*, subject: str, role: str, business_unit_id: int | None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "bu_id": business_unit_id,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
