"""
EduCat AI — Redis Client
3 Redis databases:
  db=0: L1 exact cache + rate limiting + token quotas
  db=1: Celery broker
  db=2: Celery results
"""
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from app.core.config import settings
import structlog

log = structlog.get_logger()

# ── Connection Pools ──────────────────────────────────────────────
_pool: Optional[ConnectionPool] = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> aioredis.Redis:
    """Get async Redis client from pool."""
    return aioredis.Redis(connection_pool=get_pool())


# ── Token Quota Operations (Atomic) ───────────────────────────────
QUOTA_KEY    = "quota:{user_id}:monthly"
DAILY_KEY    = "quota:{user_id}:daily:{date}"
REVOKED_KEY  = "revoked_tokens"
OTP_KEY      = "otp:{identifier}"
LOCKOUT_KEY  = "lockout:{identifier}"
CACHE_KEY    = "cache:{hash}"
SESSION_KEY  = "session:{session_id}"


async def quota_check_and_decrement(
    user_id: str,
    tier: str,
    date_str: str,
) -> dict:
    """
    Atomic check + decrement for both monthly and daily quotas.
    Returns: { allowed: bool, monthly_remaining: int, daily_remaining: int }
    Uses Redis pipeline for atomicity.
    """
    redis = await get_redis()
    monthly_key = QUOTA_KEY.format(user_id=user_id)
    daily_key = DAILY_KEY.format(user_id=user_id, date=date_str)

    daily_cap = settings.daily_caps.get(tier, 2)

    async with redis.pipeline(transaction=True) as pipe:
        try:
            await pipe.watch(monthly_key, daily_key)
            monthly_val = await redis.get(monthly_key)
            daily_val   = await redis.get(daily_key)

            monthly_remaining = int(monthly_val) if monthly_val else 0
            daily_remaining   = int(daily_val) if daily_val else daily_cap

            if monthly_remaining <= 0:
                return {"allowed": False, "reason": "monthly_exhausted",
                        "monthly_remaining": 0, "daily_remaining": daily_remaining}

            if daily_remaining <= 0:
                return {"allowed": False, "reason": "daily_cap_reached",
                        "monthly_remaining": monthly_remaining, "daily_remaining": 0}

            pipe.multi()
            pipe.decrby(monthly_key, 1)
            pipe.decrby(daily_key, 1)
            await pipe.execute()

            return {
                "allowed": True,
                "monthly_remaining": monthly_remaining - 1,
                "daily_remaining": daily_remaining - 1,
            }
        except aioredis.WatchError:
            # Concurrent modification — retry once
            return await quota_check_and_decrement(user_id, tier, date_str)


async def quota_init(user_id: str, monthly: int, tier: str, ttl_seconds: int = 2592000):
    """Initialize or reset monthly quota in Redis."""
    redis = await get_redis()
    key = QUOTA_KEY.format(user_id=user_id)
    await redis.setex(key, ttl_seconds, monthly)
    log.info("quota_initialized", user_id=user_id, monthly=monthly, tier=tier)


async def quota_get(user_id: str) -> int:
    """Get current monthly quota remaining."""
    redis = await get_redis()
    val = await redis.get(QUOTA_KEY.format(user_id=user_id))
    return int(val) if val else 0


# ── Token Revocation ──────────────────────────────────────────────
async def revoke_token(jti: str, ttl_seconds: int = 604800):
    """Add JWT JTI to revocation set."""
    redis = await get_redis()
    await redis.sadd(REVOKED_KEY, jti)
    await redis.expire(REVOKED_KEY, ttl_seconds)


async def is_token_revoked(jti: str) -> bool:
    """Check if JWT JTI is in revocation set."""
    redis = await get_redis()
    return bool(await redis.sismember(REVOKED_KEY, jti))


# ── OTP Storage ───────────────────────────────────────────────────
async def store_otp(identifier: str, otp: str, ttl_minutes: int = 10):
    """Store OTP with TTL."""
    redis = await get_redis()
    key = OTP_KEY.format(identifier=identifier)
    await redis.setex(key, ttl_minutes * 60, otp)


async def verify_otp(identifier: str, provided_otp: str) -> bool:
    """Verify OTP and delete it (one-time use)."""
    redis = await get_redis()
    key = OTP_KEY.format(identifier=identifier)
    stored = await redis.get(key)
    if stored and stored == provided_otp:
        await redis.delete(key)
        return True
    return False


async def get_otp_attempts(identifier: str) -> int:
    """Get failed OTP attempt count."""
    redis = await get_redis()
    val = await redis.get(f"otp_attempts:{identifier}")
    return int(val) if val else 0


async def increment_otp_attempts(identifier: str) -> int:
    """Increment and return failed OTP attempts."""
    redis = await get_redis()
    key = f"otp_attempts:{identifier}"
    count = await redis.incr(key)
    await redis.expire(key, settings.LOCKOUT_MINUTES * 60)
    return count


async def clear_otp_attempts(identifier: str):
    redis = await get_redis()
    await redis.delete(f"otp_attempts:{identifier}")


# ── Lockout ───────────────────────────────────────────────────────
async def set_lockout(identifier: str):
    redis = await get_redis()
    key = LOCKOUT_KEY.format(identifier=identifier)
    await redis.setex(key, settings.LOCKOUT_MINUTES * 60, "1")


async def is_locked_out(identifier: str) -> bool:
    redis = await get_redis()
    key = LOCKOUT_KEY.format(identifier=identifier)
    return bool(await redis.get(key))


# ── L1 Exact Cache ────────────────────────────────────────────────
async def cache_get(cache_hash: str) -> Optional[dict]:
    redis = await get_redis()
    val = await redis.get(CACHE_KEY.format(hash=cache_hash))
    return json.loads(val) if val else None


async def cache_set(cache_hash: str, data: dict, ttl_seconds: int = 604800):
    redis = await get_redis()
    await redis.setex(
        CACHE_KEY.format(hash=cache_hash),
        ttl_seconds,
        json.dumps(data, ensure_ascii=False)
    )


# ── Session State ─────────────────────────────────────────────────
async def session_set(session_id: str, data: dict, ttl: int = 86400):
    redis = await get_redis()
    await redis.setex(
        SESSION_KEY.format(session_id=session_id),
        ttl,
        json.dumps(data, ensure_ascii=False)
    )


async def session_get(session_id: str) -> Optional[dict]:
    redis = await get_redis()
    val = await redis.get(SESSION_KEY.format(session_id=session_id))
    return json.loads(val) if val else None


# ── Pub/Sub for Teacher Real-time ─────────────────────────────────
async def publish_lesson_event(workspace_id: str, event: dict):
    redis = await get_redis()
    channel = f"lesson:{workspace_id}"
    await redis.publish(channel, json.dumps(event, ensure_ascii=False))


async def close_redis():
    global _pool
    if _pool:
        await _pool.disconnect()
        _pool = None
