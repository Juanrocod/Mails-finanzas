from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class PendingTokenResponse(BaseModel):
    pending_token: str
    message: str


class VerifyTOTPRequest(BaseModel):
    pending_token: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ADR-0008: registro e invite tokens
class RegisterRequest(BaseModel):
    token: str
    username: str
    password: str


class RegisterResponse(BaseModel):
    totp_uri: str
    setup_token: str


class ConfirmRegisterRequest(BaseModel):
    setup_token: str
    totp_code: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RegenerateTOTPRequest(BaseModel):
    totp_code: str


class RegenerateTOTPResponse(BaseModel):
    totp_uri: str
