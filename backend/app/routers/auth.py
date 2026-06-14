from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_pending_2fa_token,
    create_refresh_token,
    decode_token,
    verify_totp,
)
from app.schemas.auth import (
    LoginRequest,
    PendingTokenResponse,
    VerifyTOTPRequest,
    TokenResponse,
    RefreshRequest,
)
from app.models.user import User
from app.services.auth import authenticate_user
from app.core.dependencies import get_current_user
from app.services import session_store

router = APIRouter(prefix="/auth", tags=["auth"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=PendingTokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(body.username, body.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    pending_token = create_pending_2fa_token(subject=str(user.id))
    return PendingTokenResponse(
        pending_token=pending_token,
        message="Ingrese el código de su autenticador",
    )


@router.post("/verify-totp", response_model=TokenResponse)
def verify_totp_endpoint(body: VerifyTOTPRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.pending_token)
        if payload.get("type") != "pending_2fa":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token pendiente inválido o expirado")

    user = db.query(User).filter(User.id == UUID(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=401, detail="Código 2FA inválido")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)):
    session_store.clear_session(str(current_user.id))


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    user = db.query(User).filter(User.id == UUID(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
