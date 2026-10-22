
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
    )


    login_account_max_attempts: int = Field(default=5, ge=1)
    login_ip_max_attempts: int = Field(default=100, ge=1)
    login_window_minutes: int = Field(default=15, ge=1)


    registration_ip_max_attempts: int = Field(default=5, ge=1)
    registration_window_minutes: int = Field(default=60, ge=1)


    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
