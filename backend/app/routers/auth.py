import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.app_user import AppUser
from app.schemas.auth import LoginRequest, UserOut
from app.security.deps import ACCESS_TOKEN_COOKIE, get_current_user
from app.security.jwt import create_access_token
from app.security.password import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]) -> AppUser:
    user = db.scalar(select(AppUser).where(AppUser.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=str(user.id), role=user.role, business_unit_id=user.business_unit_id)

    # Secure requires HTTPS, with a browser exception for http://localhost —
    # fine for local dev, but any non-localhost deployment must be HTTPS.
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )

    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    db.commit()

    return user


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(ACCESS_TOKEN_COOKIE)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(user: Annotated[AppUser, Depends(get_current_user)]) -> AppUser:
    return user
