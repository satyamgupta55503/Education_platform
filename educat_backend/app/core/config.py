"""
EduCat AI — Core Configuration
All environment variables loaded via pydantic-settings.
Never hardcode secrets — always use .env or Railway env vars.
"""
from functools import lru_cache
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────
    APP_NAME: str = "EduCat AI Backend"
    APP_VERSION: str = "3.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",       # Teacher dashboard dev
        "http://localhost:3001",       # Alt dev port
        "http://localhost:3002",       # Admin dashboard dev
        "http://localhost:5173",       # Admin panel dev
        "https://teacher.educat.ai",
        "https://admin.educat.ai",
        "https://educat.ai",
    ]

    # ── Supabase ─────────────────────────────────────────────────
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anon/public key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Service role key — NEVER expose")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT secret for custom auth")

    # ── Redis ─────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5

    # ── JWT ───────────────────────────────────────────────────────
    JWT_PRIVATE_KEY: str = Field(..., description="RSA-4096 private key for RS256 signing")
    JWT_PUBLIC_KEY: str = Field(..., description="RSA-4096 public key for verification")
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_TEACHER_EXPIRE_HOURS: int = 8
    JWT_ADMIN_EXPIRE_HOURS: int = 4
    JWT_HELPER_EXPIRE_HOURS: int = 4

    # ── Firebase ─────────────────────────────────────────────────
    FIREBASE_SERVICE_ACCOUNT_JSON: str = Field(..., description="Base64-encoded Firebase SA JSON")
    FIREBASE_PROJECT_ID: str = Field(default="educat-ai-prod")

    # ── Google OAuth2 (School/Teacher) ───────────────────────────
    GOOGLE_CLIENT_ID: str = Field(...)
    GOOGLE_CLIENT_SECRET: str = Field(...)
    GOOGLE_REDIRECT_URI: str = Field(default="https://teacher.educat.ai/auth/callback")

    # ── Gemini AI ─────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(..., description="Google AI Studio API key — NEVER expose to clients")
    GEMINI_MODEL_FREE: str = "gemini-2.0-flash-lite"
    GEMINI_MODEL_PAID: str = "gemini-2.5-flash"
    GEMINI_EMBED_MODEL: str = "models/text-embedding-004"
    GEMINI_EMBED_DIMENSIONS: int = 1536
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048
    GEMINI_STREAM_TIMEOUT: int = 60

    # ── RAG Settings ─────────────────────────────────────────────
    RAG_TOP_K: int = 7
    RAG_BM25_WEIGHT: float = 0.4
    RAG_VECTOR_WEIGHT: float = 0.6
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 128

    # ── Semantic Cache ────────────────────────────────────────────
    SEMANTIC_CACHE_THRESHOLD_DEFAULT: float = 0.92
    SEMANTIC_CACHE_TTL_DAYS: int = 30
    SEMANTIC_CACHE_ENABLED: bool = True

    # ── Rate Limiting ─────────────────────────────────────────────
    RATE_LIMIT_FREE: str = "60/minute"
    RATE_LIMIT_SMART: str = "200/minute"
    RATE_LIMIT_GENIUS: str = "500/minute"
    RATE_LIMIT_SCHOOL: str = "1000/minute"
    RATE_LIMIT_ADMIN: str = "300/minute"

    # ── Razorpay ─────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = Field(...)
    RAZORPAY_KEY_SECRET: str = Field(...)
    RAZORPAY_WEBHOOK_SECRET: str = Field(...)

    # ── Subscription Pricing ──────────────────────────────────────
    SMART_PLAN_PRICE_MONTHLY: int = 7900      # paise (Rs.79)
    SMART_PLAN_PRICE_ANNUAL: int = 69900      # paise (Rs.699)
    GENIUS_PLAN_PRICE_MONTHLY: int = 19900    # paise (Rs.199)
    GENIUS_PLAN_PRICE_ANNUAL: int = 179900    # paise (Rs.1799)
    SCHOOL_CLASSROOM_PRICE: int = 70000       # paise (Rs.700)
    SCHOOL_INSTITUTE_PRICE: int = 100000      # paise (Rs.1000)

    # ── Token Quotas ─────────────────────────────────────────────
    TOKEN_QUOTA_FREE: int = 25
    TOKEN_QUOTA_SMART: int = 250
    TOKEN_QUOTA_GENIUS: int = 600
    TOKEN_DAILY_CAP_FREE: int = 2
    TOKEN_DAILY_CAP_SMART: int = 15
    TOKEN_DAILY_CAP_GENIUS: int = 30

    # ── Google Cloud (TTS/STT/Vision) ─────────────────────────────
    GOOGLE_CLOUD_PROJECT_ID: str = Field(default="")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="")

    # ── Security ─────────────────────────────────────────────────
    FERNET_KEY: str = Field(..., description="AES-256 Fernet key for encrypting TOTP secrets")
    TOTP_ISSUER_NAME: str = "EduCat School"
    TOTP_VALID_WINDOW: int = 1       # 30s tolerance
    OTP_EXPIRE_MINUTES: int = 10
    OTP_ADMIN_EXPIRE_MINUTES: int = 5
    MAX_OTP_ATTEMPTS: int = 3
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    # ── Celery ───────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # ── Storage ───────────────────────────────────────────────────
    SUPABASE_STORAGE_BUCKET_CONTENT: str = "content"
    SUPABASE_STORAGE_BUCKET_AUDIO: str = "audio"
    SUPABASE_STORAGE_BUCKET_AVATARS: str = "avatars"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── DPDP / Data Retention ─────────────────────────────────────
    FREE_HISTORY_DAYS: int = 3
    SMART_HISTORY_DAYS: int = 60
    DATA_PURGE_AFTER_DELETE_DAYS: int = 30

    # ── Sentry ───────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        return v.lower()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def semantic_cache_thresholds(self) -> dict:
        return {
            "maths":   0.96,
            "science": 0.92,
            "hindi":   0.89,
            "english": 0.91,
            "sst":     0.90,
            "gk":      0.87,
            "default": self.SEMANTIC_CACHE_THRESHOLD_DEFAULT,
        }

    @property
    def daily_caps(self) -> dict:
        return {
            "free":   self.TOKEN_DAILY_CAP_FREE,
            "smart":  self.TOKEN_DAILY_CAP_SMART,
            "genius": self.TOKEN_DAILY_CAP_GENIUS,
        }

    @property
    def monthly_quotas(self) -> dict:
        return {
            "free":   self.TOKEN_QUOTA_FREE,
            "smart":  self.TOKEN_QUOTA_SMART,
            "genius": self.TOKEN_QUOTA_GENIUS,
        }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — call this everywhere."""
    return Settings()


settings = get_settings()
