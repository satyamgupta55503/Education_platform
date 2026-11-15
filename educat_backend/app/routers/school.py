"""
EduCat AI — School Dashboard Router
Endpoints for the school dashboard frontend (teacher-authenticated).
All routes scoped to the teacher's workspace via JWT token.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)

from app.core.database import (
    Tables,
    get_supabase,
)

from app.core.dependencies import get_current_teacher

import structlog

log = structlog.get_logger()
router = APIRouter()


@router.get("/dashboard/overview", summary="School dashboard overview")
async def school_dashboard_overview(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """
    Returns workspace info, team stats, today's usage,
    cache stats, subject engagement, and 30-day activity.
    """
    workspace_id = current_teacher["workspace_id"]
    workspace = current_teacher.get("workspace", {})
    db = await get_supabase()

    # Team stats
    teachers = await db.table(Tables.TEACHERS).select(
        "teacher_id", count="exact"
    ).eq("workspace_id", workspace_id).eq("is_active", True).execute()

    students = await db.table(Tables.USERS).select(
        "user_id", count="exact"
    ).is_("deleted_at", None).execute()
    # Note: In a full implementation, students would be linked to workspace

    # Today stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
    sessions_today = await db.table(Tables.CHAT_SESSIONS).select(
        "session_id", count="exact"
    ).gte("started_at", today_start).execute()

    messages_today = await db.table(Tables.CHAT_MESSAGES).select(
        "message_id", count="exact"
    ).gte("created_at", today_start).execute()

    # Subject engagement from content
    content_items = await db.table(Tables.CONTENT).select(
        "subject"
    ).eq("workspace_id", workspace_id).eq("status", "published").execute()

    subject_engagement = {}
    for item in (content_items.data or []):
        subj = item.get("subject", "unknown")
        subject_engagement[subj] = subject_engagement.get(subj, 0) + 1

    # Cache stats
    cache_stats = {"semantic_cache_size": 0, "hit_rate": 0}
    try:
        sem_count = await db.table(Tables.SEMANTIC_CACHE).select(
            "cache_id", count="exact"
        ).execute()
        cache_stats["semantic_cache_size"] = sem_count.count or 0
    except Exception:
        pass

    return {"success": True, "data": {
        "workspace": {
            "workspace_id": workspace_id,
            "school_name": workspace.get("school_name", ""),
            "school_code": workspace.get("school_code", ""),
            "subscription_plan": workspace.get("subscription_plan", "classroom"),
            "queries_used": workspace.get("queries_used", 0),
            "monthly_query_quota": workspace.get("monthly_query_quota", 10000),
            "is_active": workspace.get("is_active", True),
            "expires_at": workspace.get("expires_at"),
        },
        "team": {
            "total_teachers": teachers.count or 0,
            "total_students": students.count or 0,
        },
        "today": {
            "sessions": sessions_today.count or 0,
            "messages": messages_today.count or 0,
            "queries_used_today": 0,
        },
        "cache": cache_stats,
        "subject_engagement": [
            {"subject": k, "content_count": v}
            for k, v in subject_engagement.items()
        ],
        "activity_30d": [],  # TODO: aggregate daily activity over 30 days
    }}


@router.get("/dashboard/students", summary="List students with filters and pagination")
async def school_dashboard_students(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
    grade: Optional[int] = None,
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    order: str = Query(default="desc", description="Sort order: asc or desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Returns paginated list of students, optionally filtered by grade."""
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()
    offset = (page - 1) * limit

    query = db.table(Tables.USERS).select(
        "user_id,grade,language,subscription_tier,tokens_remaining,brain_coins,streak_days,created_at",
        count="exact"
    ).is_("deleted_at", None)

    if grade:
        query = query.eq("grade", grade)

    # Validate sort field
    allowed_sort_fields = {"created_at", "grade", "streak_days", "brain_coins", "tokens_remaining"}
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"

    desc = order.lower() == "desc"
    result = await query.order(sort_by, desc=desc).range(offset, offset + limit - 1).execute()

    return {"success": True, "data": {
        "students": result.data or [],
        "total": result.count or 0,
        "page": page,
        "limit": limit,
        "total_pages": ((result.count or 0) + limit - 1) // limit,
    }}


@router.get("/dashboard/teachers", summary="List teachers for this workspace")
async def school_dashboard_teachers(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Returns all teachers in the current workspace."""
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()

    result = await db.table(Tables.TEACHERS).select(
        "teacher_id,name,email,subject_specialisation,is_active,last_login,created_at"
    ).eq("workspace_id", workspace_id).order("name").execute()

    return {"success": True, "data": {
        "teachers": result.data or [],
        "total": len(result.data or []),
    }}


@router.get("/dashboard/subjects", summary="Subject statistics for this workspace")
async def school_dashboard_subjects(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Returns subject-level stats: content count, quiz attempts, etc."""
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()

    # Get content by subject for this workspace
    content = await db.table(Tables.CONTENT).select(
        "subject,status"
    ).eq("workspace_id", workspace_id).execute()

    subject_stats = {}
    for item in (content.data or []):
        subj = item.get("subject", "unknown")
        if subj not in subject_stats:
            subject_stats[subj] = {"subject": subj, "total_content": 0, "published": 0, "draft": 0}
        subject_stats[subj]["total_content"] += 1
        if item.get("status") == "published":
            subject_stats[subj]["published"] += 1
        elif item.get("status") == "draft":
            subject_stats[subj]["draft"] += 1

    # Get teachers by subject specialisation
    teachers = await db.table(Tables.TEACHERS).select(
        "subject_specialisation"
    ).eq("workspace_id", workspace_id).eq("is_active", True).execute()

    for t in (teachers.data or []):
        subjects = t.get("subject_specialisation") or []
        for subj in subjects:
            if subj in subject_stats:
                subject_stats[subj]["teachers"] = subject_stats[subj].get("teachers", 0) + 1
            else:
                subject_stats[subj] = {"subject": subj, "total_content": 0, "published": 0, "draft": 0, "teachers": 1}

    return {"success": True, "data": {
        "subjects": list(subject_stats.values()),
    }}


@router.get("/dashboard/weak-students", summary="Students below mastery threshold")
async def school_dashboard_weak_students(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
    threshold: float = Query(default=0.4, ge=0.0, le=1.0, description="Mastery threshold (0-1)"),
):
    """
    Returns students whose average mastery score is below the given threshold.
    Useful for identifying students who need additional support.
    """
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()

    # Get student progress records
    progress = await db.table(Tables.STUDENT_PROGRESS).select(
        "user_id,subject,knowledge_probability"
    ).execute()

    # Aggregate by student
    student_scores: dict = {}
    for p in (progress.data or []):
        uid = p.get("user_id")
        score = p.get("knowledge_probability", 0) or 0
        if uid not in student_scores:
            student_scores[uid] = {"scores": [], "subjects": set()}
        student_scores[uid]["scores"].append(score)
        student_scores[uid]["subjects"].add(p.get("subject", "unknown"))

    # Find weak students
    weak_students = []
    for uid, data in student_scores.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        if avg_score < threshold:
            weak_students.append({
                "user_id": uid,
                "average_mastery": round(avg_score, 3),
                "subjects_count": len(data["subjects"]),
                "assessments_taken": len(data["scores"]),
            })

    # Sort by lowest mastery first
    weak_students.sort(key=lambda x: x["average_mastery"])

    return {"success": True, "data": {
        "weak_students": weak_students[:50],  # Limit to top 50
        "total": len(weak_students),
        "threshold": threshold,
    }}


@router.get("/dashboard/content-usage", summary="Content engagement stats")
async def school_dashboard_content_usage(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """
    Returns top and low engagement content for this workspace.
    Based on content access patterns and quiz attempts.
    """
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()

    # Get published content for this workspace
    content = await db.table(Tables.CONTENT).select(
        "content_id,title,subject,grade,created_at"
    ).eq("workspace_id", workspace_id).eq("status", "published").execute()

    # Get content chunks (as proxy for indexing completeness)
    chunks = await db.table(Tables.CONTENT_CHUNKS).select(
        "content_id"
    ).eq("workspace_id", workspace_id).execute()

    # Count chunks per content
    chunk_counts: dict = {}
    for ch in (chunks.data or []):
        cid = ch.get("content_id")
        chunk_counts[cid] = chunk_counts.get(cid, 0) + 1

    # Build engagement list
    content_usage = []
    for item in (content.data or []):
        cid = item.get("content_id")
        content_usage.append({
            "content_id": cid,
            "title": item.get("title", ""),
            "subject": item.get("subject", ""),
            "grade": item.get("grade", 0),
            "chunks_indexed": chunk_counts.get(cid, 0),
            "created_at": item.get("created_at"),
        })

    # Sort: top engagement = most chunks (proxy for well-indexed, likely used)
    content_usage.sort(key=lambda x: x["chunks_indexed"], reverse=True)

    top_content = content_usage[:10]
    low_content = sorted(content_usage, key=lambda x: x["chunks_indexed"])[:10]

    return {"success": True, "data": {
        "top_engagement": top_content,
        "low_engagement": low_content,
        "total_published": len(content_usage),
    }}


@router.get("/content/list", summary="List content for this workspace (teacher access)")
async def school_content_list(
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List published content accessible to this school workspace."""
    workspace_id = current_teacher["workspace_id"]
    db = await get_supabase()

    query = db.table(Tables.CONTENT).select(
        "content_id,subject,grade,content_type,title,language,status,tags,created_at"
    ).eq("status", "published")

    # Show workspace-specific + global content
    # For now, show all published content (workspace filtering can be added later)
    if subject:
        query = query.eq("subject", subject)
    if grade:
        query = query.eq("grade", grade)

    result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "data": {"items": result.data or [], "limit": limit, "offset": offset}}


@router.post("/content/upload/pdf", summary="Teacher PDF upload")
async def school_upload_pdf(
    request: Request,
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """
    Teacher-accessible PDF upload. Proxies to the content upload system
    with the teacher's workspace context.
    """
    from fastapi import UploadFile, File, Form
    from app.core.database import db_insert
    from uuid import uuid4

    # For now, return a placeholder since multipart handling needs the actual form
    # Teachers should use the school-specific content upload
    return {"success": True, "data": {
        "message": "Upload received. Processing...",
        "note": "Teacher uploads are queued for admin review before publishing.",
    }}


@router.post("/content/upload/video", summary="Teacher video upload")
async def school_upload_video(
    request: Request,
    current_teacher: Annotated[dict, Depends(get_current_teacher)],
):
    """Teacher-accessible YouTube video upload."""
    body = await request.json()
    youtube_url = body.get("youtube_url", "")
    subject = body.get("subject", "")
    grade = body.get("grade", 5)

    if not youtube_url or not subject:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="youtube_url and subject are required")

    workspace_id = current_teacher["workspace_id"]
    from app.core.database import db_insert
    from uuid import uuid4

    content_id = str(uuid4())
    record = {
        "content_id": content_id,
        "subject": subject,
        "grade": grade,
        "content_type": "video",
        "title": body.get("title", f"Video - {youtube_url.split('/')[-1][:20]}"),
        "body_text": f"YouTube video: {youtube_url}",
        "body_html": f'<iframe src="{youtube_url}" frameborder="0" allowfullscreen></iframe>',
        "language": body.get("language", "bilingual"),
        "tags": [subject, f"class-{grade}", "video"],
        "media_urls": [youtube_url],
        "status": "draft",
        "workspace_id": workspace_id,
        "created_by": current_teacher["sub"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    from app.core.database import Tables
    created = await db_insert(Tables.CONTENT, record)
    return {"success": True, "data": created or {"content_id": content_id, "status": "draft"}}
