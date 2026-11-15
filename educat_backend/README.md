# EduCat AI — Advanced Backend

> FastAPI · Python 3.12 · Supabase + pgvector · LangChain RAG · Gemini 2.5 Flash · Celery · Redis

---

## Quick Start

### Option A: Docker (Recommended)

```bash
# 1. Clone & enter
git clone https://github.com/your-org/educat-backend
cd educat-backend

# 2. Setup environment
cp .env.example .env
# → Fill in all values in .env

# 3. Run database migrations
# Open Supabase SQL Editor → paste migrations/001_initial_schema.sql → Run

# 4. Start with Docker
docker-compose up -d
```

### Option B: Manual Install (Python 3.12 — Recommended)

```bash
# 1. Clone & enter
git clone https://github.com/your-org/educat-backend
cd educat-backend

# 2. Create virtual environment (Python 3.12 recommended)
python3.12 -m venv venv && source venv/bin/activate   # Linux/Mac
# OR on Windows:
python -m venv venv && venv\Scripts\activate
Remove-Item -Recurse -Force venv (if need to be )
# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# → Fill in all values in .env

# 5. Run database migrations
# Open Supabase SQL Editor → paste migrations/001_initial_schema.sql → Run

# 6. Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option C: Manual Install (Python 3.13+ / Without C Compiler)

If you're on Python 3.13+ or don't have MSVC Build Tools, use these commands instead of `pip install -r requirements.txt`:

```bash
# Step 1: Core packages (latest compatible versions)
pip install numpy pydantic pydantic-settings

# Step 2: Framework + Database + Cache + Queue
pip install fastapi uvicorn[standard] gunicorn python-multipart email-validator sqlalchemy redis celery flower httpx cryptography python-jose[cryptography] pyotp "qrcode[pil]" python-dateutil pytz passlib[bcrypt] aiofiles structlog slowapi sentry-sdk[fastapi] razorpay python-dotenv

# Step 3: Supabase (use --no-deps to skip pyiceberg which needs C compiler)
pip install "supabase==2.11.0" --no-deps
pip install gotrue supafunc postgrest-py realtime-py --no-deps
pip install "postgrest==0.16.11" --no-deps
pip install "storage3==0.7.7" --no-deps

# Step 4: AI / LLM packages
pip install langchain langchain-google-genai langchain-community google-generativeai openai tiktoken rank-bm25 nltk langdetect boto3

# Step 5: ML packages
pip install scikit-learn keybert

# Step 6: Content Processing + Audio + Firebase
pip install pdfplumber pypdf Pillow pytesseract google-cloud-vision youtube-transcript-api google-cloud-texttospeech google-cloud-speech firebase-admin

# Step 7: Missing sub-dependencies
pip install starlette limits billiard click-didyoumean click-plugins click-repl kombu vine tzlocal dnspython humanize prometheus-client tornado ecdsa rsa deprecation h2 hpack hyperframe "websockets==15.0.1" pyjwt[crypto] strenum cachecontrol google-cloud-core google-cloud-storage google-resumable-media google-crc32c msgpack google-cloud-firestore --no-deps

# Step 8: Setup environment
cp .env.example .env
# → Fill in all values in .env

# Step 9: Run database migrations
# Open Supabase SQL Editor → paste migrations/001_initial_schema.sql → Run

# Step 10: Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note:** On Python 3.13+, some packages (`asyncpg`, `xgboost`, `pyiceberg`) may not install without MSVC Build Tools. The server will still start but some features (direct PostgreSQL connections, storage analytics) won't work. For full compatibility, use Python 3.12.

**Docs:** http://localhost:8000/docs

---

## Project Structure

```
educat_backend/
├── app/
│   ├── main.py                     ← FastAPI app factory, middleware, lifespan
│   ├── core/
│   │   ├── config.py               ← All settings via pydantic-settings
│   │   ├── database.py             ← Supabase async client + helpers
│   │   ├── redis_client.py         ← Redis: quotas, cache, OTP, pub/sub
│   │   ├── security.py             ← JWT RS256, Fernet, OTP, HMAC
│   │   ├── firebase.py             ← Firebase Phone Auth + FCM
│   │   └── dependencies.py         ← FastAPI Depends: auth guards all 3 platforms
│   ├── routers/
│   │   ├── auth.py                 ← Phone OTP + Google OAuth2 + QR TOTP + Admin
│   │   ├── chat.py                 ← SSE streaming chat, sessions, quiz
│   │   ├── users.py                ← Profile, analytics, parent report
│   │   ├── content.py              ← CMS: upload, chunk, embed, publish
│   │   ├── subscriptions.py        ← Razorpay orders + activation
│   │   ├── _remaining.py           ← Admin, Teacher, Webhooks routers
│   │   └── __init__.py             ← Clean re-exports
│   ├── services/
│   │   └── ai/
│   │       ├── gemini_service.py   ← Streaming, embeddings, quiz gen, summaries
│   │       └── rag_pipeline.py     ← Hybrid BM25+pgvector, Thompson Sampling, BKT
│   ├── schemas/
│   │   └── schemas.py              ← All Pydantic request/response models
│   └── tasks/
│       ├── celery_app.py           ← Celery + Beat schedule
│       └── celery_tasks.py         ← All background tasks
├── migrations/
│   └── 001_initial_schema.sql      ← Full DB: 15 tables, HNSW indexes, RPC functions
├── tests/
│   └── test_backend.py             ← pytest test suite
├── .env.example                    ← All required env vars
├── Dockerfile                      ← Production multi-stage build
├── docker-compose.yml              ← Full local dev stack
└── railway.toml                    ← Railway.app deployment config
```

---

## Authentication Systems

| Platform | Method | Flow |
|---|---|---|
| **Students** | Firebase Phone OTP | Phone → SMS OTP → Firebase JWT → App JWT (RS256) |
| **Teachers/Schools** | Google OAuth2 + Email OTP + QR TOTP | Google → Email OTP → TOTP device binding |
| **Admins** | Email OTP + TOTP (SuperAdmin) | Email OTP → optional TOTP (mandatory SuperAdmin) |

---

## AI Pipeline

```
Student Question
       ↓
[L1 Redis Exact Cache] → HIT → Return cached
       ↓ MISS
[Generate Embedding] (Gemini text-embedding-004, 1536 dims)
       ↓
[L2 Semantic Cache] → HIT (similarity ≥ 0.92) → Return cached
       ↓ MISS
[Hybrid BM25 + pgvector HNSW] → Top-7 chunks (RRF fusion)
       ↓
[Thompson Sampling Reranking] → Reorder by learned utility
       ↓
[Context Builder] → Past summary + Weak topics + Future hint
       ↓
[Gemini 2.5 Flash] → SSE stream → Flutter subtitle box
       ↓
[Async] → Save to DB → Cache → Safety scan → Update BKT scores
```

---

## Key Math Algorithms

| Algorithm | Used For | Formula |
|---|---|---|
| **BM25 Okapi** | Keyword search | `IDF * (tf*(k1+1)) / (tf + k1*(1-b+b*|d|/avgdl))` |
| **Cosine Similarity** | Vector search | `(A·B) / (‖A‖·‖B‖)` |
| **HNSW** | ANN graph search | `O(log N)` instead of `O(N)` |
| **RRF** | Merge BM25+vector ranks | `α/(k+r_bm25) + (1-α)/(k+r_vec)` |
| **Thompson Sampling** | Adaptive chunk selection | `Beta(α, β)` distribution sampling |
| **BKT** | Student knowledge tracking | `P(Know\|Correct) = (1-slip)*P_know / P(Correct)` |

---

## API Endpoints Summary

| Module | Endpoints |
|---|---|
| `/auth` | `POST /phone/verify`, `/refresh`, `/logout`, `/teacher/google-callback`, `/teacher/verify-otp`, `/teacher/verify-totp`, `/teacher/qr-code`, `/admin/login` |
| `/chat` | `POST /session/create`, `/send` (SSE), `/quiz/generate`, `/quiz/submit`, `GET /sessions`, `/sessions/{id}/messages` |
| `/users` | `GET /me`, `PATCH /me`, `GET /me/analytics`, `GET /me/parent-report`, `DELETE /me` |
| `/content` | `GET`, `POST`, `/upload` (multipart), `/batch/{id}/status`, `POST /{id}/publish`, `PATCH /{id}`, `DELETE /{id}` |
| `/subscriptions` | `GET /plans`, `GET /me`, `POST /create-order`, `POST /activate` |
| `/teacher` | `POST /lesson/start`, `/lesson/{id}/question`, `GET /lesson/{id}/stream` (SSE), `GET /analytics` |
| `/admin` | `GET /dashboard`, `/users`, `/workspaces`, `/content`, `/safety/queue`, `/admins/invite`, `GET /audit` |
| `/webhooks` | `POST /razorpay` |

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v --asyncio-mode=auto
```

---

## Production Deployment (Railway.app)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli && railway login

# 2. Initialize project
railway init

# 3. Set environment variables
railway variables set SUPABASE_URL=...
railway variables set GEMINI_API_KEY=...
# ... all vars from .env.example

# 4. Deploy
railway up
```

---

## Celery Tasks Schedule

| Task | Schedule | Action |
|---|---|---|
| `monthly_token_reset` | 1st of month, 00:01 IST | Reset all user token quotas |
| `daily_streak_update` | Daily, 00:05 IST | Update/reset user streaks |
| `weekly_parent_report` | Saturday 8:00 IST | Push FCM notification to SMART/GENIUS users |
| `data_purge` | Daily, 03:00 IST | Hard-delete accounts soft-deleted 30+ days ago |
| `workspace_quota_reset` | 1st of month, 01:00 IST | Reset school query quotas |
| `rebuild_bm25_indexes` | Daily, 04:00 IST | Rebuild in-memory BM25 search indexes |

---

## Environment: Required Keys

```
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
GEMINI_API_KEY          ← never expose to frontend
JWT_PRIVATE_KEY         ← RSA-4096, RS256 signing
JWT_PUBLIC_KEY          ← RSA-4096, RS256 verification
FERNET_KEY              ← AES-256 for TOTP secrets
FIREBASE_SERVICE_ACCOUNT_JSON  ← base64 encoded
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET  ← OAuth2
RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
REDIS_URL
CELERY_BROKER_URL, CELERY_RESULT_BACKEND
```
