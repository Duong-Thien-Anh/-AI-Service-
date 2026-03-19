from typing import Annotated

import httpx
from fastapi import Header, HTTPException

from config import settings


async def require_auth(
    authorization: Annotated[str | None, Header()] = None
) -> dict:
    """
    FastAPI dependency - protects any route that uses it.

    If AUTH_MOCK_MODE=true, returns a fake user (useful while Auth Service isn't ready).
    Otherwise, validates the JWT by calling the Auth Service /verify endpoint.
    """
    if settings.auth_mock_mode:
        return {
            "id": "user-001",
            "name": "Test User",
            "email": "test@technova.com",
            "role": "customer",
        }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.auth_service_url}/verify",
                json={"token": token},
                timeout=5.0,
            )
            response.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token ({exc.response.status_code})")

    data = response.json()

    if not data.get("valid"):
        raise HTTPException(status_code=401, detail=data.get("error", "Invalid token"))

    user = data.get("user")
    if not isinstance(user, dict):
        raise HTTPException(status_code=502, detail="Auth service returned invalid user payload")

    return user

