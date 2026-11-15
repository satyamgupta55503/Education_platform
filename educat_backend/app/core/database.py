"""
EduCat AI — Supabase Database Client
Provides async Supabase client with connection pooling.
Service role key used server-side to bypass RLS when needed.
"""
import asyncio
from functools import lru_cache
from typing import Optional

from supabase import AsyncClient, acreate_client
from supabase.lib.client_options import AsyncClientOptions

from app.core.config import settings
import structlog

log = structlog.get_logger()

# ── Singleton async client ────────────────────────────────────────
_supabase_client: Optional[AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_supabase() -> AsyncClient:
    """
    Returns the singleton async Supabase client (service role).
    Uses service role key — bypasses all RLS policies.
    For user-scoped operations, set workspace_id in Postgres session.
    """
    global _supabase_client
    if _supabase_client is None:
        async with _client_lock:
            if _supabase_client is None:
                _supabase_client = await acreate_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    options=AsyncClientOptions(
                        auto_refresh_token=False,
                        persist_session=False,
                    ),
                )
                log.info("supabase_client_initialized",
                         url=settings.SUPABASE_URL[:30] + "...")
    return _supabase_client


async def get_supabase_anon() -> AsyncClient:
    """
    Returns anon-key Supabase client.
    Respects RLS policies — use for user-facing operations.
    """
    return await acreate_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
    )


async def close_supabase() -> None:
    """Close DB connection on app shutdown."""
    global _supabase_client
    if _supabase_client:
        _supabase_client = None
        log.info("supabase_client_closed")


# ── Table name constants ──────────────────────────────────────────
class Tables:
    USERS              = "users"
    WORKSPACES         = "workspaces"
    TEACHERS           = "teachers"
    TEACHER_DEVICES    = "teacher_devices"
    CHAT_SESSIONS      = "chat_sessions"
    CHAT_MESSAGES      = "chat_messages"
    CONTENT            = "content"
    CONTENT_CHUNKS     = "content_chunks"
    SEMANTIC_CACHE     = "semantic_cache"
    AUDIO_CACHE        = "audio_cache"
    ADMIN_USERS        = "admin_users"
    TOKEN_FAMILIES     = "token_families"
    AUDIT_LOG          = "audit_log"
    SUBSCRIPTIONS      = "subscriptions"
    STUDENT_PROGRESS   = "student_progress"
    QUIZ_ATTEMPTS      = "quiz_attempts"
    SESSION_SUMMARIES  = "session_summaries"
    OTP_ATTEMPTS       = "otp_attempts"


# ── DB Helper Functions ───────────────────────────────────────────
async def db_fetch_one(
    table: str,
    filters: dict,
    select: str = "*"
) -> Optional[dict]:
    """Fetch single row matching filters."""
    db = await get_supabase()
    query = db.table(table).select(select)
    for col, val in filters.items():
        query = query.eq(col, val)
    result = await query.limit(1).execute()
    return result.data[0] if result.data else None


async def db_fetch_many(
    table: str,
    filters: dict = None,
    select: str = "*",
    order_by: str = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Fetch multiple rows with optional filters."""
    db = await get_supabase()
    query = db.table(table).select(select)
    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)
    if order_by:
        desc = order_by.startswith("-")
        col = order_by.lstrip("-")
        query = query.order(col, desc=desc)
    result = await query.range(offset, offset + limit - 1).execute()
    return result.data or []


async def db_insert(table: str, data: dict) -> Optional[dict]:
    """Insert a row and return the created record."""
    db = await get_supabase()
    result = await db.table(table).insert(data).execute()
    return result.data[0] if result.data else None


async def db_update(table: str, filters: dict, data: dict) -> Optional[dict]:
    """Update rows matching filters."""
    db = await get_supabase()
    query = db.table(table).update(data)
    for col, val in filters.items():
        query = query.eq(col, val)
    result = await query.execute()
    return result.data[0] if result.data else None


async def db_upsert(table: str, data: dict, on_conflict: str = "id") -> Optional[dict]:
    """Upsert (insert or update on conflict)."""
    db = await get_supabase()
    result = await db.table(table).upsert(data, on_conflict=on_conflict).execute()
    return result.data[0] if result.data else None


async def db_delete(table: str, filters: dict) -> bool:
    """Delete rows matching filters."""
    db = await get_supabase()
    query = db.table(table).delete()
    for col, val in filters.items():
        query = query.eq(col, val)
    await query.execute()
    return True


async def db_execute_sql(sql: str, params: list = None) -> list:
    """Execute raw SQL (for complex queries like vector search)."""
    db = await get_supabase()
    result = await db.rpc("execute_sql", {"query": sql, "params": params or []}).execute()
    return result.data or []
