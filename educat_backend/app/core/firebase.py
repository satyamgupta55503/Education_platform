"""
EduCat AI — Firebase Admin SDK
Phone OTP verification + FCM push notifications.
"""
import base64
import json
from functools import lru_cache
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials, messaging

from app.core.config import settings
import structlog

log = structlog.get_logger()

_firebase_app: Optional[firebase_admin.App] = None


def get_firebase_app() -> firebase_admin.App:
    """Initialize Firebase Admin SDK (singleton)."""
    global _firebase_app
    if _firebase_app is None:
        try:
            # Decode base64-encoded service account JSON from env var
            sa_json = base64.b64decode(
                settings.FIREBASE_SERVICE_ACCOUNT_JSON
            ).decode("utf-8")
            sa_dict = json.loads(sa_json)

            cred = credentials.Certificate(sa_dict)
            _firebase_app = firebase_admin.initialize_app(cred, {
                "projectId": settings.FIREBASE_PROJECT_ID,
            })
            log.info("firebase_initialized",
                     project=settings.FIREBASE_PROJECT_ID)
        except Exception as e:
            log.error("firebase_init_failed", error=str(e))
            raise
    return _firebase_app


async def verify_firebase_phone_token(id_token: str) -> dict:
    """
    Verify Firebase Phone Auth ID token.
    Returns decoded token with uid and phone_number.
    Raises: ValueError if token invalid or expired.
    """
    get_firebase_app()
    try:
        decoded = auth.verify_id_token(id_token, check_revoked=True)
        if not decoded.get("phone_number"):
            raise ValueError("Token does not contain phone_number claim")
        log.info("firebase_token_verified", uid=decoded.get("uid"))
        return decoded
    except auth.RevokedIdTokenError:
        raise ValueError("Firebase token has been revoked")
    except auth.ExpiredIdTokenError:
        raise ValueError("Firebase token has expired")
    except auth.InvalidIdTokenError as e:
        raise ValueError(f"Invalid Firebase token: {e}")


async def send_fcm_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    image_url: Optional[str] = None,
) -> bool:
    """
    Send push notification via Firebase Cloud Messaging.
    Returns True on success.
    """
    get_firebase_app()
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
                image=image_url,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    click_action="FLUTTER_NOTIFICATION_CLICK",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default"),
                ),
            ),
        )
        response = messaging.send(message)
        log.info("fcm_sent", message_id=response)
        return True
    except Exception as e:
        log.error("fcm_send_failed", error=str(e), fcm_token=fcm_token[:20])
        return False


async def send_fcm_multicast(
    fcm_tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    """Send to multiple FCM tokens at once (max 500)."""
    get_firebase_app()
    if not fcm_tokens:
        return {"success": 0, "failure": 0}

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=fcm_tokens[:500],
    )
    response = messaging.send_each_for_multicast(message)
    return {
        "success": response.success_count,
        "failure": response.failure_count,
    }
