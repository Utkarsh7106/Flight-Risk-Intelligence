from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.app_user import AppUser
from app.security.jwt import decode_access_token

ACCESS_TOKEN_COOKIE = "access_token"


def _set_rls_context(db: Session, *, role: str, business_unit_id: int | None) -> None:
    """Mirrors the caller's role/BU into Postgres session variables for this
    transaction only (SET LOCAL semantics via set_config's is_local=true).

    This is the second, independent layer of access control described in
    ARCHITECTURE.md — RLS policies on employee/departure_event read these
    variables directly, so a bug in the app-level role check below does not
    by itself expose cross-BU data. set_config (not SET) is used because SET
    does not accept bound parameters; string concatenation here would be a
    SQL injection risk.
    """
    db.execute(text("SELECT set_config('app.current_role', :role, true)"), {"role": role})
    db.execute(
        text("SELECT set_config('app.current_bu_id', :bu_id, true)"),
        {"bu_id": str(business_unit_id) if business_unit_id is not None else ""},
    )


def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> AppUser:
    unauthenticated = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if access_token is None:
        raise unauthenticated

    try:
        payload = decode_access_token(access_token)
    except jwt.PyJWTError:
        raise unauthenticated

    user_id = payload.get("sub")
    if user_id is None:
        raise unauthenticated

    user = db.get(AppUser, int(user_id))
    if user is None or not user.is_active:
        raise unauthenticated

    _set_rls_context(db, role=user.role, business_unit_id=user.business_unit_id)

    return user


def require_role(*roles: str):
    def _dependency(user: Annotated[AppUser, Depends(get_current_user)]) -> AppUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
        return user

    return _dependency


require_hr = require_role("hr")
