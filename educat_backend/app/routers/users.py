"""
EduCat AI — Remaining Routers: users, content, subscriptions, admin, teacher, webhooks
"""
# ════════════════════════════════════════════════════════════════
# users.py
# ════════════════════════════════════════════════════════════════
from fastapi import APIRouter as _R, Depends as _D, HTTPException, BackgroundTasks, Request
from typing import Annotated
from datetime import datetime, timezone
from app.core.dependencies import get_current_student_with_profile, get_current_admin_or_above
from app.core.database import Tables, db_fetch_one, db_update, db_fetch_many
from app.schemas.schemas import UserUpdateRequest

users_router = _R()

@users_router.get("/me")
async def get_profile(u: Annotated[dict, _D(get_current_student_with_profile)]):
    p = u["profile"]
    tier_map = {"free":"FREE","smart":"SMART","genius":"GENIUS"}
    return {"success": True, "data": {**p, "tier_display_name": tier_map.get(p.get("subscription_tier","free"),"FREE")}}

@users_router.patch("/me")
async def update_profile(body: UserUpdateRequest, u: Annotated[dict, _D(get_current_student_with_profile)]):
    user_id = u["profile"]["user_id"]
    updates = body.model_dump(exclude_none=True)
    fcm_token = updates.pop("fcm_token", None)
    if updates:
        await db_update(Tables.USERS, {"user_id": user_id}, updates)
    if fcm_token:
        await db_update(Tables.USERS, {"user_id": user_id}, {"fcm_token": fcm_token})
    user = await db_fetch_one(Tables.USERS, {"user_id": user_id})
    return {"success": True, "data": user}

@users_router.get("/me/analytics")
async def get_analytics(u: Annotated[dict, _D(get_current_student_with_profile)]):
    from app.core.database import get_supabase
    user_id = u["profile"]["user_id"]
    db = await get_supabase()
    sessions = await db.table(Tables.CHAT_SESSIONS).select("subject,exchange_count,coins_earned,started_at,last_message_at").eq("user_id", user_id).execute()
    quizzes = await db.table(Tables.QUIZ_ATTEMPTS).select("subject,score,total,percentage").eq("user_id", user_id).execute()
    s_data = sessions.data or []
    q_data = quizzes.data or []
    subjects = {}
    for s in s_data:
        sub = s.get("subject","unknown")
        subjects[sub] = subjects.get(sub, 0) + s.get("exchange_count", 0)
    fav = max(subjects, key=subjects.get) if subjects else None
    avg_dur = 0.0
    if s_data:
        durs = []
        for s in s_data:
            if s.get("started_at") and s.get("last_message_at"):
                try:
                    d = (datetime.fromisoformat(s["last_message_at"]) - datetime.fromisoformat(s["started_at"])).seconds/60
                    durs.append(d)
                except: pass
        avg_dur = round(sum(durs)/len(durs), 1) if durs else 0.0
    quiz_scores = [q["percentage"] for q in q_data if q.get("percentage")]
    avg_quiz = round(sum(quiz_scores)/len(quiz_scores), 1) if quiz_scores else 0.0
    return {"success": True, "data": {
        "overview": {
            "total_sessions": len(s_data),
            "total_exchanges": sum(s.get("exchange_count",0) for s in s_data),
            "streak_days": u["profile"].get("streak_days",0),
            "brain_coins": u["profile"].get("brain_coins",0),
            "favourite_subject": fav,
            "avg_session_duration_minutes": avg_dur,
        },
        "quiz_performance": {"total": len(q_data), "avg_percentage": avg_quiz},
    }}

@users_router.delete("/me")
async def delete_account(bg: BackgroundTasks, u: Annotated[dict, _D(get_current_student_with_profile)]):
    user_id = u["profile"]["user_id"]
    await db_update(Tables.USERS, {"user_id": user_id}, {"deleted_at": datetime.now(timezone.utc).isoformat()})
    from app.tasks.celery_app import celery_app
    celery_app.send_task("tasks.schedule_data_purge", args=[user_id], countdown=86400*30)
    return {"success": True, "data": {"message": "Account deletion scheduled in 30 days"}}

@users_router.get("/me/parent-report")
async def parent_report(u: Annotated[dict, _D(get_current_student_with_profile)]):
    from app.core.database import get_supabase
    user_id = u["profile"]["user_id"]
    db = await get_supabase()
    sessions = await db.table(Tables.CHAT_SESSIONS).select("*").eq("user_id", user_id).order("started_at", desc=True).limit(20).execute()
    quizzes  = await db.table(Tables.QUIZ_ATTEMPTS).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
    progress = await db.table(Tables.STUDENT_PROGRESS).select("subject,topic,knowledge_probability").eq("user_id", user_id).order("recorded_at", desc=True).limit(50).execute()
    sub_mastery = {}
    for p in (progress.data or []):
        sub = p["subject"]
        if sub not in sub_mastery:
            sub_mastery[sub] = []
        sub_mastery[sub].append(p["knowledge_probability"])
    mastery_avg = {k: round(sum(v)/len(v)*100,1) for k,v in sub_mastery.items()}
    return {"success": True, "data": {
        "recent_sessions": sessions.data or [],
        "recent_quizzes":  quizzes.data or [],
        "subject_mastery_pct": mastery_avg,
    }}

# Export as module-level router
from fastapi import APIRouter
router = APIRouter()
router.include_router(users_router)
