from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = Field(default="GreenCare Backend")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/greencare_db"
    )
    NAS_STORAGE_PATH: str = Field(default="/mnt/nas/greencare")
    LOCAL_STORAGE_PATH: str = Field(default="./storage/images")
    MAX_IMAGE_SIZE_MB: int = Field(default=10)
    # Host uvicorn binds to (0.0.0.0 = all interfaces, reachable from phone on LAN).
    API_BIND_HOST: str = Field(default="0.0.0.0")
    # Port for dev server; keep in sync with uvicorn when not using run_dev.py.
    API_PORT: int = Field(default=8000)
    # Optional: stable URL for this machine (e.g. http://192.168.0.61:8000). Set once; use the same
    # value for golf-disease-mobile EXPO_PUBLIC_API_URL. Router DHCP reservation keeps the IP stable.
    DEV_API_PUBLIC_URL: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

if not settings.SECRET_KEY:
    raise ValueError("SECRET_KEY is empty. Set SECRET_KEY in .env.")

