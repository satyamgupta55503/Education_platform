"""
EduCat AI — Pydantic Schemas: Auth, User, Chat, Content, Admin
All API request/response models with full validation.
"""
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Shared Base ───────────────────────────────────────────────────
class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class PhoneSendOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=10,
                       description="10-digit Indian mobile number without country code")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not v.isdigit():
            raise ValueError("Phone must contain only digits")
        if v[0] not in "6789":
            raise ValueError("Phone must start with 6, 7, 8, or 9")
        return v


class PhoneVerifyOTPRequest(BaseModel):
    firebase_token: str = Field(..., description="Firebase ID token from phone OTP verification")
    grade: Optional[int] = Field(default=5, ge=1, le=10)
    language: Optional[Literal["hi", "en"]] = "hi"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserProfileResponse"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Teacher Auth
class TeacherGoogleCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class TeacherOTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class TeacherTOTPVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)
    device_fingerprint: str = Field(..., min_length=16)
    device_name: Optional[str] = "Unknown Device"


# Admin Auth
class AdminLoginRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    totp_code: Optional[str] = Field(default=None, min_length=6, max_length=6)


class QRCodeResponse(BaseModel):
    qr_code_svg: str
    secret_preview: str
    instructions: dict
    expires_in: int = 300


# ═══════════════════════════════════════════════════════════════════
# USER SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class UserProfileResponse(BaseModel):
    user_id: str
    grade: int
    language: str
    subscription_tier: str
    tokens_remaining: int
    total_tokens: int
    renewal_date: datetime
    brain_coins: int
    streak_days: int
    last_active_date: Optional[str]
    cat_config: dict
    tier_display_name: str
    created_at: datetime

    @property
    def tier_display_name(self) -> str:
        return {
            "free": "FREE",
            "smart": "SMART",
            "genius": "GENIUS",
        }.get(self.subscription_tier, "FREE")


class UserUpdateRequest(BaseModel):
    grade: Optional[int] = Field(default=None, ge=1, le=10)
    language: Optional[Literal["hi", "en"]] = None
    cat_config: Optional[dict] = None
    fcm_token: Optional[str] = None


class UserStatsResponse(BaseModel):
    total_sessions: int
    total_exchanges: int
    streak_days: int
    brain_coins: int
    favourite_subject: Optional[str]
    avg_session_duration_minutes: float
    subject_mastery: dict
    quiz_performance: dict
    learning_velocity: dict


# ═══════════════════════════════════════════════════════════════════
# CHAT SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class CreateSessionRequest(BaseModel):
    subject: Literal["science", "maths", "hindi", "english", "sst", "gk"]
    topic: str = Field(..., min_length=2, max_length=200)
    grade: Optional[int] = Field(default=None, ge=1, le=10)


class CreateSessionResponse(BaseModel):
    session_id: str
    subject: str
    topic: str
    grade: int
    context_injected: dict


class SendMessageRequest(BaseModel):
    session_id: str
    question: str = Field(..., min_length=1, max_length=500)
    input_type: Literal["text", "voice"] = "text"
    subject: Optional[str] = None
    language: Optional[Literal["hi", "en"]] = None


class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)
    subject: Literal["science", "maths", "hindi", "english", "sst", "gk"]
    grade: int = Field(..., ge=1, le=10)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    count: int = Field(default=5, ge=3, le=10)


class QuizQuestion(BaseModel):
    q_id: str
    question: str
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)
    explanation: str
    difficulty: str
    ncert_reference: Optional[str] = None


class QuizResponse(BaseModel):
    quiz_id: str
    questions: list[QuizQuestion]
    topic: str
    estimated_time_minutes: int


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: dict[str, int]  # {q_id: selected_index}


class QuizSubmitResponse(BaseModel):
    quiz_id: str
    score: int
    total: int
    percentage: float
    brain_coins_earned: int
    feedback: list[dict]


class SessionHistoryResponse(BaseModel):
    session_id: str
    subject: str
    topic: str
    grade: int
    exchange_count: int
    coins_earned: int
    started_at: datetime
    last_message_at: Optional[datetime]
    ai_summary: Optional[str]


class MessageResponse(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


# ═══════════════════════════════════════════════════════════════════
# CONTENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class ContentCreateRequest(BaseModel):
    subject: Literal["science", "maths", "hindi", "english", "sst", "gk"]
    grade: int = Field(..., ge=0, le=10, description="0 = all grades")
    content_type: Literal["lesson", "quiz", "pdf", "video", "flashcard", "worksheet"]
    title: str = Field(..., min_length=3, max_length=200)
    body_text: str = Field(..., min_length=10)
    body_html: Optional[str] = None
    language: Literal["hi", "en", "bilingual"] = "bilingual"
    tags: list[str] = Field(default_factory=list)
    workspace_id: Optional[str] = None
    video_url: Optional[str] = None


class ContentResponse(BaseModel):
    content_id: str
    subject: str
    grade: int
    content_type: str
    title: str
    body_html: Optional[str]
    media_urls: list[dict]
    language: str
    status: str
    tags: list[str]
    difficulty: Optional[str]
    created_at: datetime


class UploadBatchResponse(BaseModel):
    batch_id: str
    files_received: int
    processing_status: str
    estimated_completion: str
    status_url: str


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: Literal["queued", "processing", "complete", "failed"]
    files_processed: int
    files_total: int
    chunks_created: int
    duplicates_detected: int
    errors: list[str]


# ═══════════════════════════════════════════════════════════════════
# SUBSCRIPTION SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class PlanInfo(BaseModel):
    plan_id: str
    name: str
    price_monthly: int
    price_annual: int
    tokens_monthly: int
    daily_cap: int
    features: list[str]
    is_popular: bool = False


class CreateOrderRequest(BaseModel):
    plan_id: Literal["smart_monthly", "smart_annual", "genius_monthly", "genius_annual"]


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str = "INR"
    razorpay_key_id: str


class ActivateSubscriptionRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str


class SubscriptionStatusResponse(BaseModel):
    tier: str
    tokens_remaining: int
    total_tokens: int
    renewal_date: datetime
    is_active: bool
    plan_display_name: str


# ═══════════════════════════════════════════════════════════════════
# ADMIN SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class WorkspaceCreateRequest(BaseModel):
    school_name: str = Field(..., min_length=3, max_length=200)
    admin_email: EmailStr
    subscription_plan: Literal["classroom", "institute", "campus_plus"] = "classroom"
    max_teachers: int = Field(default=5, ge=1, le=1000)
    monthly_query_quota: int = Field(default=10000, ge=100)


class WorkspaceResponse(BaseModel):
    workspace_id: str
    school_name: str
    school_code: str
    subscription_plan: str
    max_teachers: int
    monthly_query_quota: int
    queries_used: int
    is_active: bool
    admin_email: str
    expires_at: datetime
    created_at: datetime
    teacher_count: int = 0


class AdminInviteRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    role: Literal["admin", "helper"]


class DashboardStats(BaseModel):
    dau: int
    mau: int
    total_students: int
    paid_students: int
    active_schools: int
    queries_today: int
    mrr_paise: int
    safety_queue_depth: int
    cache_hit_rate: float


# ═══════════════════════════════════════════════════════════════════
# TEACHER SCHEMAS
# ═══════════════════════════════════════════════════════════════════
class LessonStartRequest(BaseModel):
    subject: Literal["science", "maths", "hindi", "english", "sst", "gk"]
    topic: str = Field(..., min_length=2, max_length=200)
    class_name: str = Field(..., description="e.g. '7-A', 'Class 8 Biology'")
    grade: int = Field(..., ge=1, le=10)


class LessonQuestionRequest(BaseModel):
    lesson_id: str
    question: str = Field(..., min_length=2, max_length=500)
    language: Literal["hi", "en"] = "hi"


class TeacherAnalyticsResponse(BaseModel):
    total_lessons: int
    total_questions_asked: int
    avg_lesson_duration_minutes: float
    top_topics: list[str]
    queries_used_this_month: int
    queries_remaining: int


# Forward reference resolution
TokenResponse.model_rebuild()
