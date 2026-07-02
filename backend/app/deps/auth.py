"""`require_user` — the single auth dependency for every protected route.

The verified JWT is the only source of user identity; user ids arriving in
request bodies or query strings are never trusted (docs/auth.md #2). Missing,
malformed, expired, or otherwise invalid tokens all return 401. Wrong-user
resource access (403/404) is decided per-endpoint in the service layer once
product routes exist.
"""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.security import verify_supabase_jwt

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
    claims: dict


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail=message, headers={"WWW-Authenticate": "Bearer"})


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("Missing bearer token.")
    try:
        claims = verify_supabase_jwt(credentials.credentials)
    except jwt.InvalidTokenError:
        # Deliberately unspecific: the reason a token failed is not client info.
        raise _unauthorized("Invalid or expired token.")
    sub = claims.get("sub")
    if not sub:
        raise _unauthorized("Invalid or expired token.")
    return CurrentUser(user_id=sub, email=claims.get("email"), claims=claims)
