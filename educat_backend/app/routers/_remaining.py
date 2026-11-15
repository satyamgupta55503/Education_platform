"""
EduCat AI — Admin, Teacher, and Webhooks Routers
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.core.config import settings
from app.core.database import Tables, db_fetch_many, db_fetch_one, db_insert, db_update, get_supabase
from app.core.dependencies import (
    get_current_admin,
    get_current_admin_or_above,
    get_current_superadmin,
    get_current_teacher,
)
from app.core.security import generate_otp, verify_razorpay_webhook
from app.schemas.schemas import AdminInviteRequest, WorkspaceCreateRequest
import structlog

log = structlog.get_logger()

# ════════════════════════════════════════════════════════════════
# ADMIN ROUTER
# ════════════════════════════════════════════════════════════════
admin_router = APIRouter()


@admin_router.get("/dashboard", summary="Platform KPI dashboard")
async def dashboard(current_admin: Annotated[dict, Depends(get_current_admin)]):
    db = await get_supabase()
    users_count = await db.table(Tables.USERS).select("user_id", count="exact").execute()
    paid_count  = await db.table(Tables.USERS).select("user_id", count="exact").neq("subscription_tier","free").execute()
    ws_count    = await db.table(Tables.WORKSPACES).select("workspace_id", count="exact").eq("is_active", True).execute()
    safety_q    = await db.table(Tables.CHAT_MESSAGES).select("message_id", count="exact").eq("is_flagged", True).execute()
    return {"success": True, "data": {
        "total_students":    users_count.count or 0,
        "paid_students":     paid_count.count or 0,
        "active_schools":    ws_count.count or 0,
        "safety_queue_depth": safety_q.count or 0,
        "queries_today":     0,  # TODO: Redis counter
        "mrr_estimate":      0,  # TODO: subscription aggregation
    }}


@admin_router.get("/users", summary="List all users with filters")
async def list_users(
    tier: Optional[str] = None,
    grade: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    db = await get_supabase()
    query = db.table(Tables.USERS).select(
        "user_id,grade,language,subscription_tier,tokens_remaining,brain_coins,streak_days,is_suspended,created_at"
    ).is_("deleted_at", None)
    if tier:  query = query.eq("subscription_tier", tier)
    if grade: query = query.eq("grade", grade)
    result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "data": {"users": result.data or []}}


@admin_router.patch("/users/{user_id}/suspend", summary="Suspend or unsuspend user")
async def suspend_user(
    user_id: str,
    suspended: bool,
    reason: str = "",
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    await db_update(Tables.USERS, {"user_id": user_id}, {"is_suspended": suspended})
    await _log_audit(current_admin["sub"], f"user_{'suspend' if suspended else 'unsuspend'}", user_id, reason)
    return {"success": True, "data": {"user_id": user_id, "is_suspended": suspended}}


# ── Workspaces ────────────────────────────────────────────────────
@admin_router.get("/workspaces", summary="List all school workspaces")
async def list_workspaces(
    limit: int = 50, offset: int = 0,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    db = await get_supabase()
    result = await db.table(Tables.WORKSPACES).select("*").order("created_at", desc=True).range(offset, offset+limit-1).execute()
    return {"success": True, "data": {"workspaces": result.data or []}}


@admin_router.post("/workspaces", summary="Create new school workspace")
async def create_workspace(
    body: WorkspaceCreateRequest,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    admin_id = current_admin["sub"]
    # Generate unique school code
    prefix = body.school_name[:3].upper().replace(" ", "")
    school_code = f"{prefix}-{str(uuid4())[:6].upper()}"

    from datetime import timedelta
    plan_days = {"classroom": 30, "institute": 30, "campus_plus": 365}
    expires = (datetime.now(timezone.utc) + timedelta(days=plan_days.get(body.subscription_plan, 30))).isoformat()

    quotas = {"classroom": 10000, "institute": 30000, "campus_plus": 100000}
    workspace = await db_insert(Tables.WORKSPACES, {
        "workspace_id":        str(uuid4()),
        "school_name":         body.school_name,
        "school_code":         school_code,
        "subscription_plan":   body.subscription_plan,
        "max_teachers":        body.max_teachers,
        "monthly_query_quota": quotas.get(body.subscription_plan, 10000),
        "queries_used":        0,
        "is_active":           True,
        "admin_email":         body.admin_email,
        "expires_at":          expires,
        "created_by":          admin_id,
        "created_at":          datetime.now(timezone.utc).isoformat(),
    })
    await _log_audit(admin_id, "workspace_create", workspace["workspace_id"], body.school_name)
    log.info("workspace_created", school=body.school_name, code=school_code)
    return {"success": True, "data": workspace}


@admin_router.patch("/workspaces/{workspace_id}", summary="Update workspace")
async def update_workspace(
    workspace_id: str,
    body: dict,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    allowed = {"max_teachers","monthly_query_quota","is_active","subscription_plan","expires_at"}
    updates = {k: v for k, v in body.items() if k in allowed}
    result  = await db_update(Tables.WORKSPACES, {"workspace_id": workspace_id}, updates)
    await _log_audit(current_admin["sub"], "workspace_update", workspace_id, str(updates))
    return {"success": True, "data": result}


# ── Safety Queue ──────────────────────────────────────────────────
@admin_router.get("/safety/queue", summary="Get flagged conversations")
async def safety_queue(
    limit: int = 50,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    db = await get_supabase()
    result = await db.table(Tables.CHAT_MESSAGES).select(
        "message_id,session_id,content,created_at"
    ).eq("is_flagged", True).order("created_at", desc=True).limit(limit).execute()
    return {"success": True, "data": {"flagged": result.data or [], "count": len(result.data or [])}}


@admin_router.patch("/safety/{message_id}/resolve", summary="Resolve flagged message")
async def resolve_flagged(
    message_id: str,
    action: str,  # safe | escalate | ban_user
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    await db_update(Tables.CHAT_MESSAGES, {"message_id": message_id}, {"is_flagged": False})
    await _log_audit(current_admin["sub"], f"safety_{action}", message_id, "")
    return {"success": True, "data": {"message_id": message_id, "action": action}}


# ── Admin Management (SuperAdmin only) ────────────────────────────
@admin_router.post("/admins/invite", summary="Invite new admin/helper")
async def invite_admin(
    body: AdminInviteRequest,
    current_admin: Annotated[dict, Depends(get_current_superadmin)] = None,
):
    from app.core.security import hash_password
    admin_id = str(uuid4())
    await db_insert(Tables.ADMIN_USERS, {
        "admin_id":   admin_id,
        "email":      body.email.lower(),
        "name":       body.name,
        "role":       body.role,
        "is_active":  True,
        "created_by": current_admin["sub"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _log_audit(current_admin["sub"], "admin_invite", admin_id, body.role)
    return {"success": True, "data": {"admin_id": admin_id, "email": body.email, "role": body.role}}


@admin_router.get("/audit", summary="Audit log (SuperAdmin only)")
async def audit_log(
    limit: int = 100,
    offset: int = 0,
    current_admin: Annotated[dict, Depends(get_current_superadmin)] = None,
):
    db = await get_supabase()
    result = await db.table(Tables.AUDIT_LOG).select("*").order("created_at", desc=True).range(offset, offset+limit-1).execute()
    return {"success": True, "data": {"log": result.data or []}}


async def _log_audit(admin_id: str, action: str, target_id: str, detail: str):
    try:
        await db_insert(Tables.AUDIT_LOG, {
            "log_id":     str(uuid4()),
            "admin_id":   admin_id,
            "action":     action,
            "target_id":  target_id,
            "detail":     detail[:500],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


# ── Admin Dashboard (Rich Endpoints) ─────────────────────────────

@admin_router.get("/dashboard/overview", summary="Full admin dashboard overview")
async def dashboard_overview(current_admin: Annotated[dict, Depends(get_current_admin)]):
    """Returns comprehensive platform metrics for the admin dashboard."""
    db = await get_supabase()

    # User stats
    users_total = await db.table(Tables.USERS).select("user_id", count="exact").is_("deleted_at", None).execute()
    free_count = await db.table(Tables.USERS).select("user_id", count="exact").eq("subscription_tier", "free").is_("deleted_at", None).execute()
    smart_count = await db.table(Tables.USERS).select("user_id", count="exact").eq("subscription_tier", "smart").is_("deleted_at", None).execute()
    genius_count = await db.table(Tables.USERS).select("user_id", count="exact").eq("subscription_tier", "genius").is_("deleted_at", None).execute()

    # Schools
    schools_total = await db.table(Tables.WORKSPACES).select("workspace_id", count="exact").eq("is_active", True).execute()
    schools_data = await db.table(Tables.WORKSPACES).select("subscription_plan").eq("is_active", True).execute()
    by_plan = {}
    for ws in (schools_data.data or []):
        plan = ws.get("subscription_plan", "unknown")
        by_plan[plan] = by_plan.get(plan, 0) + 1

    # Content
    content_total = await db.table(Tables.CONTENT).select("content_id", count="exact").execute()
    content_subjects = await db.table(Tables.CONTENT).select("subject").execute()
    subject_counts = {}
    for c in (content_subjects.data or []):
        subj = c.get("subject", "unknown")
        subject_counts[subj] = subject_counts.get(subj, 0) + 1
    by_subject = [{"subject": k, "count": v} for k, v in subject_counts.items()]

    # Today stats (approximate)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    sessions_today = await db.table(Tables.CHAT_SESSIONS).select("session_id", count="exact").gte("started_at", today_start).execute()
    messages_today = await db.table(Tables.CHAT_MESSAGES).select("message_id", count="exact").gte("created_at", today_start).execute()

    # Cache stats (from Redis if available, else defaults)
    cache_stats = {"semantic_cache_size": 0, "hit_rates_7d": {}, "redis_memory": {"used_memory_mb": 0, "peak_memory_mb": 0}}
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        info = await redis.info("memory")
        cache_stats["redis_memory"]["used_memory_mb"] = round(info.get("used_memory", 0) / (1024 * 1024), 2)
        cache_stats["redis_memory"]["peak_memory_mb"] = round(info.get("used_memory_peak", 0) / (1024 * 1024), 2)
        sem_cache_count = await db.table(Tables.SEMANTIC_CACHE).select("cache_id", count="exact").execute()
        cache_stats["semantic_cache_size"] = sem_cache_count.count or 0
    except Exception:
        pass

    return {"success": True, "data": {
        "status": "ok",
        "users": {
            "total": users_total.count or 0,
            "by_tier": {
                "free": free_count.count or 0,
                "smart": smart_count.count or 0,
                "genius": genius_count.count or 0,
            },
            "growth_30d": [],
        },
        "today": {
            "dau": 0,
            "sessions": sessions_today.count or 0,
            "messages": messages_today.count or 0,
            "tokens_used": 0,
        },
        "this_week": {
            "wau": 0,
            "sessions": 0,
            "tokens_used": 0,
        },
        "schools": {
            "total": schools_total.count or 0,
            "by_plan": [{"plan": k, "count": v} for k, v in by_plan.items()],
        },
        "cache": cache_stats,
        "content": {
            "total_pieces": content_total.count or 0,
            "by_subject": by_subject,
        },
    }}


@admin_router.get("/dashboard/schools", summary="List schools with pagination")
async def dashboard_schools(
    plan_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Returns paginated list of schools for admin dashboard."""
    db = await get_supabase()
    offset = (page - 1) * limit

    query = db.table(Tables.WORKSPACES).select("*", count="exact")
    if plan_type:
        query = query.eq("subscription_plan", plan_type)

    result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    return {"success": True, "data": {
        "schools": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
        "total_pages": ((result.count or 0) + limit - 1) // limit,
    }}


@admin_router.get("/dashboard/revenue", summary="Monthly revenue breakdown")
async def dashboard_revenue(
    months: int = 6,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Returns monthly revenue breakdown from subscriptions."""
    db = await get_supabase()

    # Get active subscriptions to compute revenue
    from datetime import timedelta
    start_date = (datetime.now(timezone.utc) - timedelta(days=months * 30)).isoformat()

    subs = await db.table(Tables.SUBSCRIPTIONS).select(
        "plan_id,status,activated_at,amount"
    ).eq("status", "active").gte("activated_at", start_date).execute()

    # Aggregate by month
    monthly = {}
    for sub in (subs.data or []):
        activated = sub.get("activated_at", "")
        if activated:
            month_key = activated[:7]  # YYYY-MM
            amount = sub.get("amount", 0) or 0
            if month_key not in monthly:
                monthly[month_key] = {"month": month_key, "revenue": 0, "subscriptions": 0}
            monthly[month_key]["revenue"] += amount
            monthly[month_key]["subscriptions"] += 1

    # Sort by month
    revenue_data = sorted(monthly.values(), key=lambda x: x["month"])

    return {"success": True, "data": {
        "months_requested": months,
        "monthly_revenue": revenue_data,
        "total_revenue": sum(m["revenue"] for m in revenue_data),
        "total_subscriptions": sum(m["subscriptions"] for m in revenue_data),
    }}


@admin_router.get("/dashboard/cache-health", summary="Redis and semantic cache health")
async def dashboard_cache_health(
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Returns Redis memory stats and semantic cache metrics."""
    cache_health = {
        "redis": {"status": "unknown", "used_memory_mb": 0, "peak_memory_mb": 0, "connected_clients": 0},
        "semantic_cache": {"total_entries": 0, "hit_rate": 0},
    }

    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        info = await redis.info("memory")
        clients_info = await redis.info("clients")
        cache_health["redis"] = {
            "status": "ok",
            "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
            "peak_memory_mb": round(info.get("used_memory_peak", 0) / (1024 * 1024), 2),
            "connected_clients": clients_info.get("connected_clients", 0),
            "uptime_days": info.get("uptime_in_days", 0),
        }
    except Exception as e:
        cache_health["redis"]["status"] = "error"
        cache_health["redis"]["error"] = str(e)

    try:
        db = await get_supabase()
        sem_count = await db.table(Tables.SEMANTIC_CACHE).select("cache_id", count="exact").execute()
        cache_health["semantic_cache"]["total_entries"] = sem_count.count or 0
    except Exception:
        pass

    return {"success": True, "data": cache_health}


@admin_router.get("/dashboard/alerts", summary="System alerts and warnings")
async def dashboard_alerts(
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Returns system alerts: quota warnings, errors, workspace expiries."""
    db = await get_supabase()
    alerts = []

    # Check workspaces near quota
    try:
        workspaces = await db.table(Tables.WORKSPACES).select(
            "workspace_id,school_name,queries_used,monthly_query_quota,expires_at"
        ).eq("is_active", True).execute()

        for ws in (workspaces.data or []):
            used = ws.get("queries_used", 0)
            quota = ws.get("monthly_query_quota", 10000)
            if quota > 0 and used / quota >= 0.9:
                alerts.append({
                    "type": "quota_warning",
                    "severity": "high" if used >= quota else "medium",
                    "message": f"{ws['school_name']} has used {used}/{quota} queries ({round(used/quota*100)}%)",
                    "workspace_id": ws["workspace_id"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

            # Check expiring workspaces
            expires = ws.get("expires_at")
            if expires:
                try:
                    exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    days_left = (exp_dt - datetime.now(timezone.utc)).days
                    if 0 < days_left <= 7:
                        alerts.append({
                            "type": "expiry_warning",
                            "severity": "medium",
                            "message": f"{ws['school_name']} expires in {days_left} days",
                            "workspace_id": ws["workspace_id"],
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                    elif days_left <= 0:
                        alerts.append({
                            "type": "expired",
                            "severity": "high",
                            "message": f"{ws['school_name']} has expired",
                            "workspace_id": ws["workspace_id"],
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    # Check flagged messages (safety)
    try:
        flagged = await db.table(Tables.CHAT_MESSAGES).select("message_id", count="exact").eq("is_flagged", True).execute()
        if (flagged.count or 0) > 0:
            alerts.append({
                "type": "safety_queue",
                "severity": "medium",
                "message": f"{flagged.count} messages in safety review queue",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception:
        pass

    return {"success": True, "data": {
        "alerts": alerts,
        "total": len(alerts),
    }}


@admin_router.patch("/users/{user_id}/tier", summary="Update user subscription tier")
async def update_user_tier(
    user_id: str,
    request: Request,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    """Update a user's subscription tier (admin action)."""
    body_data = await request.json()
    tier = body_data.get("tier", "")

    valid_tiers = {"free", "smart", "genius"}
    if tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")

    # Get token quotas for the tier
    tier_tokens = {"free": 25, "smart": 200, "genius": 1000}
    tokens = tier_tokens.get(tier, 25)

    updated = await db_update(Tables.USERS, {"user_id": user_id}, {
        "subscription_tier": tier,
        "tokens_remaining": tokens,
        "total_tokens": tokens,
    })

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    # Update Redis quota
    try:
        from app.core.redis_client import quota_init
        await quota_init(user_id, tokens, tier)
    except Exception:
        pass

    await _log_audit(current_admin["sub"], "user_tier_update", user_id, f"tier={tier}")
    log.info("user_tier_updated", user_id=user_id, tier=tier, by=current_admin["sub"])

    return {"success": True, "data": {"user_id": user_id, "tier": tier, "tokens": tokens}}


# ── Export the router ─────────────────────────────────────────────
router = APIRouter()
router.include_router(admin_router)


# ════════════════════════════════════════════════════════════════
# TEACHER ROUTER
# ════════════════════════════════════════════════════════════════
teacher_router = APIRouter()


@teacher_router.post("/lesson/start", summary="Start a new classroom lesson")
async def start_lesson(
    body: dict,
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    teacher_id   = current_teacher["sub"]
    workspace_id = current_teacher["workspace_id"]
    lesson_id    = str(uuid4())

    # Check workspace query quota
    workspace = current_teacher.get("workspace", {})
    if workspace.get("queries_used", 0) >= workspace.get("monthly_query_quota", 10000):
        raise HTTPException(status_code=429, detail="Monthly query quota exhausted for this school")

    from app.core.redis_client import session_set
    await session_set(f"lesson:{lesson_id}", {
        "lesson_id":   lesson_id,
        "teacher_id":  teacher_id,
        "workspace_id": workspace_id,
        "subject":     body.get("subject","science"),
        "topic":       body.get("topic",""),
        "grade":       body.get("grade", 7),
        "class_name":  body.get("class_name",""),
        "messages":    [],
        "started_at":  datetime.now(timezone.utc).isoformat(),
    }, ttl=86400)

    log.info("lesson_started", lesson_id=lesson_id, teacher_id=teacher_id)
    return {"success": True, "data": {"lesson_id": lesson_id, "stream_url": f"/api/v1/teacher/lesson/{lesson_id}/stream"}}


@teacher_router.post("/lesson/{lesson_id}/question", summary="Teacher asks question for projector")
async def lesson_question(
    lesson_id: str,
    background: BackgroundTasks,
    body: dict,
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    from app.core.redis_client import session_get, session_set
    lesson = await session_get(f"lesson:{lesson_id}")
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found or expired")

    question = body.get("question","")
    lang     = body.get("language", "hi")
    subject  = lesson.get("subject","science")
    grade    = lesson.get("grade", 7)
    workspace_id = lesson.get("workspace_id")

    # RAG retrieval
    from app.services.ai.rag_pipeline import get_search_engine
    engine = get_search_engine()
    chunks = await engine.search(question, subject, grade, workspace_id=workspace_id)
    chunk_texts = [c["chunk_text"] for c in chunks]

    # Generate embedding for caching
    from app.services.ai.gemini_service import generate_embedding, stream_chat_response
    q_emb = await generate_embedding(question)

    # Semantic cache check
    from app.services.ai.rag_pipeline import semantic_cache_lookup
    cached = await semantic_cache_lookup(question, q_emb, subject, grade)

    if cached:
        # Publish to lesson channel
        from app.core.redis_client import publish_lesson_event
        await publish_lesson_event(workspace_id, {
            "type": "ai_response", "lesson_id": lesson_id,
            "text": cached, "from_cache": True,
        })
        return {"success": True, "data": {"response": cached, "from_cache": True}}

    # Stream and collect
    full_text = []
    async for event in stream_chat_response(
        question=question, context_chunks=chunk_texts,
        conversation_history=lesson.get("messages",[]),
        grade=grade, subject=subject, language=lang, tier="teacher",
    ):
        if '"type": "token"' in event:
            try:
                data = json.loads(event[6:])
                full_text.append(data.get("content",""))
            except Exception:
                pass

    response = "".join(full_text)

    # Update lesson messages and increment workspace quota
    msgs = lesson.get("messages",[])
    msgs.append({"role":"user","content":question})
    msgs.append({"role":"assistant","content":response})
    lesson["messages"] = msgs[-20:]
    await session_set(f"lesson:{lesson_id}", lesson, ttl=86400)

    # Increment workspace queries_used
    db = await get_supabase()
    await db.rpc("increment_workspace_queries", {"p_workspace_id": workspace_id}).execute()

    # Publish to Supabase Realtime
    from app.core.redis_client import publish_lesson_event
    await publish_lesson_event(workspace_id, {
        "type": "ai_response", "lesson_id": lesson_id, "text": response,
    })
    background.add_task(
        semantic_cache_store_bg, question, response, q_emb, subject, grade
    )
    return {"success": True, "data": {"response": response}}


@teacher_router.get("/lesson/{lesson_id}/stream", summary="SSE stream for live lesson (projector)")
async def lesson_stream(
    lesson_id: str,
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
    request: Request,
):
    from fastapi.responses import StreamingResponse
    import asyncio

    workspace_id = current_teacher["workspace_id"]

    async def event_generator():
        from app.core.redis_client import get_redis
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"lesson:{workspace_id}")
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("data"):
                    yield f"data: {msg['data']}\n\n"
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"lesson:{workspace_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@teacher_router.get("/analytics", summary="Teacher usage analytics")
async def teacher_analytics(current_teacher: Annotated[dict, Depends(get_current_teacher)]):
    workspace = current_teacher.get("workspace", {})
    return {"success": True, "data": {
        "queries_used_this_month": workspace.get("queries_used", 0),
        "queries_remaining": max(0, workspace.get("monthly_query_quota",10000) - workspace.get("queries_used",0)),
        "workspace_plan": workspace.get("subscription_plan","classroom"),
    }}


async def semantic_cache_store_bg(q, r, emb, subject, grade):
    from app.services.ai.rag_pipeline import semantic_cache_store
    try:
        await semantic_cache_store(q, r, emb, subject, grade)
    except Exception:
        pass


# Export teacher router
teacher_router_export = APIRouter()
teacher_router_export.include_router(teacher_router)


# ════════════════════════════════════════════════════════════════
# WEBHOOKS ROUTER
# ════════════════════════════════════════════════════════════════
webhooks_router = APIRouter()


@webhooks_router.post("/razorpay", summary="Razorpay webhook handler")
async def razorpay_webhook(request: Request, background: BackgroundTasks):
    body_bytes = await request.body()
    signature  = request.headers.get("X-Razorpay-Signature", "")

    if not verify_razorpay_webhook(body_bytes, signature):
        log.warning("razorpay_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    log.info("razorpay_webhook_received", event=event)

    if event == "payment.captured":
        background.add_task(_handle_payment_captured, payload)
    elif event == "subscription.charged":
        background.add_task(_handle_subscription_charged, payload)
    elif event in ("payment.failed", "subscription.halted"):
        background.add_task(_handle_payment_failed, payload)

    return {"success": True, "data": {"event": event}}


async def _handle_payment_captured(payload: dict):
    try:
        order_id   = payload["payload"]["payment"]["entity"]["order_id"]
        payment_id = payload["payload"]["payment"]["entity"]["id"]
        db = await get_supabase()
        sub = await db.table(Tables.SUBSCRIPTIONS).select("*").eq("razorpay_order_id", order_id).execute()
        if sub.data:
            record = sub.data[0]
            if record["status"] != "active":
                from app.routers.subscriptions import PLANS
                from app.core.redis_client import quota_init
                plan = PLANS.get(record["plan_id"])
                if plan:
                    from datetime import timedelta
                    renewal = (datetime.now(timezone.utc) + timedelta(days=plan["days"])).isoformat()
                    await db_update(Tables.USERS, {"user_id": record["user_id"]}, {
                        "subscription_tier": plan["tier"],
                        "tokens_remaining": plan["tokens"],
                        "total_tokens": plan["tokens"],
                        "renewal_date": renewal,
                    })
                    await db_update(Tables.SUBSCRIPTIONS, {"razorpay_order_id": order_id}, {
                        "status": "active",
                        "razorpay_payment_id": payment_id,
                        "activated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    await quota_init(record["user_id"], plan["tokens"], plan["tier"])
                    log.info("webhook_subscription_activated", user_id=record["user_id"])
    except Exception as e:
        log.error("webhook_payment_captured_failed", error=str(e))


async def _handle_subscription_charged(payload: dict):
    log.info("subscription_charged_webhook", payload=str(payload)[:200])


async def _handle_payment_failed(payload: dict):
    try:
        order_id = payload["payload"]["payment"]["entity"]["order_id"]
        await db_update(Tables.SUBSCRIPTIONS, {"razorpay_order_id": order_id}, {"status": "failed"})
    except Exception as e:
        log.error("webhook_payment_failed_handler_error", error=str(e))
