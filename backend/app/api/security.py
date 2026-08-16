from hmac import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings


async def require_write_access(
    request: Request,
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    settings: Settings = request.app.state.settings
    if settings.write_api_key is None:
        return

    expected = settings.write_api_key.get_secret_value()
    if api_key is None or not compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="a valid X-API-Key is required",
        )
