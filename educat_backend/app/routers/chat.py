"""
EduCat AI — Chat Router
Main AI chat endpoint with SSE streaming, session management, quiz, history.
"""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import Tables, db_fetch_many, db_fetch_one, db_insert, db_update
from app.core.dependencies import get_current_student_with_profile
from app.core.redis_client import (
    cache_get,
    cache_set,
    quota_check_and_decrement,
    session_get,
    session_set,
)
from app.core.security import hash_text
from app.schemas.schemas import (
    CreateSessionRequest,
    QuizGenerateRequest,
    QuizSubmitRequest,
    SendMessageRequest,
)
from app.services.ai.gemini_service import (
    curate_video_for_topic,
    generate_embedding,
    generate_quiz,
    generate_session_summary,
    stream_chat_response,
)
from app.services.ai.rag_pipeline import (
    build_student_context,
    get_difficulty_classifier,
    get_search_engine,
    semantic_cache_lookup,
    semantic_cache_store,
    update_chunk_utility,
)
import structlog

log = structlog.get_logger()
router = APIRouter()


# ══════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════════

@router.post("/session/create", summary="Create a new chat session")
async def create_session(
    body: CreateSessionRequest,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    user    = current_user["profile"]
    user_id = user["user_id"]
    grade   = body.grade or user.get("grade", 5)
    lang    = user.get("language", "hi")

    session_id = str(uuid4())

    # Build context for this session
    ctx = await build_student_context(user_id, body.subject, grade)

    # Store session in DB
    session_data = {
        "session_id":     session_id,
        "user_id":        user_id,
        "subject":        body.subject,
        "topic":          body.topic,
        "grade":          grade,
        "exchange_count": 0,
        "coins_earned":   0,
        "started_at":     datetime.now(timezone.utc).isoformat(),
    }
    await db_insert(Tables.CHAT_SESSIONS, session_data)

    # Cache session state in Redis for fast lookup
    await session_set(session_id, {
        "user_id":   user_id,
        "subject":   body.subject,
        "topic":     body.topic,
        "grade":     grade,
        "language":  lang,
        "tier":      user.get("subscription_tier", "free"),
        "messages":  [],
    })

    log.info("session_created", session_id=session_id, subject=body.subject)
    return {"success": True, "data": {
        "session_id":      session_id,
        "subject":         body.subject,
        "topic":           body.topic,
        "grade":           grade,
        "context_injected": {
            "past_summary":     ctx.get("past_summary"),
            "weak_topics":      ctx.get("weak_topics", []),
            "future_hint":      ctx.get("future_hint"),
            "difficulty_preset": "medium",
        },
    }}


# ══════════════════════════════════════════════════════════════════
# MAIN CHAT ENDPOINT — SSE STREAMING
# ══════════════════════════════════════════════════════════════════

@router.post("/send", summary="Send message and receive SSE-streamed AI response")
async def send_message(
    body: SendMessageRequest,
    request: Request,
    background: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    """
    Main AI chat endpoint. Returns Server-Sent Events stream.
    Pipeline: quota check → L1 cache → L2 semantic cache → RAG → Gemini stream
    """
    user    = current_user["profile"]
    user_id = user["user_id"]
    tier    = user.get("subscription_tier", "free")
    lang    = body.language or user.get("language", "hi")

    # ── Step 1: Quota check (atomic Redis) ───────────────────────
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quota = await quota_check_and_decrement(user_id, tier, today_str)
    if not quota["allowed"]:
        reason = quota.get("reason", "quota_exhausted")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "reason": reason,
                "monthly_remaining": quota["monthly_remaining"],
                "daily_remaining": quota.get("daily_remaining", 0),
                "upgrade_url": "/api/v1/subscriptions/plans",
            }
        )

    # ── Step 2: Load session ──────────────────────────────────────
    session = await session_get(body.session_id)
    if not session:
        # Reload from DB if not in Redis
        db_session = await db_fetch_one(
            Tables.CHAT_SESSIONS,
            {"session_id": body.session_id, "user_id": user_id}
        )
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages_db = await db_fetch_many(
            Tables.CHAT_MESSAGES,
            {"session_id": body.session_id},
            order_by="created_at",
            limit=30,
        )
        session = {
            "user_id":  user_id,
            "subject":  db_session["subject"],
            "topic":    db_session["topic"],
            "grade":    db_session["grade"],
            "language": lang,
            "tier":     tier,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages_db],
        }

    subject = body.subject or session.get("subject", "science")
    grade   = session.get("grade", user.get("grade", 5))

    # ── Step 3: L1 Redis exact cache ─────────────────────────────
    cache_hash = hash_text(f"{body.question}_{subject}_{grade}_{lang}")
    l1_hit = await cache_get(cache_hash)

    async def sse_from_cache(cached: dict) -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'billi_state', 'state': 'idle'})}\n\n"
        yield f"data: {json.dumps({'type': 'cache_hit', 'layer': 'L1'})}\n\n"
        # Stream cached text as tokens for smooth UI
        text = cached["response"]
        for i in range(0, len(text), 8):
            chunk = text[i:i+8]
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)
        yield f"data: {json.dumps({'type': 'complete', 'billi_state': 'happy', 'full_text': text})}\n\n"
        yield "data: [DONE]\n\n"

    if l1_hit:
        log.info("l1_cache_hit", user_id=user_id)
        return StreamingResponse(
            sse_from_cache(l1_hit),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── Step 4: Generate query embedding ─────────────────────────
    query_embedding = await generate_embedding(body.question)

    # ── Step 5: L2 Semantic cache ─────────────────────────────────
    l2_cached = await semantic_cache_lookup(body.question, query_embedding, subject, grade)
    if l2_cached:
        async def sse_from_l2(text: str) -> AsyncGenerator[str, None]:
            yield f"data: {json.dumps({'type': 'billi_state', 'state': 'idle'})}\n\n"
            yield f"data: {json.dumps({'type': 'cache_hit', 'layer': 'L2'})}\n\n"
            for i in range(0, len(text), 8):
                yield f"data: {json.dumps({'type': 'token', 'content': text[i:i+8]})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'type': 'complete', 'billi_state': 'happy', 'full_text': text})}\n\n"
            yield "data: [DONE]\n\n"

        log.info("l2_semantic_cache_hit", user_id=user_id, subject=subject)
        # Save message to DB async
        background.add_task(
            _save_exchange,
            body.session_id, user_id, body.question, l2_cached, [], subject, grade
        )
        return StreamingResponse(sse_from_l2(l2_cached),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # ── Step 6: Classify difficulty ───────────────────────────────
    classifier = get_difficulty_classifier()
    difficulty = classifier.classify(body.question, grade, subject)

    # ── Step 7: RAG retrieval ─────────────────────────────────────
    engine = get_search_engine()
    chunks = await engine.search(
        question=body.question,
        subject=subject,
        grade=grade,
        workspace_id=None,
    )
    chunk_texts = [c["chunk_text"] for c in chunks]
    chunk_ids   = [c["chunk_id"] for c in chunks]

    # ── Step 8: Load past/future context ──────────────────────────
    ctx = await build_student_context(user_id, subject, grade)

    # ── Step 9: Video suggestion (background) ─────────────────────
    video_query = None
    if len(session.get("messages", [])) % 5 == 4:  # Every 5th exchange
        background.add_task(
            _update_video_suggestion,
            body.session_id, session.get("topic", body.question), subject, grade, lang
        )

    # ── Step 10: Stream Gemini response ───────────────────────────
    full_text_parts = []

    async def sse_generator() -> AsyncGenerator[str, None]:
        async for event in stream_chat_response(
            question=body.question,
            context_chunks=chunk_texts,
            conversation_history=session.get("messages", []),
            grade=grade,
            subject=subject,
            language=lang,
            tier=tier,
            difficulty=difficulty,
            past_summary=ctx.get("past_summary"),
            future_hint=ctx.get("future_hint"),
            weakness_note=ctx.get("weakness_note"),
        ):
            if '"type": "token"' in event:
                try:
                    data = json.loads(event[6:])  # Strip "data: "
                    full_text_parts.append(data.get("content", ""))
                except Exception:
                    pass
            elif '"type": "complete"' in event:
                full_text = "".join(full_text_parts)
                # Fire background tasks
                background.add_task(
                    _post_response_tasks,
                    body.session_id, user_id, body.question, full_text,
                    chunk_ids, query_embedding, subject, grade, cache_hash,
                    session.get("messages", []),
                )
            yield event

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "X-Tokens-Remaining": str(quota["monthly_remaining"]),
        },
    )


# ══════════════════════════════════════════════════════════════════
# QUIZ ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@router.post("/quiz/generate", summary="Generate AI quiz for a topic")
async def generate_quiz_endpoint(
    body: QuizGenerateRequest,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    user = current_user["profile"]
    lang = user.get("language", "hi")
    grade = body.grade or user.get("grade", 5)

    questions = await generate_quiz(
        topic=body.topic,
        subject=body.subject,
        grade=grade,
        language=lang,
        difficulty=body.difficulty,
        count=body.count,
    )

    quiz_id = str(uuid4())
    # Store quiz in Redis for submission verification
    await cache_set(f"quiz:{quiz_id}", {
        "questions": questions,
        "user_id": user["user_id"],
        "topic": body.topic,
        "subject": body.subject,
        "grade": grade,
    }, ttl_seconds=3600)

    return {"success": True, "data": {
        "quiz_id": quiz_id,
        "questions": questions,
        "topic": body.topic,
        "estimated_time_minutes": len(questions),
    }}


@router.post("/quiz/submit", summary="Submit quiz answers and earn Brain Coins")
async def submit_quiz(
    body: QuizSubmitRequest,
    background: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)],
):
    user    = current_user["profile"]
    user_id = user["user_id"]

    # Load quiz from cache
    cached = await cache_get(f"quiz:{body.quiz_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="Quiz not found or expired")

    if cached["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="This quiz belongs to another user")

    questions = cached["questions"]
    score = 0
    feedback = []

    for q in questions:
        q_id     = q["q_id"]
        selected = body.answers.get(q_id)
        correct  = q["correct_index"]
        is_right = selected == correct
        if is_right:
            score += 1

        feedback.append({
            "q_id":          q_id,
            "is_correct":    is_right,
            "selected":      selected,
            "correct_index": correct,
            "explanation":   q.get("explanation", ""),
        })

    total     = len(questions)
    pct       = round((score / total) * 100, 1) if total else 0
    coins     = score * 2  # 2 coins per correct answer

    # Award Brain Coins
    if coins > 0:
        background.add_task(_award_brain_coins, user_id, coins)

    # Save progress
    background.add_task(
        _save_quiz_attempt,
        user_id, body.quiz_id, cached["topic"],
        cached["subject"], cached["grade"],
        score, total, pct
    )

    log.info("quiz_submitted", user_id=user_id, score=score, total=total)
    return {"success": True, "data": {
        "quiz_id":          body.quiz_id,
        "score":            score,
        "total":            total,
        "percentage":       pct,
        "brain_coins_earned": coins,
        "feedback":         feedback,
    }}


# ══════════════════════════════════════════════════════════════════
# SESSION HISTORY
# ══════════════════════════════════════════════════════════════════

@router.get("/sessions", summary="Get user's session history")
async def get_sessions(
    subject: str = None,
    limit: int = 20,
    offset: int = 0,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)] = None,
):
    user_id = current_user["profile"]["user_id"]
    db = __import__("app.core.database", fromlist=["get_supabase"]).get_supabase

    from app.core.database import get_supabase
    supabase = await get_supabase()
    query = supabase.table(Tables.CHAT_SESSIONS).select(
        "session_id, subject, topic, grade, exchange_count, coins_earned, "
        "started_at, last_message_at"
    ).eq("user_id", user_id).is_("deleted_at", None)

    if subject:
        query = query.eq("subject", subject)

    result = await query.order("started_at", desc=True).range(
        offset, offset + limit - 1
    ).execute()

    return {"success": True, "data": {
        "sessions": result.data or [],
        "total": len(result.data or []),
    }}


@router.get("/sessions/{session_id}/messages", summary="Get messages for a session")
async def get_session_messages(
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)] = None,
):
    user_id = current_user["profile"]["user_id"]

    # Verify session belongs to user
    session = await db_fetch_one(
        Tables.CHAT_SESSIONS,
        {"session_id": session_id, "user_id": user_id}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await db_fetch_many(
        Tables.CHAT_MESSAGES,
        {"session_id": session_id},
        order_by="created_at",
        limit=100,
    )

    return {"success": True, "data": {
        "session": session,
        "messages": messages,
    }}


@router.delete("/sessions/{session_id}", summary="Delete a session")
async def delete_session(
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_student_with_profile)] = None,
):
    user_id = current_user["profile"]["user_id"]
    tier    = current_user["profile"].get("subscription_tier", "free")

    session = await db_fetch_one(
        Tables.CHAT_SESSIONS,
        {"session_id": session_id, "user_id": user_id}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.core.database import db_update
    if tier == "genius":
        # Archive only (permanent history)
        await db_update(Tables.CHAT_SESSIONS,
                        {"session_id": session_id},
                        {"is_archived": True})
    else:
        # Soft delete
        await db_update(Tables.CHAT_SESSIONS,
                        {"session_id": session_id},
                        {"deleted_at": datetime.now(timezone.utc).isoformat()})

    return {"success": True, "data": {"deleted": True}}


# ── Background Tasks ──────────────────────────────────────────────
async def _post_response_tasks(
    session_id: str, user_id: str, question: str, response: str,
    chunk_ids: list, query_embedding: list, subject: str, grade: int,
    cache_hash: str, prev_messages: list,
):
    """All async work after response is streamed."""
    # Save to DB
    await _save_exchange(session_id, user_id, question, response,
                         chunk_ids, subject, grade)
    # Store in L1 cache
    await cache_set(cache_hash, {"response": response}, ttl_seconds=604800)
    # Store in L2 semantic cache
    await semantic_cache_store(question, response, query_embedding, subject, grade)
    # Update session Redis
    session = await session_get(session_id) or {}
    msgs = session.get("messages", [])
    msgs.append({"role": "user", "content": question})
    msgs.append({"role": "assistant", "content": response})
    session["messages"] = msgs[-30:]  # Keep last 30
    await session_set(session_id, session)
    # Safety scan (async)
    asyncio.create_task(_safety_scan(session_id, response))


async def _save_exchange(
    session_id: str, user_id: str, question: str, response: str,
    chunk_ids: list, subject: str, grade: int,
):
    now = datetime.now(timezone.utc).isoformat()
    msg_user = {
        "message_id": str(uuid4()), "session_id": session_id,
        "user_id": user_id, "role": "user",
        "content": question, "created_at": now,
    }
    msg_ai = {
        "message_id": str(uuid4()), "session_id": session_id,
        "user_id": user_id, "role": "assistant",
        "content": response, "created_at": now,
    }
    from app.core.database import get_supabase
    db = await get_supabase()
    await db.table(Tables.CHAT_MESSAGES).insert([msg_user, msg_ai]).execute()
    await db.table(Tables.CHAT_SESSIONS).update({
        "exchange_count": db.table(Tables.CHAT_SESSIONS).select("exchange_count"),
        "last_message_at": now,
    }).eq("session_id", session_id).execute()


async def _award_brain_coins(user_id: str, coins: int):
    from app.core.database import get_supabase
    db = await get_supabase()
    await db.rpc("increment_brain_coins",
                 {"p_user_id": user_id, "p_coins": coins}).execute()


async def _save_quiz_attempt(
    user_id, quiz_id, topic, subject, grade, score, total, pct
):
    from app.core.database import get_supabase
    db = await get_supabase()
    await db.table(Tables.QUIZ_ATTEMPTS).insert({
        "attempt_id": str(uuid4()),
        "user_id": user_id, "quiz_id": quiz_id,
        "topic": topic, "subject": subject, "grade": grade,
        "score": score, "total": total,
        "percentage": pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Update student progress
    knowledge_prob = min(0.99, score / total) if total else 0.5
    await db.table(Tables.STUDENT_PROGRESS).upsert({
        "user_id": user_id, "subject": subject, "grade": grade,
        "topic": topic,
        "interaction_type": "quiz_attempt",
        "response_quality": "positive" if pct >= 70 else "negative",
        "knowledge_probability": knowledge_prob,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id,subject,grade,topic").execute()


async def _safety_scan(session_id: str, response: str):
    """Post-response safety scan — runs asynchronously."""
    blocked_patterns = [
        "violence", "adult", "politics", "religion", "18+",
    ]
    is_flagged = any(p in response.lower() for p in blocked_patterns)
    if is_flagged:
        from app.core.database import get_supabase
        db = await get_supabase()
        await db.table(Tables.CHAT_MESSAGES).update({
            "is_flagged": True
        }).eq("session_id", session_id).eq("role", "assistant").execute()


async def _update_video_suggestion(
    session_id: str, topic: str, subject: str, grade: int, lang: str
):
    query = await curate_video_for_topic(topic, subject, grade, lang)
    await cache_set(f"video_query:{session_id}", {"query": query}, ttl_seconds=3600)
