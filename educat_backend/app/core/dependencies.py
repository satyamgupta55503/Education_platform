"""
EduCat AI — FastAPI Dependencies (Auth Guards + DB Injection)
Usage:
    student = Depends(get_current_student)
    teacher = Depends(get_current_teacher)
    admin   = Depends(get_current_admin)
"""
from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import Tables, db_fetch_one
from app.core.security import verify_token
import structlog

log = structlog.get_logger()
bearer_scheme = HTTPBearer(auto_error=False)


# ── Extract Token from Header or Cookie ───────────────────────────
async def _get_token(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
    auth_cookie: Annotated[Optional[str], Cookie(alias="auth_token")] = None,
) -> str:
    """Extract Bearer token from Authorization header or auth_token cookie."""
    if credentials and credentials.credentials:
        return credentials.credentials
    if auth_cookie:
        return auth_cookie
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials missing",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── Student Auth Guard ────────────────────────────────────────────
async def get_current_student(
    token: Annotated[str, Depends(_get_token)]
) -> dict:
    """
    Validates student JWT. Returns payload dict with:
    { sub (user_id), tier, grade, lang, jti }
    """
    payload = await verify_token(token, expected_type="student_access")
    return payload


async def get_current_student_with_profile(
    token: Annotated[str, Depends(_get_token)]
) -> dict:
    """Validates JWT and fetches full user profile from DB."""
    payload = await verify_token(token, expected_type="student_access")
    user = await db_fetch_one(Tables.USERS, {"user_id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User profile not found")
    if user.get("is_suspended"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Account suspended. Contact support.")
    if user.get("deleted_at"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Account deleted")
    return {**payload, "profile": user}


# ── Teacher Auth Guard ────────────────────────────────────────────
async def get_current_teacher(
    token: Annotated[str, Depends(_get_token)],
    x_csrf_token: Annotated[Optional[str], Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[Optional[str], Cookie(alias="csrf_token")] = None,
) -> dict:
    """
    Validates teacher JWT. Checks CSRF token.
    Returns payload with workspace_id, school_code.
    """
    payload = await verify_token(token, expected_type="teacher")

    # Fetch teacher from DB to check active status
    teacher = await db_fetch_one(Tables.TEACHERS, {"teacher_id": payload["sub"]})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if not teacher.get("is_active"):
        raise HTTPException(status_code=403, detail="Teacher account inactive")

    # Check workspace is active
    workspace = await db_fetch_one(
        Tables.WORKSPACES, {"workspace_id": payload["workspace_id"]}
    )
    if not workspace or not workspace.get("is_active"):
        raise HTTPException(status_code=403, detail="School workspace is inactive")

    return {**payload, "teacher": teacher, "workspace": workspace}


# ── Admin Auth Guards (Role-based) ────────────────────────────────
async def get_current_admin(
    token: Annotated[str, Depends(_get_token)]
) -> dict:
    """Any admin role (helper, admin, superadmin)."""
    payload = await verify_token(token, expected_type="admin")
    admin = await db_fetch_one(Tables.ADMIN_USERS, {"admin_id": payload["sub"]})
    if not admin or not admin.get("is_active"):
        raise HTTPException(status_code=403, detail="Admin account inactive")
    return {**payload, "admin": admin}


async def get_current_admin_or_above(
    token: Annotated[str, Depends(_get_token)]
) -> dict:
    """Requires admin or superadmin role."""
    payload = await get_current_admin(token)
    if payload.get("role") not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Admin or SuperAdmin role"
        )
    return payload


async def get_current_superadmin(
    token: Annotated[str, Depends(_get_token)]
) -> dict:
    """Requires superadmin role."""
    payload = await get_current_admin(token)
    if payload.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires SuperAdmin role"
        )
    return payload


# ── Rate Limit Keys ───────────────────────────────────────────────
def get_rate_limit_key(request: Request) -> str:
    """Use user_id from JWT if available, else IP."""
    # Try to get user from state (set by middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


def get_remote_address(request: Request) -> str:
    """Get real client IP, considering proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Workspace Scoping ─────────────────────────────────────────────
async def verify_workspace_access(
    workspace_id: str,
    teacher_payload: dict = Depends(get_current_teacher),
) -> str:
    """Ensure teacher is accessing their own workspace."""
    if teacher_payload["workspace_id"] != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not your workspace"
        )
    return workspace_id


# ── Optional Auth (for public + authenticated routes) ─────────────
async def get_optional_student(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
) -> Optional[dict]:
    """Returns student payload if authenticated, None otherwise."""
    if not credentials:
        return None
    try:
        return await verify_token(credentials.credentials, expected_type="student_access")
    except HTTPException:
        return None
