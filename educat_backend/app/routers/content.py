"""
EduCat AI — Content Router
Multi-file upload, async processing, RAG indexing.
"""
import io
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi import status as http_status

from app.core.config import settings
from app.core.database import Tables, db_fetch_many, db_fetch_one, db_insert, db_update, get_supabase
from app.core.dependencies import get_current_admin, get_current_admin_or_above
from app.schemas.schemas import ContentCreateRequest
import structlog

log = structlog.get_logger()
router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png", "image/jpeg", "image/webp", "image/gif",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


# ── List / Search Content ─────────────────────────────────────────
@router.get("", summary="List content with filters")
async def list_content(
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    db = await get_supabase()
    query = db.table(Tables.CONTENT).select(
        "content_id, subject, grade, content_type, title, language, status, tags, created_at"
    )
    if subject:      query = query.eq("subject", subject)
    if grade:        query = query.eq("grade", grade)
    if content_type: query = query.eq("content_type", content_type)
    if status:       query = query.eq("status", status)
    if language:     query = query.eq("language", language)
    if search:       query = query.ilike("title", f"%{search}%")

    result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "data": {"items": result.data or [], "limit": limit, "offset": offset}}


@router.get("/list", summary="List content (alias for GET /content)", include_in_schema=False)
async def list_content_alias(
    request: Request,
    subject: Optional[str] = None,
    grade: Optional[int] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Alias: GET /content/list — accessible by both admin and teacher tokens."""
    db = await get_supabase()
    query = db.table(Tables.CONTENT).select(
        "content_id, subject, grade, content_type, title, language, status, tags, created_at"
    ).eq("status", "published")
    if subject:      query = query.eq("subject", subject)
    if grade:        query = query.eq("grade", grade)
    if content_type: query = query.eq("content_type", content_type)
    if language:     query = query.eq("language", language)
    if search:       query = query.ilike("title", f"%{search}%")

    result = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "data": {"items": result.data or [], "limit": limit, "offset": offset}}


# ── Get Single Content ────────────────────────────────────────────
@router.get("/{content_id}", summary="Get content by ID")
async def get_content(
    content_id: str,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    item = await db_fetch_one(Tables.CONTENT, {"content_id": content_id})
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"success": True, "data": item}


# ── Create Content (text) ─────────────────────────────────────────
@router.post("", summary="Create content item (text-based)")
async def create_content(
    body: ContentCreateRequest,
    background: BackgroundTasks,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    admin_id = current_admin["sub"]
    role = current_admin.get("role", "helper")
    # Helpers create drafts; admins can directly create as review-ready
    initial_status = "draft" if role == "helper" else "review"

    content_id = str(uuid.uuid4())
    record = {
        "content_id":   content_id,
        "subject":      body.subject,
        "grade":        body.grade,
        "content_type": body.content_type,
        "title":        body.title,
        "body_text":    body.body_text,
        "body_html":    body.body_html or f"<p>{body.body_text}</p>",
        "language":     body.language,
        "tags":         body.tags,
        "media_urls":   [],
        "status":       initial_status,
        "workspace_id": body.workspace_id,
        "created_by":   admin_id,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }

    created = await db_insert(Tables.CONTENT, record)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create content")

    # Queue embedding generation
    background.add_task(_generate_embedding_bg, content_id, body.body_text)

    log.info("content_created", content_id=content_id, subject=body.subject, grade=body.grade)
    return {"success": True, "data": created}


# ── Upload Files ──────────────────────────────────────────────────
@router.post("/upload", summary="Upload PDF/Image files for content")
async def upload_content_files(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    subject: str = Form(...),
    grade: int = Form(...),
    content_type: str = Form(default="lesson"),
    language: str = Form(default="bilingual"),
    workspace_id: Optional[str] = Form(default=None),
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files per upload")

    admin_id = current_admin["sub"]
    batch_id = str(uuid.uuid4())

    accepted, rejected = [], []

    for f in files:
        # Validate size
        content = await f.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            rejected.append({"name": f.filename, "reason": "File too large"})
            continue

        # Validate type
        ext = "." + f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if f.content_type not in ALLOWED_MIME_TYPES and ext not in ALLOWED_EXTENSIONS:
            rejected.append({"name": f.filename, "reason": "Unsupported file type"})
            continue

        file_id = str(uuid.uuid4())
        accepted.append({
            "file_id":   file_id,
            "filename":  f.filename,
            "mime_type": f.content_type,
            "content":   content,
            "size_bytes": len(content),
        })

    if not accepted:
        raise HTTPException(status_code=400, detail=f"No valid files. Rejected: {rejected}")

    # Queue batch processing
    background.add_task(
        _process_file_batch,
        batch_id, accepted, subject, grade,
        content_type, language, workspace_id, admin_id
    )

    log.info("upload_batch_queued", batch_id=batch_id, files=len(accepted))
    return {"success": True, "data": {
        "batch_id":           batch_id,
        "files_received":     len(accepted),
        "files_rejected":     rejected,
        "processing_status":  "queued",
        "status_url":         f"/api/v1/content/batch/{batch_id}/status",
    }}


@router.post("/upload/pdf", summary="Upload PDF files (alias for /upload)", include_in_schema=False)
async def upload_pdf_alias(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    subject: str = Form(...),
    grade: int = Form(...),
    content_type: str = Form(default="lesson"),
    language: str = Form(default="bilingual"),
    workspace_id: Optional[str] = Form(default=None),
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Alias: POST /content/upload/pdf → same handler as POST /content/upload."""
    return await upload_content_files(
        background=background, files=files, subject=subject,
        grade=grade, content_type=content_type, language=language,
        workspace_id=workspace_id, current_admin=current_admin,
    )


@router.post("/upload/video", summary="Upload video content (YouTube URL)")
async def upload_video_content(
    background: BackgroundTasks,
    request: Request,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    """
    Create content from a YouTube video URL.
    Accepts: youtube_url, subject, grade, workspace_id.
    """
    body = await request.json()
    youtube_url = body.get("youtube_url", "")
    subject = body.get("subject", "")
    grade = body.get("grade", 5)
    workspace_id = body.get("workspace_id")

    if not youtube_url or not subject:
        raise HTTPException(status_code=422, detail="youtube_url and subject are required")

    # Validate URL format
    import re
    yt_pattern = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)[\w\-]+'
    )
    if not yt_pattern.match(youtube_url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL format")

    admin_id = current_admin["sub"]
    content_id = str(uuid.uuid4())

    # Extract video title from URL (best effort)
    video_title = body.get("title", f"Video - {youtube_url.split('/')[-1][:20]}")

    record = {
        "content_id":   content_id,
        "subject":      subject,
        "grade":        grade,
        "content_type": "video",
        "title":        video_title,
        "body_text":    f"YouTube video: {youtube_url}",
        "body_html":    f'<iframe src="{youtube_url}" frameborder="0" allowfullscreen></iframe>',
        "language":     body.get("language", "bilingual"),
        "tags":         [subject, f"class-{grade}", "video"],
        "media_urls":   [youtube_url],
        "status":       "draft",
        "workspace_id": workspace_id,
        "created_by":   admin_id,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }

    created = await db_insert(Tables.CONTENT, record)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create video content")

    log.info("video_content_created", content_id=content_id, url=youtube_url[:50])
    return {"success": True, "data": created}


@router.get("/batch/{batch_id}/status", summary="Get upload batch processing status")
async def get_batch_status(
    batch_id: str,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    from app.core.redis_client import cache_get
    status_data = await cache_get(f"batch:{batch_id}")
    if not status_data:
        raise HTTPException(status_code=404, detail="Batch not found or expired")
    return {"success": True, "data": status_data}


# ── Publish Content ───────────────────────────────────────────────
@router.post("/{content_id}/publish", summary="Publish content (Admin only)")
async def publish_content(
    content_id: str,
    background: BackgroundTasks,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    admin_id = current_admin["sub"]
    item = await db_fetch_one(Tables.CONTENT, {"content_id": content_id})
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    await db_update(Tables.CONTENT, {"content_id": content_id}, {
        "status":      "published",
        "approved_by": admin_id,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    })

    # Regenerate embedding with published content
    background.add_task(_generate_embedding_bg, content_id, item["body_text"])
    # Invalidate BM25 index for subject+grade
    background.add_task(_invalidate_bm25_cache, item["subject"], item["grade"])

    log.info("content_published", content_id=content_id, admin=admin_id)
    return {"success": True, "data": {"content_id": content_id, "status": "published"}}


# ── Update / Delete Content ───────────────────────────────────────
@router.patch("/{content_id}", summary="Update content")
async def update_content(
    content_id: str,
    body: dict,
    background: BackgroundTasks,
    current_admin: Annotated[dict, Depends(get_current_admin)] = None,
):
    allowed_fields = {"title", "body_text", "body_html", "tags", "language", "grade", "subject"}
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    updated = await db_update(Tables.CONTENT, {"content_id": content_id}, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")

    if "body_text" in updates:
        background.add_task(_generate_embedding_bg, content_id, updates["body_text"])

    return {"success": True, "data": updated}


@router.delete("/{content_id}", summary="Archive content (soft delete)")
async def archive_content(
    content_id: str,
    current_admin: Annotated[dict, Depends(get_current_admin_or_above)] = None,
):
    await db_update(Tables.CONTENT, {"content_id": content_id}, {
        "status": "archived",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "data": {"archived": True}}


# ── Background Processing ─────────────────────────────────────────
async def _generate_embedding_bg(content_id: str, text: str):
    """Generate and store vector embedding for content chunk."""
    try:
        from app.services.ai.gemini_service import generate_document_embedding
        from app.core.database import get_supabase
        embedding = await generate_document_embedding(text)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        db = await get_supabase()
        await db.table(Tables.CONTENT).update({
            "vector_embedding": embedding_str
        }).eq("content_id", content_id).execute()

        # Also create chunks
        await _create_chunks(content_id, text, embedding)

        log.info("embedding_generated", content_id=content_id)
    except Exception as e:
        log.error("embedding_failed", content_id=content_id, error=str(e))


async def _create_chunks(content_id: str, text: str, full_embedding: list):
    """Split text into 512-token chunks with 128 overlap and embed each."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback: rough split by ~400 words
        words = text.split()
        chunks_text = [
            " ".join(words[i:i+400])
            for i in range(0, len(words), 272)  # 400-128 overlap
        ]
    else:
        tokens = enc.encode(text)
        size, overlap = settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP
        chunks_text = []
        for i in range(0, len(tokens), size - overlap):
            chunk_tokens = tokens[i:i + size]
            chunks_text.append(enc.decode(chunk_tokens))

    # Fetch content metadata
    item = await db_fetch_one(Tables.CONTENT, {"content_id": content_id})
    if not item:
        return

    from app.services.ai.gemini_service import generate_document_embedding
    from app.services.ai.rag_pipeline import get_difficulty_classifier
    classifier = get_difficulty_classifier()
    db = await get_supabase()

    for i, chunk_text in enumerate(chunks_text):
        if len(chunk_text.strip()) < 20:
            continue
        emb = await generate_document_embedding(chunk_text)
        emb_str = "[" + ",".join(map(str, emb)) + "]"
        difficulty = classifier.classify(chunk_text[:100], item.get("grade", 5), item.get("subject", "science"))

        await db.table(Tables.CONTENT_CHUNKS).insert({
            "chunk_id":    str(uuid.uuid4()),
            "content_id":  content_id,
            "workspace_id": item.get("workspace_id"),
            "subject":     item["subject"],
            "grade":       item["grade"],
            "chunk_text":  chunk_text,
            "chunk_index": i,
            "embedding":   emb_str,
            "difficulty":  difficulty,
            "language":    item.get("language", "bilingual"),
            "source_type": item.get("content_type", "lesson"),
            "created_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()


async def _process_file_batch(
    batch_id: str, files: list, subject: str, grade: int,
    content_type: str, language: str, workspace_id: Optional[str], admin_id: str,
):
    """Process uploaded files: extract text, chunk, embed, index."""
    from app.core.redis_client import cache_set
    status = {
        "batch_id": batch_id, "status": "processing",
        "files_processed": 0, "files_total": len(files),
        "chunks_created": 0, "duplicates_detected": 0, "errors": [],
    }
    await cache_set(f"batch:{batch_id}", status, ttl_seconds=86400)

    for i, file_info in enumerate(files):
        try:
            mime   = file_info["mime_type"]
            content = file_info["content"]
            fname  = file_info["filename"]

            # Extract text
            extracted_text = await _extract_text(content, mime, language)
            if not extracted_text.strip():
                status["errors"].append(f"{fname}: No text extracted")
                continue

            # Create content record
            content_id = str(uuid.uuid4())
            await db_insert(Tables.CONTENT, {
                "content_id":   content_id,
                "subject":      subject,
                "grade":        grade,
                "content_type": content_type,
                "title":        fname.rsplit(".", 1)[0].replace("_", " ").title(),
                "body_text":    extracted_text,
                "body_html":    f"<p>{extracted_text[:500]}...</p>",
                "language":     language,
                "tags":         [subject, f"class-{grade}"],
                "media_urls":   [],
                "status":       "draft",
                "workspace_id": workspace_id,
                "created_by":   admin_id,
                "created_at":   datetime.now(timezone.utc).isoformat(),
                "updated_at":   datetime.now(timezone.utc).isoformat(),
            })

            # Generate embedding + chunks
            await _generate_embedding_bg(content_id, extracted_text)

            status["files_processed"] += 1
        except Exception as e:
            status["errors"].append(f"{file_info['filename']}: {str(e)}")
            log.error("file_processing_failed", filename=file_info["filename"], error=str(e))

    status["status"] = "complete"
    await cache_set(f"batch:{batch_id}", status, ttl_seconds=86400)
    log.info("batch_complete", batch_id=batch_id, processed=status["files_processed"])


async def _extract_text(content: bytes, mime_type: str, language: str) -> str:
    """Extract text from PDF or image."""
    if mime_type == "application/pdf":
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                # Extract tables
                for table in page.extract_tables():
                    for row in table:
                        text += " | ".join([str(c or "") for c in row]) + "\n"
        return text.strip()

    elif mime_type.startswith("image/"):
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            if response.text_annotations:
                return response.text_annotations[0].description
        except Exception:
            pass
        # Fallback: pytesseract
        try:
            import pytesseract
            from PIL import Image
            lang_map = {"hi": "hin", "en": "eng", "bilingual": "hin+eng"}
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img, lang=lang_map.get(language, "hin+eng"))
        except Exception:
            return ""
    return ""


async def _invalidate_bm25_cache(subject: str, grade: int):
    """Signal RAG pipeline to rebuild BM25 index for this subject+grade."""
    from app.services.ai.rag_pipeline import get_search_engine
    engine = get_search_engine()
    cache_key = f"{subject}_{grade}"
    engine._bm25_cache.pop(cache_key, None)
    engine._bm25_chunk_ids.pop(cache_key, None)
    log.info("bm25_cache_invalidated", subject=subject, grade=grade)
