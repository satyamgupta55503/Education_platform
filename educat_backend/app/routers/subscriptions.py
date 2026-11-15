"""
EduCat AI — Subscriptions Router
Razorpay order creation, payment activation, plan listing.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import razorpay
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.config import settings
from app.core.database import Tables, db_fetch_one, db_insert, db_update
from app.core.dependencies import get_current_student_with_profile
from app.core.security import verify_razorpay_signature
from app.core.redis_client import quota_init
import structlog

log = structlog.get_logger()
router = APIRouter()

# ── Razorpay client ───────────────────────────────────────────────
rzp = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# ── Plan catalogue ────────────────────────────────────────────────
PLANS = {
    "smart_monthly": {
        "plan_id": "smart_monthly", "name": "SMART Plan",
        "tier": "smart", "period": "monthly",
        "price_paise": settings.SMART_PLAN_PRICE_MONTHLY,
        "tokens": settings.TOKEN_QUOTA_SMART,
        "days": 30,
        "features": ["250 exchanges/month","WaveNet HD voice","60-day history","Weekly PDF report","20 premium outfits"],
        "is_popular": True,
    },
    "smart_annual": {
        "plan_id": "smart_annual", "name": "SMART Plan (Annual)",
        "tier": "smart", "period": "annual",
        "price_paise": settings.SMART_PLAN_PRICE_ANNUAL,
        "tokens": settings.TOKEN_QUOTA_SMART,
        "days": 365,
        "features": ["250 exchanges/month","WaveNet HD voice","60-day history","Weekly PDF report","Save 25%"],
        "is_popular": False,
    },
    "genius_monthly": {
        "plan_id": "genius_monthly", "name": "GENIUS Plan",
        "tier": "genius", "period": "monthly",
        "price_paise": settings.GENIUS_PLAN_PRICE_MONTHLY,
        "tokens": settings.TOKEN_QUOTA_GENIUS,
        "days": 30,
        "features": ["600 exchanges/month","WaveNet HD Priority","Permanent history","Real-time dashboard","Full wardrobe"],
        "is_popular": False,
    },
    "genius_annual": {
        "plan_id": "genius_annual", "name": "GENIUS Plan (Annual)",
        "tier": "genius", "period": "annual",
        "price_paise": settings.GENIUS_PLAN_PRICE_ANNUAL,
        "tokens": settings.TOKEN_QUOTA_GENIUS,
        "days": 365,
        "features": ["600 exchanges/month","WaveNet HD Priority","Permanent history","Real-time dashboard","Save 25%"],
        "is_popular": False,
    },
}


@router.get("/plans", summary="List all student subscription plans")
async def list_plans():
    return {"success": True, "data": {"plans": list(PLANS.values())}}


@router.get("/me", summary="Get current subscription status")
async def get_subscription(
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    profile = current_user["profile"]
    tier_names = {"free":"FREE","smart":"SMART","genius":"GENIUS"}
    return {"success": True, "data": {
        "tier":            profile.get("subscription_tier","free"),
        "plan_display":    tier_names.get(profile.get("subscription_tier","free"), "FREE"),
        "tokens_remaining": profile.get("tokens_remaining", 25),
        "total_tokens":    profile.get("total_tokens", 25),
        "renewal_date":    profile.get("renewal_date"),
        "is_active":       not bool(profile.get("deleted_at")),
    }}


@router.post("/create-order", summary="Create Razorpay payment order")
async def create_order(
    plan_id: str,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    user_id = current_user["profile"]["user_id"]

    try:
        order = rzp.order.create({
            "amount":   plan["price_paise"],
            "currency": "INR",
            "receipt":  f"order_{user_id[:8]}_{plan_id}",
            "notes": {
                "user_id": user_id,
                "plan_id": plan_id,
                "tier":    plan["tier"],
            },
        })
    except Exception as e:
        log.error("razorpay_order_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Payment order creation failed")

    # Save pending order
    await db_insert(Tables.SUBSCRIPTIONS, {
        "subscription_id": str(uuid4()),
        "user_id":          user_id,
        "plan_id":          plan_id,
        "tier":             plan["tier"],
        "razorpay_order_id": order["id"],
        "status":           "pending",
        "amount_paise":     plan["price_paise"],
        "created_at":       datetime.now(timezone.utc).isoformat(),
    })

    log.info("razorpay_order_created", user_id=user_id, plan_id=plan_id, order_id=order["id"])
    return {"success": True, "data": {
        "order_id":       order["id"],
        "amount":         plan["price_paise"],
        "currency":       "INR",
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "plan":           plan,
    }}


@router.post("/activate", summary="Activate subscription after successful payment")
async def activate_subscription(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    background: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    # Verify Razorpay signature
    if not verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    user_id = current_user["profile"]["user_id"]

    # Find pending subscription
    sub = await db_fetch_one(
        Tables.SUBSCRIPTIONS,
        {"razorpay_order_id": razorpay_order_id, "user_id": user_id}
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription record not found")

    plan = PLANS.get(sub["plan_id"])
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    renewal_date = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()

    # Update user tier
    await db_update(Tables.USERS, {"user_id": user_id}, {
        "subscription_tier": plan["tier"],
        "tokens_remaining":  plan["tokens"],
        "total_tokens":      plan["tokens"],
        "renewal_date":      renewal_date,
    })

    # Update subscription record
    await db_update(Tables.SUBSCRIPTIONS,
                    {"razorpay_order_id": razorpay_order_id},
                    {"status": "active", "razorpay_payment_id": razorpay_payment_id,
                     "activated_at": datetime.now(timezone.utc).isoformat(),
                     "renewal_date": renewal_date})

    # Reset Redis quota with new limit
    await quota_init(user_id, plan["tokens"], plan["tier"])

    # Send confirmation notification
    background.add_task(_send_activation_notification, user_id, plan["name"])

    log.info("subscription_activated", user_id=user_id, plan=sub["plan_id"], tier=plan["tier"])
    return {"success": True, "data": {
        "tier":          plan["tier"],
        "plan_name":     plan["name"],
        "tokens":        plan["tokens"],
        "renewal_date":  renewal_date,
        "message":       "Plan activated! Ab aur padho! 🎉",
    }}


async def _send_activation_notification(user_id: str, plan_name: str):
    try:
        from app.core.database import get_supabase
        from app.core.firebase import send_fcm_notification
        db = await get_supabase()
        user = await db.table(Tables.USERS).select("fcm_token,language").eq("user_id", user_id).execute()
        if user.data:
            token = user.data[0].get("fcm_token")
            lang  = user.data[0].get("language","hi")
            if token:
                title = "Plan Activated! 🎉" if lang == "en" else "Plan Active Ho Gaya! 🎉"
                body  = f"Your {plan_name} is now active. Happy learning!" if lang == "en" \
                        else f"Tumhara {plan_name} shuru ho gaya. Padhte raho!"
                await send_fcm_notification(token, title, body)
    except Exception as e:
        log.warning("activation_notification_failed", user_id=user_id, error=str(e))
