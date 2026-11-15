"""
EduCat AI — Security: JWT (RS256), Fernet Encryption, Hashing
"""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from cryptography.fernet import Fernet
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis_client import is_token_revoked
import structlog

log = structlog.get_logger()

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet: Optional[Fernet] = None


def get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.FERNET_KEY.encode())
    return _fernet


# ── Hashing ───────────────────────────────────────────────────────
def hash_phone(phone: str) -> str:
    """SHA-256 hash of phone number. Never store raw phone."""
    return hashlib.sha256(phone.encode()).hexdigest()


def hash_text(text: str) -> str:
    """SHA-256 hash for cache keys."""
    return hashlib.sha256(text.encode()).hexdigest()


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── Fernet Symmetric Encryption (TOTP secrets) ────────────────────
def encrypt_secret(plaintext: str) -> str:
    """Encrypt TOTP secret with AES-256-GCM via Fernet."""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt TOTP secret."""
    return get_fernet().decrypt(ciphertext.encode()).decode()


# ── JWT Creation ──────────────────────────────────────────────────
def create_student_token(
    user_id: str,
    tier: str,
    grade: int,
    language: str,
) -> dict:
    """Create RS256 student access + refresh token pair."""
    jti = str(uuid4())
    family_id = str(uuid4())
    now = datetime.now(timezone.utc)

    access_payload = {
        "sub": user_id,
        "type": "student_access",
        "tier": tier,
        "grade": grade,
        "lang": language,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS),
    }
    refresh_jti = str(uuid4())
    refresh_payload = {
        "sub": user_id,
        "type": "student_refresh",
        "family_id": family_id,
        "jti": refresh_jti,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return {
        "access_token": _encode(access_payload),
        "refresh_token": _encode(refresh_payload),
        "token_type": "Bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        "family_id": family_id,
        "refresh_jti": refresh_jti,
    }


def create_teacher_token(
    teacher_id: str,
    workspace_id: str,
    school_code: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": teacher_id,
        "type": "teacher",
        "workspace_id": workspace_id,
        "school_code": school_code,
        "role": "teacher",
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_TEACHER_EXPIRE_HOURS),
    }
    return _encode(payload)


def create_admin_token(admin_id: str, role: str, permissions: list[str]) -> str:
    now = datetime.now(timezone.utc)
    expire_hours = {
        "superadmin": settings.JWT_ADMIN_EXPIRE_HOURS,
        "admin": settings.JWT_ADMIN_EXPIRE_HOURS,
        "helper": settings.JWT_HELPER_EXPIRE_HOURS,
    }.get(role, 4)

    payload = {
        "sub": admin_id,
        "type": "admin",
        "role": role,
        "permissions": permissions,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
    }
    return _encode(payload)


def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


# ── JWT Verification ──────────────────────────────────────────────
async def verify_token(token: str, expected_type: Optional[str] = None) -> dict:
    """
    Verify RS256 JWT. Check revocation. Return payload.
    Raises: HTTPException on any failure.
    """
    from fastapi import HTTPException, status

    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expired")
    except JWTError as e:
        log.warning("jwt_decode_failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token")

    # Check revocation list
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has been revoked")

    if expected_type and payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Wrong token type: expected {expected_type}")

    return payload


# ── CSRF Token ────────────────────────────────────────────────────
def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_token: str, header_token: str) -> bool:
    return secrets.compare_digest(cookie_token, header_token)


# ── OTP Generation ────────────────────────────────────────────────
def generate_otp(length: int = 6) -> str:
    """Cryptographically secure OTP."""
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


# ── Razorpay HMAC Verification ────────────────────────────────────
import hmac


def verify_razorpay_signature(
    order_id: str,
    payment_id: str,
    signature: str,
) -> bool:
    """Verify Razorpay payment signature."""
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return secrets.compare_digest(expected, signature)


def verify_razorpay_webhook(payload: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return secrets.compare_digest(expected, signature)
