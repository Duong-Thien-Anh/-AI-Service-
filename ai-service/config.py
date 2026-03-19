import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    database_url: str
    context_message_limit: int
    auth_service_url: str
    auth_mock_mode: bool


settings = Settings(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/ai_service",
    ),
    context_message_limit=_as_int(os.getenv("CONTEXT_MESSAGE_LIMIT"), default=20),
    auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://localhost:3001"),
    auth_mock_mode=_as_bool(os.getenv("AUTH_MOCK_MODE"), default=True),
)
