from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from backend.app.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    """
    Verify API key for protected endpoints.
    In development mode or when no SECRET_KEY enforcement is needed, it allows requests.
    """
    if settings.APP_ENV == "development":
        return True
    
    if not api_key or api_key != settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return True

