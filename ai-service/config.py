import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    auth_service_url: str
    auth_mock_mode: bool


settings = Settings(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://localhost:3001"),
    auth_mock_mode=_as_bool(os.getenv("AUTH_MOCK_MODE"), default=True),
)
