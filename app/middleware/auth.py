"""
API Key Authentication middleware.
"""

from typing import Optional
from fastapi import Request, Security, HTTPException
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(request: Request, api_key: Optional[str] = Security(api_key_header)):
    # 1. Check standard X-API-Key header
    if not api_key:
        api_key = request.headers.get("X-API-Key")
        
    # 2. Check Authorization: Bearer <key> header
    if not api_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            api_key = auth_header.split(" ", 1)[1]
            
    # 3. Check query parameters
    if not api_key:
        api_key = request.query_params.get("api_key")
        
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return api_key
