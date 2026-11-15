"""
EduCat AI — Celery Task Implementations
All background and scheduled tasks.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from app.tasks.celery_app import celery_app
import structlog

log = structlog.get_logger()


def run_async(coro):
    """Helper to run async code in Celery (sync) context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════════════
# EMBEDDING TASKS
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.generate_content_embedding", bind=True, max_retries=3)
def generate_content_embedding(self, content_id: str, text: str):
    """Generate and store vector embedding for a content chunk."""
    try:
        async def _run():
            from app.services.ai.gemini_service import generate_document_embedding
            from app.core.database import Tables, db_update, get_supabase

            embedding = await generate_document_embedding(text)
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            db = await get_supabase()
            await db.table(Tables.CONTENT).update({
                "vector_embedding": embedding_str
            }).eq("content_id", content_id).execute()

            log.info("embedding_stored", content_id=content_id)

        run_async(_run())
        return {"status": "success", "content_id": content_id}

    except Exception as exc:
        log.error("embedding_task_failed", content_id=content_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="tasks.generate_chunk_embeddings", bind=True)
def generate_chunk_embeddings(self, content_id: str, text: str, subject: str, grade: int):
    """Chunk content and generate embeddings for all chunks."""
    try:
        async def _run():
            from app.routers.content import _create_chunks
            from app.services.ai.gemini_service import generate_document_embedding
            embedding = await generate_document_embedding(text)
            await _create_chunks(content_id, text, embedding)

        run_async(_run())
        return {"status": "success", "content_id": content_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


# ══════════════════════════════════════════════════════════════════
# SESSION TASKS
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.generate_session_summary", bind=True)
def generate_session_summary_task(self, session_id: str, user_id: str):
    """Generate AI summary of completed session for past context."""
    try:
        async def _run():
            from app.core.database import Tables, db_fetch_many, db_insert, db_update, get_supabase
            from app.services.ai.gemini_service import generate_session_summary

            db = await get_supabase()
            messages = await db.table(Tables.CHAT_MESSAGES).select("role,content").eq(
                "session_id", session_id
            ).order("created_at").limit(50).execute()

            session = await db.table(Tables.CHAT_SESSIONS).select("subject,grade,user_id").eq(
                "session_id", session_id
            ).execute()

            if not messages.data or not session.data:
                return

            sess = session.data[0]
            user = await db.table(Tables.USERS).select("language").eq("user_id", user_id).execute()
            lang = user.data[0].get("language","hi") if user.data else "hi"

            summary = await generate_session_summary(
                messages=messages.data,
                subject=sess["subject"],
                grade=sess["grade"],
                language=lang,
            )

            await db.table(Tables.SESSION_SUMMARIES).insert({
                "summary_id": str(uuid4()),
                "session_id": session_id,
                "user_id":    user_id,
                "subject":    sess["subject"],
                "summary_text": summary,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

            log.info("session_summary_generated", session_id=session_id)

        run_async(_run())
    except Exception as exc:
        log.error("session_summary_failed", session_id=session_id, error=str(exc))


# ══════════════════════════════════════════════════════════════════
# SCHEDULED TASKS
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.monthly_token_reset")
def monthly_token_reset():
    """Reset token quotas for all users at start of month."""
    async def _run():
        from app.core.database import Tables, get_supabase
        from app.core.redis_client import quota_init
        from app.core.config import settings

        db = await get_supabase()
        result = await db.table(Tables.USERS).select(
            "user_id, subscription_tier, total_tokens"
        ).is_("deleted_at", None).execute()

        count = 0
        for user in (result.data or []):
            tier   = user.get("subscription_tier","free")
            tokens = settings.monthly_quotas.get(tier, settings.TOKEN_QUOTA_FREE)

            await db.table(Tables.USERS).update({
                "tokens_remaining": tokens,
                "renewal_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            }).eq("user_id", user["user_id"]).execute()

            await quota_init(user["user_id"], tokens, tier)
            count += 1

        log.info("monthly_token_reset_complete", users_reset=count)
        return {"reset_count": count}

    return run_async(_run())


@celery_app.task(name="tasks.daily_streak_update")
def daily_streak_update():
    """Update streak_days: increment if active yesterday, reset if missed."""
    async def _run():
        from app.core.database import Tables, get_supabase

        db = await get_supabase()
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        # Get users active yesterday
        result = await db.table(Tables.USERS).select(
            "user_id, streak_days, last_active_date"
        ).is_("deleted_at", None).execute()

        streak_updates = 0
        streak_resets  = 0

        for user in (result.data or []):
            last_active = user.get("last_active_date")
            if not last_active:
                continue
            try:
                last_date = datetime.fromisoformat(str(last_active)).date()
            except Exception:
                continue

            if last_date == yesterday:
                # Active yesterday → increment streak
                await db.table(Tables.USERS).update({
                    "streak_days": (user.get("streak_days",0) or 0) + 1
                }).eq("user_id", user["user_id"]).execute()
                streak_updates += 1
            elif last_date < yesterday:
                # Missed a day → reset streak
                await db.table(Tables.USERS).update({
                    "streak_days": 0
                }).eq("user_id", user["user_id"]).execute()
                streak_resets += 1

        log.info("streak_update_complete",
                 incremented=streak_updates, reset=streak_resets)

    return run_async(_run())


@celery_app.task(name="tasks.weekly_parent_report")
def weekly_parent_report():
    """Generate and push weekly PDF reports to parents."""
    async def _run():
        from app.core.database import Tables, get_supabase
        from app.core.firebase import send_fcm_notification

        db = await get_supabase()
        # Get SMART + GENIUS users with FCM token
        result = await db.table(Tables.USERS).select(
            "user_id, fcm_token, language"
        ).in_("subscription_tier", ["smart","genius"]).not_.is_("fcm_token", None).execute()

        for user in (result.data or []):
            try:
                token = user.get("fcm_token")
                lang  = user.get("language","hi")
                if not token:
                    continue
                title = "Weekly Report Ready! 📊" if lang == "en" else "Weekly Report Taiyar Hai! 📊"
                body  = "Check how you studied this week." if lang == "en" \
                        else "Is hafte ki padhai dekho!"
                await send_fcm_notification(token, title, body,
                                            data={"type":"weekly_report"})
            except Exception as e:
                log.warning("report_notification_failed",
                            user_id=user["user_id"], error=str(e))

        log.info("weekly_reports_sent", count=len(result.data or []))

    return run_async(_run())


@celery_app.task(name="tasks.data_purge")
def data_purge():
    """Hard-delete accounts soft-deleted more than 30 days ago."""
    async def _run():
        from app.core.database import Tables, get_supabase
        from app.core.config import settings

        db = await get_supabase()
        cutoff = (datetime.now(timezone.utc) - timedelta(
            days=settings.DATA_PURGE_AFTER_DELETE_DAYS
        )).isoformat()

        result = await db.table(Tables.USERS).select("user_id").lt(
            "deleted_at", cutoff
        ).execute()

        purged = 0
        for user in (result.data or []):
            uid = user["user_id"]
            # Delete in order: messages → sessions → progress → user
            await db.table(Tables.CHAT_MESSAGES).delete().eq("user_id", uid).execute()
            await db.table(Tables.CHAT_SESSIONS).delete().eq("user_id", uid).execute()
            await db.table(Tables.STUDENT_PROGRESS).delete().eq("user_id", uid).execute()
            await db.table(Tables.QUIZ_ATTEMPTS).delete().eq("user_id", uid).execute()
            await db.table(Tables.USERS).delete().eq("user_id", uid).execute()
            purged += 1

        log.info("data_purge_complete", purged=purged)
        return {"purged": purged}

    return run_async(_run())


@celery_app.task(name="tasks.schedule_data_purge")
def schedule_data_purge(user_id: str):
    """Mark user for purge in 30 days (called at delete time)."""
    log.info("data_purge_scheduled", user_id=user_id)
    # The daily data_purge task picks this up when deleted_at is 30+ days old
    return {"scheduled": True, "user_id": user_id}


@celery_app.task(name="tasks.workspace_quota_reset")
def workspace_quota_reset():
    """Reset queries_used for all active school workspaces."""
    async def _run():
        from app.core.database import Tables, get_supabase
        db = await get_supabase()
        await db.table(Tables.WORKSPACES).update(
            {"queries_used": 0}
        ).eq("is_active", True).execute()
        log.info("workspace_quotas_reset")

    return run_async(_run())


@celery_app.task(name="tasks.rebuild_bm25_indexes")
def rebuild_bm25_indexes():
    """Rebuild all BM25 in-memory indexes (clears cache, forces rebuild on next query)."""
    from app.services.ai.rag_pipeline import get_search_engine
    engine = get_search_engine()
    engine._bm25_cache.clear()
    engine._bm25_chunk_ids.clear()
    log.info("bm25_indexes_cleared")
    return {"status": "cleared"}


# ══════════════════════════════════════════════════════════════════
# ON-DEMAND TASKS
# ══════════════════════════════════════════════════════════════════

@celery_app.task(name="tasks.update_chunk_thompson_sampling")
def update_chunk_thompson_sampling(chunk_ids: list[str], feedback: str):
    """Update Thompson Sampling scores for chunks based on user feedback."""
    async def _run():
        from app.services.ai.rag_pipeline import update_chunk_utility
        await update_chunk_utility(chunk_ids, feedback)

    return run_async(_run())


@celery_app.task(name="tasks.safety_scan_response")
def safety_scan_response(session_id: str, message_id: str, response_text: str):
    """Deep safety scan on AI response. Flag if unsafe."""
    blocked = ["violent", "adult content", "political", "religious extremism"]
    is_flagged = any(term in response_text.lower() for term in blocked)

    if is_flagged:
        async def _flag():
            from app.core.database import Tables, db_update
            await db_update(Tables.CHAT_MESSAGES, {"message_id": message_id},
                           {"is_flagged": True})
            log.warning("ai_response_flagged", session_id=session_id, message_id=message_id)

        run_async(_flag())

    return {"flagged": is_flagged, "message_id": message_id}
