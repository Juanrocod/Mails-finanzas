import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_pending_2fa_token,
    create_refresh_token,
    create_totp_setup_token,
    decode_token,
    generate_totp_secret,
    get_totp_provisioning_uri,
    hash_password,
    verify_password,
    verify_totp,
)
from app.models.invite_token import InviteToken
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ConfirmRegisterRequest,
    LoginRequest,
    PendingTokenResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    RegenerateTOTPRequest,
    RegenerateTOTPResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyTOTPRequest,
)
from app.services import session_store
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


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
@limiter.limit("5/minute")
def verify_totp_endpoint(request: Request, body: VerifyTOTPRequest, db: Session = Depends(get_db)):
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
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
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


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    invite = db.query(InviteToken).filter(
        InviteToken.token == body.token,
        InviteToken.tipo == "invite",
        InviteToken.usado_en.is_(None),
    ).first()
    if not invite:
        raise HTTPException(status_code=400, detail="Link de registro inválido o expirado")
    if invite.expira_en < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link de registro inválido o expirado")

    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=409, detail="Nombre de usuario no disponible")

    totp_secret = generate_totp_secret()
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        totp_secret=totp_secret,
        is_active=False,
    )
    db.add(user)
    db.flush()

    totp_uri = get_totp_provisioning_uri(totp_secret, body.username, settings.TOTP_ISSUER)
    setup_token = create_totp_setup_token(str(user.id), str(invite.id))
    db.commit()

    return RegisterResponse(totp_uri=totp_uri, setup_token=setup_token)


@router.post("/register/confirm", status_code=204)
@limiter.limit("5/minute")
def confirm_register(request: Request, body: ConfirmRegisterRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.setup_token)
        if payload.get("type") != "totp_setup":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token de setup inválido o expirado")

    user = db.query(User).filter(
        User.id == UUID(payload["sub"]),
        User.is_active.is_(False),
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado o ya confirmado")

    if not verify_totp(user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Código del Authenticator incorrecto")

    invite = db.get(InviteToken, UUID(payload["invite_token_id"]))
    if invite:
        invite.usado_en = datetime.now(timezone.utc)

    user.is_active = True
    db.commit()


@router.post("/reset-password", status_code=204)
@limiter.limit("3/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_row = db.query(InviteToken).filter(
        InviteToken.token == body.token,
        InviteToken.tipo == "reset",
        InviteToken.usado_en.is_(None),
    ).first()
    if not token_row:
        raise HTTPException(status_code=400, detail="Link de reset inválido o expirado")
    if token_row.expira_en < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link de reset inválido o expirado")

    user = db.query(User).filter(
        User.id == token_row.user_id,
        User.is_active.is_(True),
    ).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado")

    user.hashed_password = hash_password(body.password)
    token_row.usado_en = datetime.now(timezone.utc)
    db.commit()


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()


@router.post("/regenerate-totp", response_model=RegenerateTOTPResponse)
def regenerate_totp(
    body: RegenerateTOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_totp(current_user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Código del Authenticator incorrecto")
    new_secret = generate_totp_secret()
    current_user.totp_secret = new_secret
    db.add(current_user)
    db.commit()
    totp_uri = get_totp_provisioning_uri(new_secret, current_user.username, settings.TOTP_ISSUER)
    return RegenerateTOTPResponse(totp_uri=totp_uri)
