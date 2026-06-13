from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    TOTP_ISSUER: str = "GestionMails"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_HOURS: int = 24
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
