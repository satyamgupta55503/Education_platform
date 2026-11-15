"""
EduCat AI — Test Suite
Run: pytest tests/ -v --asyncio-mode=auto
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c


# ── Health Check ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "EduCat" in r.json()["name"]


# ── Auth ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_phone_verify_invalid_token(client):
    r = await client.post("/api/v1/auth/phone/verify", json={
        "firebase_token": "invalid_token_xyz"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_wrong_otp(client):
    # First send OTP
    await client.post("/api/v1/auth/admin/send-otp", params={"email": "test@test.com"})
    # Then submit wrong OTP
    r = await client.post("/api/v1/auth/admin/login", json={
        "email": "test@test.com",
        "otp": "000000"
    })
    assert r.status_code in (400, 404)


# ── Plans ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_plans(client):
    r = await client.get("/api/v1/subscriptions/plans")
    assert r.status_code == 200
    plans = r.json()["data"]["plans"]
    assert len(plans) == 4
    plan_ids = [p["plan_id"] for p in plans]
    assert "smart_monthly" in plan_ids
    assert "genius_monthly" in plan_ids


# ── Difficulty Classifier ─────────────────────────────────────────
def test_difficulty_classifier_easy():
    from app.services.ai.rag_pipeline import get_difficulty_classifier
    clf = get_difficulty_classifier()
    assert clf.classify("What is photosynthesis?", 7, "science") == "easy"


def test_difficulty_classifier_hard():
    from app.services.ai.rag_pipeline import get_difficulty_classifier
    clf = get_difficulty_classifier()
    assert clf.classify("Why does the rate of photosynthesis decrease at very high temperatures and how does this relate to enzyme denaturation?", 7, "science") == "hard"


# ── Hybrid Search Query Type ──────────────────────────────────────
def test_query_type_formula():
    from app.services.ai.rag_pipeline import HybridSearchEngine
    qtype, alpha = HybridSearchEngine.classify_query("calculate the value of x in the equation")
    assert qtype == "formula"
    assert alpha > 0.5  # BM25-favoured


def test_query_type_conceptual():
    from app.services.ai.rag_pipeline import HybridSearchEngine
    qtype, alpha = HybridSearchEngine.classify_query("explain why plants need sunlight")
    assert qtype == "conceptual"
    assert alpha < 0.5  # Vector-favoured


# ── OTP Generation ────────────────────────────────────────────────
def test_otp_generation():
    from app.core.security import generate_otp
    otp = generate_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()


# ── Hash functions ────────────────────────────────────────────────
def test_phone_hash_consistency():
    from app.core.security import hash_phone
    h1 = hash_phone("+919876543210")
    h2 = hash_phone("+919876543210")
    h3 = hash_phone("+919999999999")
    assert h1 == h2
    assert h1 != h3


# ── Encryption ────────────────────────────────────────────────────
def test_fernet_encrypt_decrypt():
    import os
    os.environ.setdefault("FERNET_KEY",
        "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    os.environ["FERNET_KEY"] = key.decode()
    from app.core.security import encrypt_secret, decrypt_secret
    secret   = "JBSWY3DPEBLW64TMMQQQ"
    encrypted = encrypt_secret(secret)
    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret


# ── RRF Fusion ────────────────────────────────────────────────────
def test_rrf_fusion():
    from app.services.ai.rag_pipeline import HybridSearchEngine
    bm25   = [("a", 2.1), ("b", 1.8), ("c", 1.2)]
    vector = [("b", 0.95), ("a", 0.91), ("d", 0.88)]
    fused  = HybridSearchEngine.reciprocal_rank_fusion(bm25, vector, alpha=0.4)
    assert len(fused) >= 3
    # "b" appears in both lists — should rank highly
    top_ids = [cid for cid, _ in fused[:2]]
    assert "b" in top_ids or "a" in top_ids
