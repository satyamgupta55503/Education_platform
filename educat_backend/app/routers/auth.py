"""
EduCat AI — Auth Router
Endpoints: student phone OTP, teacher Google OAuth2+TOTP, admin email OTP+TOTP
"""
import base64
import io
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

import httpx
import pyotp
import qrcode
import qrcode.image.svg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Tables, db_fetch_one, db_insert, db_update
from app.core.dependencies import get_current_admin, get_current_student
from app.core.firebase import verify_firebase_phone_token
from app.core.redis_client import (
    clear_otp_attempts,
    get_otp_attempts,
    increment_otp_attempts,
    is_locked_out,
    revoke_token,
    set_lockout,
    store_otp,
    verify_otp,
    cache_set,
    cache_get,
)
from app.core.security import (
    create_admin_token,
    create_student_token,
    create_teacher_token,
    decrypt_secret,
    encrypt_secret,
    generate_otp,
    hash_phone,
    verify_token,
)
from app.schemas.schemas import (
    AdminLoginRequest,
    PhoneVerifyOTPRequest,
    QRCodeResponse,
    RefreshTokenRequest,
    TeacherGoogleCallbackRequest,
    TeacherOTPVerifyRequest,
    TeacherTOTPVerifyRequest,
    TokenResponse,
)
import structlog

log = structlog.get_logger()
router = APIRouter()

# ── Admin permissions map ─────────────────────────────────────────
ADMIN_PERMISSIONS = {
    "superadmin": ["all"],
    "admin": ["content", "workspaces", "users", "safety", "subscriptions",
              "coupons", "notifications", "analytics", "support", "assets"],
    "helper": ["content_draft", "safety_review", "support_tier1", "analytics_read",
               "quiz_draft"],
}


# ══════════════════════════════════════════════════════════════════
# STUDENT AUTH — Firebase Phone OTP
# ══════════════════════════════════════════════════════════════════

@router.post("/phone/verify", summary="Verify Firebase Phone OTP and get app JWT")
async def verify_phone(
    request: Request,
    body: PhoneVerifyOTPRequest,
    background: BackgroundTasks,
):
    """
    Verifies Firebase ID token from phone OTP.
    Creates user profile on first login.
    Returns: access_token, refresh_token, user_profile.
    """
    try:
        decoded = await verify_firebase_phone_token(body.firebase_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    uid   = decoded["uid"]
    phone = decoded.get("phone_number", "")
    phone_hash = hash_phone(phone)

    # Fetch or create user
    user = await db_fetch_one(Tables.USERS, {"firebase_uid": uid})

    if not user:
        # New user — create profile
        user = await db_insert(Tables.USERS, {
            "user_id":           str(uuid4()),
            "firebase_uid":      uid,
            "phone_hash":        phone_hash,
            "grade":             body.grade,
            "language":          body.language,
            "subscription_tier": "free",
            "tokens_remaining":  settings.TOKEN_QUOTA_FREE,
            "total_tokens":      settings.TOKEN_QUOTA_FREE,
            "renewal_date":      _next_month_date(),
            "brain_coins":       0,
            "streak_days":       0,
            "cat_config":        {},
            "created_at":        datetime.now(timezone.utc).isoformat(),
        })
        log.info("new_user_created", uid=uid)
    elif user.get("is_suspended"):
        raise HTTPException(status_code=403, detail="Account suspended")
    elif user.get("deleted_at"):
        raise HTTPException(status_code=403, detail="Account deleted")

    # Initialize Redis quota
    background.add_task(
        _init_user_quota,
        user["user_id"],
        user.get("tokens_remaining", settings.TOKEN_QUOTA_FREE),
        user.get("subscription_tier", "free"),
    )

    # Generate tokens
    tokens = create_student_token(
        user_id=user["user_id"],
        tier=user.get("subscription_tier", "free"),
        grade=user.get("grade", 5),
        language=user.get("language", "hi"),
    )

    # Save refresh token family
    await db_insert(Tables.TOKEN_FAMILIES, {
        "family_id":  tokens["family_id"],
        "user_id":    user["user_id"],
        "last_jti":   tokens["refresh_jti"],
        "is_valid":   True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    log.info("student_login_success", user_id=user["user_id"])
    return {
        "success": True,
        "data": {
            "access_token":  tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type":    "Bearer",
            "expires_in":    tokens["expires_in"],
            "user": _format_user_profile(user),
        }
    }


@router.post("/refresh", summary="Refresh access token using refresh token")
async def refresh_token(body: RefreshTokenRequest):
    """
    Token family rotation with replay detection.
    Old refresh token is invalidated, new pair issued.
    """
    try:
        payload = await verify_token(body.refresh_token, expected_type="student_refresh")
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id   = payload["sub"]
    family_id = payload["family_id"]
    old_jti   = payload["jti"]

    # Verify family is valid and JTI matches
    family = await db_fetch_one(Tables.TOKEN_FAMILIES,
                                {"family_id": family_id, "user_id": user_id})
    if not family or not family.get("is_valid"):
        # Family already invalidated → possible replay attack
        log.warning("token_replay_detected", user_id=user_id, family_id=family_id)
        raise HTTPException(status_code=401, detail="Token family invalidated")

    if family["last_jti"] != old_jti:
        # Stolen token used — invalidate entire family
        await db_update(Tables.TOKEN_FAMILIES,
                        {"family_id": family_id},
                        {"is_valid": False})
        log.warning("stolen_token_used", user_id=user_id)
        raise HTTPException(status_code=401, detail="Token invalidated — please login again")

    # Fetch fresh user profile for updated tier/grade
    user = await db_fetch_one(Tables.USERS, {"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tokens = create_student_token(
        user_id=user_id,
        tier=user.get("subscription_tier", "free"),
        grade=user.get("grade", 5),
        language=user.get("language", "hi"),
    )

    # Update family with new JTI
    await db_update(Tables.TOKEN_FAMILIES,
                    {"family_id": family_id},
                    {"last_jti": tokens["refresh_jti"]})

    return {"success": True, "data": {
        "access_token":  tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type":    "Bearer",
        "expires_in":    tokens["expires_in"],
    }}


@router.delete("/logout", summary="Logout — revoke current token")
async def logout(current_user: Annotated[dict, Depends(get_current_student)]):
    jti = current_user.get("jti")
    if jti:
        await revoke_token(jti)
    return {"success": True, "data": {"message": "Logged out successfully"}}


@router.post("/logout", summary="Logout via POST — revoke current token", include_in_schema=False)
async def logout_post(current_user: Annotated[dict, Depends(get_current_student)]):
    """POST alias for logout (frontend compatibility)."""
    jti = current_user.get("jti")
    if jti:
        await revoke_token(jti)
    return {"success": True, "data": {"message": "Logged out successfully"}}


# ══════════════════════════════════════════════════════════════════
# TEACHER AUTH — Google OAuth2 + Email OTP + QR TOTP
# ══════════════════════════════════════════════════════════════════

# ── Teacher Direct OTP (for School Dashboard) ─────────────────────
@router.post("/teacher/otp/send", summary="Send OTP to teacher email directly")
async def teacher_send_otp(request: Request):
    """Direct OTP send for school dashboard (bypasses Google OAuth in dev)."""
    body_data = await request.json()
    email = body_data.get("email", "").lower()
    workspace_id = body_data.get("workspace_id", "")

    if not email:
        raise HTTPException(status_code=422, detail="Email required")

    if await is_locked_out(f"teacher_otp:{email}"):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")

    # Check teacher exists
    teacher = await db_fetch_one(Tables.TEACHERS, {"email": email})
    if not teacher:
        # Don't reveal whether email exists
        return {"success": True, "data": {"otp_sent": True}}

    if not teacher.get("is_active"):
        raise HTTPException(status_code=403, detail="Teacher account is inactive")

    otp = generate_otp(6)
    if settings.ENVIRONMENT == "development":
        otp = "123456"
        log.warning("DEV_MODE_OTP", email=email, otp=otp)

    await store_otp(f"teacher:{email}", otp, ttl_minutes=5)
    log.info("teacher_otp_generated", email=email[:3] + "***",
             dev_otp=otp if settings.ENVIRONMENT == "development" else "[hidden]")

    return {"success": True, "data": {"otp_sent": True}}


@router.post("/teacher/otp/verify", summary="Verify teacher OTP directly")
async def teacher_direct_verify_otp(request: Request):
    """Direct OTP verify for school dashboard."""
    body_data = await request.json()
    email = body_data.get("email", "").lower()
    otp_code = body_data.get("otp_code", "")
    workspace_id = body_data.get("workspace_id", "")

    if not email or not otp_code:
        raise HTTPException(status_code=422, detail="Email and OTP required")

    if await is_locked_out(f"teacher_otp:{email}"):
        raise HTTPException(status_code=429, detail="Account locked. Try again in 15 minutes.")

    otp_valid = await verify_otp(f"teacher:{email}", otp_code)
    if not otp_valid:
        attempts = await increment_otp_attempts(f"teacher_otp:{email}")
        if attempts >= settings.MAX_OTP_ATTEMPTS:
            await set_lockout(f"teacher_otp:{email}")
            raise HTTPException(status_code=429, detail="Too many wrong attempts. Locked for 15 min.")
        raise HTTPException(status_code=400,
                            detail=f"Invalid OTP. {settings.MAX_OTP_ATTEMPTS - attempts} attempts remaining.")

    await clear_otp_attempts(f"teacher_otp:{email}")
    teacher = await db_fetch_one(Tables.TEACHERS, {"email": email})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # In dev mode, skip TOTP and issue token directly
    if settings.ENVIRONMENT == "development":
        token = create_teacher_token(
            teacher_id=teacher["teacher_id"],
            workspace_id=teacher["workspace_id"],
            school_code=teacher.get("school_code", ""),
        )
        return {
            "success": True,
            "access_token": token,
            "requires_totp": False,
            "workspace_id": teacher["workspace_id"],
            "teacher_name": teacher["name"],
        }

    # Production: check if TOTP is needed
    device_count = await db_fetch_one(
        Tables.TEACHER_DEVICES,
        {"teacher_id": teacher["teacher_id"], "revoked_at": None}
    )
    requires_totp = device_count is not None

    if not requires_totp:
        token = create_teacher_token(
            teacher_id=teacher["teacher_id"],
            workspace_id=teacher["workspace_id"],
            school_code=teacher.get("school_code", ""),
        )
        return {
            "success": True,
            "access_token": token,
            "requires_totp": False,
            "setup_totp": True,
            "workspace_id": teacher["workspace_id"],
        }

    return {"success": True, "requires_totp": True, "teacher_id": teacher["teacher_id"],
            "workspace_id": teacher["workspace_id"], "next_step": "verify-totp"}


@router.post("/teacher/google-callback", summary="Handle Google OAuth2 callback for teacher")
async def teacher_google_callback(body: TeacherGoogleCallbackRequest):
    """
    Exchange Google auth code for teacher identity.
    Step 1 of 3: Google OAuth2.
    After this, OTP is sent to teacher email.
    """
    # Exchange code for tokens with Google
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          body.code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  body.redirect_uri,
                "grant_type":    "authorization_code",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Google auth code exchange failed")

    token_data = resp.json()
    id_token_str = token_data.get("id_token")

    # Decode Google ID token (without verification — Google already validated)
    import jwt as pyjwt
    decoded_google = pyjwt.decode(id_token_str, options={"verify_signature": False})
    email = decoded_google.get("email", "").lower()
    name  = decoded_google.get("name", "")

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google token")

    # Check teacher exists and is active
    teacher = await db_fetch_one(Tables.TEACHERS, {"email": email})
    if not teacher:
        raise HTTPException(
            status_code=403,
            detail="This email is not registered as a teacher. Contact your school admin."
        )
    if not teacher.get("is_active"):
        raise HTTPException(status_code=403, detail="Teacher account is inactive")

    # Check lockout
    if await is_locked_out(f"teacher_otp:{email}"):
        raise HTTPException(status_code=429,
                            detail="Too many attempts. Try again in 15 minutes.")

    # Send OTP to teacher email via Supabase Auth
    from app.core.database import get_supabase
    db = await get_supabase()
    otp = generate_otp(6)
    await store_otp(f"teacher:{email}", otp, ttl_minutes=settings.OTP_EXPIRE_MINUTES)

    # In production: send via Supabase Auth email OTP or SendGrid
    # For now, log it (dev only)
    log.info("teacher_otp_generated", email=email[:3] + "***",
             otp="[hidden in production]")

    # Mask email for response
    parts = email.split("@")
    masked = parts[0][:3] + "***@" + parts[1]

    return {"success": True, "data": {
        "otp_sent": True,
        "masked_email": masked,
        "teacher_name": name,
        "next_step": "verify-otp",
    }}


@router.post("/teacher/verify-otp", summary="Verify teacher email OTP")
async def teacher_verify_otp(body: TeacherOTPVerifyRequest):
    """Step 2 of 3: Verify email OTP."""
    email = body.email.lower()

    if await is_locked_out(f"teacher_otp:{email}"):
        raise HTTPException(status_code=429, detail="Account locked. Try again in 15 minutes.")

    otp_valid = await verify_otp(f"teacher:{email}", body.otp)
    if not otp_valid:
        attempts = await increment_otp_attempts(f"teacher_otp:{email}")
        if attempts >= settings.MAX_OTP_ATTEMPTS:
            await set_lockout(f"teacher_otp:{email}")
            raise HTTPException(status_code=429, detail="Too many wrong attempts. Locked for 15 min.")
        raise HTTPException(status_code=400,
                            detail=f"Invalid OTP. {settings.MAX_OTP_ATTEMPTS - attempts} attempts remaining.")

    await clear_otp_attempts(f"teacher_otp:{email}")

    teacher = await db_fetch_one(Tables.TEACHERS, {"email": email})

    # Check if teacher has a registered device
    device_count = await db_fetch_one(
        Tables.TEACHER_DEVICES,
        {"teacher_id": teacher["teacher_id"], "revoked_at": None}
    )

    requires_totp = device_count is not None  # Has registered devices → needs TOTP

    if not requires_totp:
        # First time: issue token + prompt QR setup
        token = create_teacher_token(
            teacher_id=teacher["teacher_id"],
            workspace_id=teacher["workspace_id"],
            school_code=teacher.get("school_code", ""),
        )
        return {"success": True, "data": {
            "access_token": token,
            "requires_totp": False,
            "setup_totp": True,  # Signal: please set up TOTP now
            "workspace_id": teacher["workspace_id"],
        }}

    # Store pending teacher state for TOTP step
    await cache_set(f"teacher_pending:{email}", {
        "teacher_id": teacher["teacher_id"],
        "workspace_id": teacher["workspace_id"],
    }, ttl_seconds=300)

    return {"success": True, "data": {"requires_totp": True, "next_step": "verify-totp"}}


@router.post("/teacher/verify-totp", summary="Verify TOTP code for teacher device")
async def teacher_verify_totp(body: TeacherTOTPVerifyRequest, request: Request):
    """Step 3 of 3: Verify TOTP from authenticator app."""
    # Get pending teacher from cache
    import hashlib
    device_fp = hashlib.sha256(
        f"{body.device_fingerprint}{request.headers.get('user-agent', '')}".encode()
    ).hexdigest()

    # Find teacher by device fingerprint
    device = await db_fetch_one(
        Tables.TEACHER_DEVICES, {"device_fingerprint": device_fp}
    )

    if not device:
        raise HTTPException(status_code=404,
                            detail="Device not registered. Please complete QR code setup.")

    # Decrypt TOTP secret and verify
    try:
        secret = decrypt_secret(device["totp_secret_encrypted"])
    except Exception:
        raise HTTPException(status_code=500, detail="TOTP configuration error")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.totp_code, valid_window=settings.TOTP_VALID_WINDOW):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    teacher_id = device["teacher_id"]
    teacher = await db_fetch_one(Tables.TEACHERS, {"teacher_id": teacher_id})

    # Update last used
    await db_update(Tables.TEACHER_DEVICES,
                    {"device_id": device["device_id"]},
                    {"last_used": datetime.now(timezone.utc).isoformat(),
                     "is_trusted": True})

    token = create_teacher_token(
        teacher_id=teacher_id,
        workspace_id=teacher["workspace_id"],
        school_code=teacher.get("school_code", ""),
    )

    log.info("teacher_login_success", teacher_id=teacher_id)
    return {"success": True, "data": {
        "access_token": token,
        "device_trusted": True,
        "workspace_id": teacher["workspace_id"],
    }}


@router.get("/teacher/qr-code", summary="Generate TOTP QR code for new device")
async def teacher_get_qr_code(
    request: Request,
    current_teacher: Annotated[dict, Depends(
        __import__("app.core.dependencies", fromlist=["get_current_teacher"]).get_current_teacher
    )],
):
    """Generate TOTP QR code for binding new device."""
    teacher_id = current_teacher["sub"]
    teacher    = current_teacher["teacher"]
    email      = teacher["email"]

    # Generate TOTP secret
    secret = pyotp.random_base32()
    totp   = pyotp.TOTP(secret)
    uri    = totp.provisioning_uri(
        name=email,
        issuer_name=settings.TOTP_ISSUER_NAME
    )

    # Generate QR code as SVG
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(uri)
    qr.make(fit=True)
    svg_img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
    svg_buf = io.BytesIO()
    svg_img.save(svg_buf)
    svg_str = svg_buf.getvalue().decode("utf-8")

    # Store pending secret in Redis (expires in 5 min)
    await cache_set(f"totp_pending:{teacher_id}", {
        "secret": secret,
        "teacher_id": teacher_id,
    }, ttl_seconds=300)

    return {"success": True, "data": QRCodeResponse(
        qr_code_svg=svg_str,
        secret_preview=secret[:8],
        instructions={
            "hi": "Google Authenticator app kholo, + dabao, QR code scan karo",
            "en": "Open Google Authenticator, tap +, scan this QR code",
        },
        expires_in=300,
    )}


@router.post("/teacher/confirm-totp-setup", summary="Confirm TOTP setup by verifying first code")
async def teacher_confirm_totp(
    body: TeacherTOTPVerifyRequest,
    request: Request,
    current_teacher: Annotated[dict, Depends(
        __import__("app.core.dependencies", fromlist=["get_current_teacher"]).get_current_teacher
    )],
):
    """Confirm TOTP setup by verifying the first code from authenticator app."""
    teacher_id = current_teacher["sub"]

    # Get pending TOTP secret
    pending = await cache_get(f"totp_pending:{teacher_id}")
    if not pending:
        raise HTTPException(status_code=400, detail="No pending TOTP setup. Generate QR code first.")

    secret = pending["secret"]
    totp = pyotp.TOTP(secret)

    if not totp.verify(body.totp_code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code. Please try scanning again.")

    # Save encrypted device record
    import hashlib as hl
    device_fp = hl.sha256(
        f"{body.device_fingerprint}{request.headers.get('user-agent', '')}".encode()
    ).hexdigest()

    await db_insert(Tables.TEACHER_DEVICES, {
        "device_id":              str(uuid4()),
        "teacher_id":             teacher_id,
        "workspace_id":           current_teacher["workspace_id"],
        "device_fingerprint":     device_fp,
        "device_name":            body.device_name or "School Device",
        "totp_secret_encrypted":  encrypt_secret(secret),
        "is_trusted":             True,
        "last_used":              datetime.now(timezone.utc).isoformat(),
    })

    # Clean up pending
    from app.core.redis_client import get_redis
    r = await get_redis()
    await r.delete(f"totp_pending:{teacher_id}")

    return {"success": True, "data": {"totp_configured": True, "device_name": body.device_name}}


# ── Teacher TOTP Aliases (frontend compatibility) ─────────────────
@router.get("/teacher/totp/setup", summary="TOTP setup alias → same as /teacher/qr-code", include_in_schema=False)
async def teacher_totp_setup_alias(
    request: Request,
    current_teacher: Annotated[dict, Depends(
        __import__("app.core.dependencies", fromlist=["get_current_teacher"]).get_current_teacher
    )],
):
    """Alias: GET /auth/teacher/totp/setup → same handler as /auth/teacher/qr-code."""
    return await teacher_get_qr_code(request, current_teacher)


@router.post("/teacher/totp/verify", summary="TOTP verify alias → same as /teacher/verify-totp", include_in_schema=False)
async def teacher_totp_verify_alias(body: TeacherTOTPVerifyRequest, request: Request):
    """Alias: POST /auth/teacher/totp/verify → same handler as /auth/teacher/verify-totp."""
    return await teacher_verify_totp(body, request)


# ══════════════════════════════════════════════════════════════════
# ADMIN AUTH — Email OTP + TOTP
# ══════════════════════════════════════════════════════════════════

@router.post("/admin/send-otp", summary="Send OTP to admin email")
@router.post("/admin/otp/send", summary="Send OTP to admin email (alias)", include_in_schema=False)
async def admin_send_otp(request: Request):
    # Accept email from query param or JSON body
    email = None
    try:
        body = await request.json()
        email = body.get("email")
    except Exception:
        pass
    if not email:
        from fastapi import Query
        # Fallback: won't reach here if body has email
        raise HTTPException(status_code=422, detail="Email required")

    email = email.lower()
    if await is_locked_out(f"admin:{email}"):
        raise HTTPException(status_code=429, detail="Locked out. Wait 15 minutes.")

    admin = await db_fetch_one(Tables.ADMIN_USERS, {"email": email})
    if not admin or not admin.get("is_active"):
        # Don't reveal whether email exists
        return {"success": True, "data": {"otp_sent": True}}

    otp = generate_otp(6)
    # DEV MODE: Use fixed OTP for development
    if settings.ENVIRONMENT == "development":
        otp = "123456"
        log.warning("DEV_MODE_OTP", email=email, otp=otp)
    await store_otp(f"admin:{email}", otp, ttl_minutes=settings.OTP_ADMIN_EXPIRE_MINUTES)
    # TODO: Send via email provider (SendGrid/Resend)
    log.info("admin_otp_generated", email=email[:4] + "***", dev_otp=otp if settings.ENVIRONMENT == "development" else "[hidden]")
    return {"success": True, "data": {"otp_sent": True}}


@router.post("/admin/login", summary="Admin login: verify OTP + optional TOTP")
@router.post("/admin/otp/verify", summary="Admin OTP verify (alias)", include_in_schema=False)
async def admin_login(request: Request):
    body_data = await request.json()
    email = body_data.get("email", "").lower()
    otp_code = body_data.get("otp") or body_data.get("otp_code", "")
    totp_code = body_data.get("totp_code")

    if not email or not otp_code:
        raise HTTPException(status_code=422, detail="Email and OTP required")

    if await is_locked_out(f"admin_login:{email}"):
        raise HTTPException(status_code=429, detail="Locked out. Wait 15 minutes.")

    # Verify OTP
    otp_valid = await verify_otp(f"admin:{email}", otp_code)
    if not otp_valid:
        attempts = await increment_otp_attempts(f"admin_login:{email}")
        if attempts >= settings.MAX_OTP_ATTEMPTS:
            await set_lockout(f"admin_login:{email}")
        raise HTTPException(status_code=400, detail="Invalid OTP")

    admin = await db_fetch_one(Tables.ADMIN_USERS, {"email": email})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # SuperAdmin: verify TOTP
    if admin["role"] == "superadmin":
        if settings.ENVIRONMENT != "development":
            if not totp_code:
                raise HTTPException(status_code=400, detail="TOTP code required for SuperAdmin")
            try:
                secret = decrypt_secret(admin["totp_secret_encrypted"])
            except Exception:
                raise HTTPException(status_code=500, detail="TOTP not configured. Contact system admin.")

            totp = pyotp.TOTP(secret)
            if not totp.verify(totp_code, valid_window=settings.TOTP_VALID_WINDOW):
                raise HTTPException(status_code=400, detail="Invalid TOTP code")
        else:
            log.warning("DEV_MODE: skipping TOTP for superadmin")

    # Clear lockout
    await clear_otp_attempts(f"admin_login:{email}")

    # Update last login
    await db_update(Tables.ADMIN_USERS, {"admin_id": admin["admin_id"]},
                    {"last_login": datetime.now(timezone.utc).isoformat()})

    permissions = ADMIN_PERMISSIONS.get(admin["role"], [])
    token = create_admin_token(admin["admin_id"], admin["role"], permissions)

    log.info("admin_login_success", admin_id=admin["admin_id"], role=admin["role"])
    return {
        "success": True,
        "access_token": token,
        "token_type":   "Bearer",
        "role":         admin["role"],
        "permissions":  permissions,
        "name":         admin["name"],
    }


@router.post("/admin/totp/verify", summary="Admin TOTP verification (separate step)")
async def admin_totp_verify(request: Request):
    """
    Separate TOTP verification step for admin login.
    Called after OTP is verified, when TOTP is required as second factor.
    """
    body_data = await request.json()
    email = body_data.get("email", "").lower()
    totp_code = body_data.get("totp_code", "")

    if not email or not totp_code:
        raise HTTPException(status_code=422, detail="Email and TOTP code required")

    admin = await db_fetch_one(Tables.ADMIN_USERS, {"email": email})
    if not admin or not admin.get("is_active"):
        raise HTTPException(status_code=404, detail="Admin not found")

    # Verify TOTP
    try:
        secret = decrypt_secret(admin["totp_secret_encrypted"])
    except Exception:
        raise HTTPException(status_code=500, detail="TOTP not configured. Contact system admin.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(totp_code, valid_window=settings.TOTP_VALID_WINDOW):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    # Update last login
    await db_update(Tables.ADMIN_USERS, {"admin_id": admin["admin_id"]},
                    {"last_login": datetime.now(timezone.utc).isoformat()})

    permissions = ADMIN_PERMISSIONS.get(admin["role"], [])
    token = create_admin_token(admin["admin_id"], admin["role"], permissions)

    log.info("admin_totp_verify_success", admin_id=admin["admin_id"], role=admin["role"])
    return {
        "success": True,
        "access_token": token,
        "token_type":   "Bearer",
        "role":         admin["role"],
        "permissions":  permissions,
        "name":         admin["name"],
    }


# ── Helpers ───────────────────────────────────────────────────────
def _next_month_date() -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc).replace(day=1) +
            timedelta(days=32)).replace(day=1).isoformat()


def _format_user_profile(user: dict) -> dict:
    tier_names = {"free": "FREE", "smart": "SMART", "genius": "GENIUS"}
    return {
        "user_id":           user["user_id"],
        "grade":             user.get("grade", 5),
        "language":          user.get("language", "hi"),
        "subscription_tier": user.get("subscription_tier", "free"),
        "tier_display_name": tier_names.get(user.get("subscription_tier", "free"), "FREE"),
        "tokens_remaining":  user.get("tokens_remaining", 25),
        "total_tokens":      user.get("total_tokens", 25),
        "renewal_date":      user.get("renewal_date"),
        "brain_coins":       user.get("brain_coins", 0),
        "streak_days":       user.get("streak_days", 0),
        "cat_config":        user.get("cat_config", {}),
    }


async def _init_user_quota(user_id: str, monthly: int, tier: str):
    from app.core.redis_client import quota_get, quota_init
    existing = await quota_get(user_id)
    if existing == 0:
        await quota_init(user_id, monthly, tier)
