from __future__ import annotations

import datetime as dt

from app.config import settings
from app.security.jwt import create_access_token, decode_access_token


def test_jwt_expiry_is_fifteen_minutes():
    assert settings.jwt_expire_minutes == 15


def test_access_token_exp_claim_is_fifteen_minutes_from_iat():
    token = create_access_token(subject="1", role="hr", business_unit_id=None)
    payload = decode_access_token(token)
    delta = payload["exp"] - payload["iat"]
    assert delta == 15 * 60
