-- ════════════════════════════════════════════════════════════════
-- EduCat AI — Complete Database Schema (FIXED ORDER)
-- PostgreSQL 15 + pgvector
-- Run on Supabase SQL Editor
-- ════════════════════════════════════════════════════════════════

-- ── Extensions ───────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ════════════════════════════════════════════════════════════════
-- HELPER FUNCTION: Create Monthly Partitions (MUST BE FIRST)
-- ════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION create_monthly_partitions(
    p_table TEXT,
    p_months INT DEFAULT 12
)
RETURNS VOID AS $$
DECLARE
    v_start DATE;
    v_end   DATE;
    v_name  TEXT;
BEGIN
    FOR i IN 0..p_months LOOP
        v_start := DATE_TRUNC('month', NOW() + (i || ' months')::INTERVAL);
        v_end   := v_start + INTERVAL '1 month';
        v_name  := p_table || '_' || TO_CHAR(v_start, 'YYYY_MM');
        EXECUTE FORMAT(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
             FOR VALUES FROM (%L) TO (%L)',
            v_name, p_table, v_start, v_end
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ════════════════════════════════════════════════════════════════
-- CORE TABLES
-- ════════════════════════════════════════════════════════════════

-- ── Users (Students) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash          TEXT UNIQUE NOT NULL,
    firebase_uid        TEXT UNIQUE NOT NULL,
    grade               SMALLINT NOT NULL DEFAULT 5 CHECK (grade BETWEEN 1 AND 10),
    language            TEXT NOT NULL DEFAULT 'hi' CHECK (language IN ('hi','en')),
    subscription_tier   TEXT NOT NULL DEFAULT 'free'
                            CHECK (subscription_tier IN ('free','smart','genius')),
    tokens_remaining    INT NOT NULL DEFAULT 25 CHECK (tokens_remaining >= 0),
    total_tokens        INT NOT NULL DEFAULT 25,
    renewal_date        TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days',
    brain_coins         INT NOT NULL DEFAULT 0 CHECK (brain_coins >= 0),
    streak_days         INT NOT NULL DEFAULT 0 CHECK (streak_days >= 0),
    last_active_date    DATE DEFAULT CURRENT_DATE,
    cat_config          JSONB DEFAULT '{}',
    fcm_token           TEXT,
    is_suspended        BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Workspaces (Schools) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_name         TEXT NOT NULL,
    school_code         TEXT UNIQUE NOT NULL,
    subscription_plan   TEXT NOT NULL DEFAULT 'classroom'
                            CHECK (subscription_plan IN ('classroom','institute','campus_plus')),
    max_teachers        INT NOT NULL DEFAULT 5,
    monthly_query_quota INT NOT NULL DEFAULT 10000,
    queries_used        INT NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    admin_email         TEXT NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Teachers ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teachers (
    teacher_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id           UUID NOT NULL REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
    name                   TEXT NOT NULL,
    email                  TEXT UNIQUE NOT NULL,
    school_code            TEXT,
    subject_specialisation TEXT[] DEFAULT '{}',
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    last_login             TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Teacher Devices (TOTP) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_devices (
    device_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id              UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    workspace_id            UUID NOT NULL,
    device_fingerprint      TEXT NOT NULL,
    device_name             TEXT DEFAULT 'Unknown Device',
    totp_secret_encrypted   TEXT NOT NULL,
    is_trusted              BOOLEAN NOT NULL DEFAULT FALSE,
    last_used               TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at              TIMESTAMPTZ,
    UNIQUE(teacher_id, device_fingerprint)
);

-- ── Admin Users ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
    admin_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   TEXT UNIQUE NOT NULL,
    name                    TEXT NOT NULL,
    role                    TEXT NOT NULL CHECK (role IN ('superadmin','admin','helper')),
    totp_secret_encrypted   TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_login              TIMESTAMPTZ,
    login_count             INT DEFAULT 0,
    created_by              UUID REFERENCES admin_users(admin_id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Token Families (JWT Refresh Rotation) ────────────────────────
CREATE TABLE IF NOT EXISTS token_families (
    family_id   UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    last_jti    TEXT NOT NULL,
    is_valid    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- CHAT TABLES (Partitioned by Month)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id      UUID DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subject         TEXT NOT NULL,
    topic           TEXT NOT NULL,
    grade           SMALLINT NOT NULL,
    exchange_count  INT NOT NULL DEFAULT 0,
    coins_earned    INT NOT NULL DEFAULT 0,
    is_archived     BOOLEAN DEFAULT FALSE,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    PRIMARY KEY (session_id, started_at)
) PARTITION BY RANGE (started_at);

SELECT create_monthly_partitions('chat_sessions', 12);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id  UUID DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL,
    user_id     UUID NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content     TEXT NOT NULL,
    token_count INT DEFAULT 0,
    is_flagged  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (message_id, created_at)
) PARTITION BY RANGE (created_at);

SELECT create_monthly_partitions('chat_messages', 12);

CREATE TABLE IF NOT EXISTS session_summaries (
    summary_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL,
    user_id      UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    subject      TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id  UUID DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    quiz_id     TEXT NOT NULL,
    topic       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    grade       SMALLINT NOT NULL,
    score       INT NOT NULL,
    total       INT NOT NULL,
    percentage  FLOAT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (attempt_id, created_at)
) PARTITION BY RANGE (created_at);

SELECT create_monthly_partitions('quiz_attempts', 12);

-- ═══════════════════════════════════════════════════════════════
-- CONTENT / RAG TABLES
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS content (
    content_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     UUID REFERENCES workspaces(workspace_id),
    subject          TEXT NOT NULL,
    grade            SMALLINT NOT NULL CHECK (grade BETWEEN 0 AND 10),
    content_type     TEXT NOT NULL
                         CHECK (content_type IN ('lesson','quiz','pdf','video','flashcard','worksheet')),
    title            TEXT NOT NULL,
    body_text        TEXT NOT NULL,
    body_html        TEXT,
    media_urls       JSONB DEFAULT '[]',
    vector_embedding VECTOR(1536),
    tags             TEXT[] DEFAULT '{}',
    language         TEXT DEFAULT 'bilingual' CHECK (language IN ('hi','en','bilingual')),
    status           TEXT NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft','review','published','archived')),
    created_by       UUID REFERENCES admin_users(admin_id),
    approved_by      UUID REFERENCES admin_users(admin_id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS content_chunks (
    chunk_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id       UUID NOT NULL REFERENCES content(content_id) ON DELETE CASCADE,
    workspace_id     UUID,
    subject          TEXT NOT NULL,
    grade            SMALLINT NOT NULL,
    chunk_text       TEXT NOT NULL,
    chunk_index      INT NOT NULL DEFAULT 0,
    embedding        VECTOR(1536) NOT NULL,
    difficulty       TEXT DEFAULT 'medium' CHECK (difficulty IN ('easy','medium','hard')),
    language         TEXT DEFAULT 'bilingual',
    source_type      TEXT DEFAULT 'lesson',
    source_url       TEXT,
    alpha_score      FLOAT NOT NULL DEFAULT 1.0,
    beta_score       FLOAT NOT NULL DEFAULT 1.0,
    ncert_chapter_id INT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS semantic_cache (
    cache_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    embedding     VECTOR(1536) NOT NULL,
    subject       TEXT NOT NULL,
    grade         SMALLINT NOT NULL,
    hit_count     INT NOT NULL DEFAULT 0,
    last_hit_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);

CREATE TABLE IF NOT EXISTS audio_cache (
    cache_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key    TEXT UNIQUE NOT NULL,
    audio_url    TEXT NOT NULL,
    language     TEXT NOT NULL,
    voice_id     TEXT,
    text_hash    TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days'
);

-- ═══════════════════════════════════════════════════════════════
-- SUBSCRIPTION & PAYMENTS
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id       UUID DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL,
    plan_id               TEXT NOT NULL,
    tier                  TEXT NOT NULL,
    razorpay_order_id     TEXT,
    razorpay_payment_id   TEXT,
    status                TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','active','failed','cancelled','expired')),
    amount_paise          INT NOT NULL,
    renewal_date          TIMESTAMPTZ,
    activated_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (subscription_id, created_at),
    UNIQUE (razorpay_order_id, created_at)
) PARTITION BY RANGE (created_at);

SELECT create_monthly_partitions('subscriptions', 12);

-- ═══════════════════════════════════════════════════════════════
-- ANALYTICS & AUDIT
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS student_progress (
    progress_id           UUID DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL,
    subject               TEXT NOT NULL,
    grade                 SMALLINT NOT NULL,
    topic                 TEXT NOT NULL,
    interaction_type      TEXT,
    difficulty_level      TEXT,
    response_quality      TEXT,
    knowledge_probability FLOAT DEFAULT 0.1 CHECK (knowledge_probability BETWEEN 0 AND 1),
    session_id            UUID,
    recorded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (progress_id, recorded_at),
    UNIQUE (user_id, subject, grade, topic, recorded_at)
) PARTITION BY RANGE (recorded_at);

SELECT create_monthly_partitions('student_progress', 12);

CREATE TABLE IF NOT EXISTS otp_attempts (
    attempt_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier   TEXT NOT NULL,
    attempt_type TEXT NOT NULL,
    success      BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id     UUID DEFAULT gen_random_uuid(),
    admin_id   UUID,
    action     TEXT NOT NULL,
    target_id  TEXT,
    detail     TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

SELECT create_monthly_partitions('audit_log', 12);

-- ════════════════════════════════════════════════════════════════
-- INDEXES
-- ════════════════════════════════════════════════════════════════

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_hash   ON users (phone_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_firebase_uid ON users (firebase_uid);
CREATE INDEX IF NOT EXISTS idx_users_tier                ON users (subscription_tier);
CREATE INDEX IF NOT EXISTS idx_users_grade               ON users (grade);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspaces_code    ON workspaces (school_code);
CREATE INDEX IF NOT EXISTS idx_workspaces_active         ON workspaces (is_active);

CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_email     ON teachers (email);
CREATE INDEX IF NOT EXISTS idx_teachers_workspace        ON teachers (workspace_id, is_active);

CREATE INDEX IF NOT EXISTS idx_token_families_user       ON token_families (user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_user_date        ON chat_sessions (user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_subject          ON chat_sessions (user_id, subject);

CREATE INDEX IF NOT EXISTS idx_messages_session          ON chat_messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_flagged          ON chat_messages (is_flagged) WHERE is_flagged = TRUE;

CREATE INDEX IF NOT EXISTS idx_content_subject_grade     ON content (subject, grade, status);
CREATE INDEX IF NOT EXISTS idx_content_status            ON content (status);
CREATE INDEX IF NOT EXISTS idx_content_title_trgm        ON content USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_content_workspace         ON content (workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_chunks_hnsw
    ON content_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_chunks_subject_grade      ON content_chunks (subject, grade);
CREATE INDEX IF NOT EXISTS idx_chunks_content            ON content_chunks (content_id);

CREATE INDEX IF NOT EXISTS idx_cache_hnsw
    ON semantic_cache USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_cache_subject_grade       ON semantic_cache (subject, grade);
CREATE INDEX IF NOT EXISTS idx_cache_expires             ON semantic_cache (expires_at);

CREATE INDEX IF NOT EXISTS idx_progress_user_subject     ON student_progress (user_id, subject, grade);
CREATE INDEX IF NOT EXISTS idx_summaries_user_subject    ON session_summaries (user_id, subject, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_admin               ON audit_log (admin_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_otp_identifier            ON otp_attempts (identifier, created_at DESC);

-- ════════════════════════════════════════════════════════════════
-- RPC FUNCTIONS
-- ════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION hybrid_vector_search(
    query_embedding   VECTOR(1536),
    target_subject    TEXT,
    target_grade      SMALLINT,
    match_count       INT DEFAULT 20,
    workspace_filter  UUID DEFAULT NULL
)
RETURNS TABLE (
    chunk_id    UUID,
    chunk_text  TEXT,
    similarity  FLOAT,
    source_url  TEXT,
    difficulty  TEXT
)
LANGUAGE sql STABLE AS $$
    SELECT
        cc.chunk_id,
        cc.chunk_text,
        1 - (cc.embedding <=> query_embedding) AS similarity,
        cc.source_url,
        cc.difficulty
    FROM content_chunks cc
    WHERE
        cc.subject = target_subject
        AND cc.grade = target_grade
        AND (cc.workspace_id IS NULL OR cc.workspace_id = workspace_filter)
        AND 1 - (cc.embedding <=> query_embedding) > 0.55
    ORDER BY cc.embedding <=> query_embedding
    LIMIT match_count;
$$;

CREATE OR REPLACE FUNCTION semantic_cache_lookup(
    query_embedding      VECTOR(1536),
    target_subject       TEXT,
    target_grade         SMALLINT,
    similarity_threshold FLOAT DEFAULT 0.92
)
RETURNS TABLE (
    cache_id       UUID,
    response_text  TEXT,
    similarity     FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        sc.cache_id,
        sc.response_text,
        1 - (sc.embedding <=> query_embedding) AS similarity
    FROM semantic_cache sc
    WHERE
        sc.subject = target_subject
        AND sc.grade = target_grade
        AND sc.expires_at > NOW()
        AND 1 - (sc.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY sc.embedding <=> query_embedding
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION increment_cache_hit(p_cache_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE semantic_cache
    SET hit_count = hit_count + 1, last_hit_at = NOW()
    WHERE cache_id = p_cache_id;
$$;

CREATE OR REPLACE FUNCTION increment_chunk_alpha(p_chunk_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE content_chunks SET alpha_score = alpha_score + 1 WHERE chunk_id = p_chunk_id;
$$;

CREATE OR REPLACE FUNCTION increment_chunk_beta(p_chunk_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE content_chunks SET beta_score = beta_score + 1 WHERE chunk_id = p_chunk_id;
$$;

CREATE OR REPLACE FUNCTION increment_brain_coins(p_user_id UUID, p_coins INT)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE users SET brain_coins = brain_coins + p_coins WHERE user_id = p_user_id;
$$;

CREATE OR REPLACE FUNCTION increment_workspace_queries(p_workspace_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE workspaces SET queries_used = queries_used + 1 WHERE workspace_id = p_workspace_id;
$$;

CREATE OR REPLACE FUNCTION increment_session_exchanges(p_session_id UUID)
RETURNS VOID LANGUAGE sql AS $$
    UPDATE chat_sessions SET exchange_count = exchange_count + 1, last_message_at = NOW()
    WHERE session_id = p_session_id;
$$;

-- ════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ════════════════════════════════════════════════════════════════

ALTER TABLE users            ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages    ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE teachers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE content          ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_chunks   ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_cache   ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_self ON users
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY sessions_self ON chat_sessions
    USING (user_id = auth.uid());

CREATE POLICY messages_self ON chat_messages
    USING (user_id = auth.uid());

CREATE POLICY progress_self ON student_progress
    USING (user_id = auth.uid());

CREATE POLICY teachers_workspace ON teachers
    USING (workspace_id::text = current_setting('app.workspace_id', true));

CREATE POLICY content_read_published ON content FOR SELECT
    USING (status = 'published');

CREATE POLICY chunks_read ON content_chunks FOR SELECT
    USING (TRUE);

CREATE POLICY cache_read ON semantic_cache FOR SELECT
    USING (expires_at > NOW());

-- ════════════════════════════════════════════════════════════════
-- UPDATED_AT TRIGGER
-- ════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER content_updated_at
    BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
