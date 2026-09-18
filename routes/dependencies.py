from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.utils.security import decode_access_token
from backend.models.user import User
from backend.models.admin import Admin

security_bearer = HTTPBearer(auto_error=False)

async def get_token_str(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[str]:
    # 1. Try header
    if creds:
        return creds.credentials
    # 2. Try cookie
    token = request.cookies.get("access_token")
    if token:
        # If token is prefixed with "Bearer ", strip it
        if token.startswith("Bearer "):
            token = token[7:]
        return token
    return None

async def get_current_user(
    token_str: Optional[str] = Depends(get_token_str)
) -> User:
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    payload = decode_access_token(token_str)
    if not payload or payload.get("role") != "user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    user_id = payload.get("sub")
    user = await User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked"
        )
    return user

async def get_current_admin(
    token_str: Optional[str] = Depends(get_token_str)
) -> Admin:
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    payload = decode_access_token(token_str)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token"
        )
    admin_id = payload.get("sub")
    admin = await Admin.get(admin_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account not found"
        )
    if admin.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    return admin
