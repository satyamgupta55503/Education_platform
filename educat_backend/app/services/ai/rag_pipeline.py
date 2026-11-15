"""
EduCat AI — RAG Pipeline
Hybrid BM25 + Cosine Similarity (pgvector) with Thompson Sampling
for adaptive chunk selection and 3-layer semantic caching.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.database import Tables, db_fetch_many, db_insert, db_update, get_supabase
from app.core.redis_client import cache_get, cache_set
from app.services.ai.gemini_service import generate_embedding
import structlog

log = structlog.get_logger()


# ══════════════════════════════════════════════════════════════════
# HYBRID SEARCH ENGINE
# ══════════════════════════════════════════════════════════════════

class HybridSearchEngine:
    """
    Combines BM25 keyword search + pgvector cosine similarity.
    Uses Reciprocal Rank Fusion (RRF) to merge rankings.
    Alpha is dynamically set based on query type.
    """

    def __init__(self):
        self._bm25_cache: dict[str, BM25Okapi] = {}  # subject_grade -> BM25Okapi

    # ── Query Type Classifier ─────────────────────────────────────
    @staticmethod
    def classify_query(question: str) -> tuple[str, float]:
        """
        Classify query type and return (type, bm25_alpha).
        Higher alpha = more weight to BM25 (keyword match).
        """
        q_lower = question.lower()

        # Math/formula queries → favour BM25 (exact formula match)
        math_indicators = ["formula", "calculate", "solve", "equation",
                           "theorem", "proof", "value of", "find the"]
        if any(ind in q_lower for ind in math_indicators):
            return ("formula", 0.65)

        # Definition queries → balanced
        def_indicators = ["what is", "define", "meaning of", "kya hai",
                         "matlab", "paribhasha"]
        if any(ind in q_lower for ind in def_indicators):
            return ("definition", 0.50)

        # Chapter/topic specific → favour BM25
        chapter_indicators = ["chapter", "adhyay", "ncert", "lesson", "page"]
        if any(ind in q_lower for ind in chapter_indicators):
            return ("chapter", 0.70)

        # Conceptual/explanation queries → favour vector
        return ("conceptual", 0.35)

    # ── BM25 Search ───────────────────────────────────────────────
    async def bm25_search(
        self,
        query: str,
        subject: str,
        grade: int,
        top_k: int = 20,
    ) -> list[tuple[str, float]]:
        """
        BM25 Okapi search over content_chunks for subject+grade.
        Returns: [(chunk_id, score)] sorted descending.
        k1=1.5, b=0.75 (tuned for short educational Q&A).
        """
        cache_key = f"{subject}_{grade}"

        # Build BM25 index if not cached
        if cache_key not in self._bm25_cache:
            await self._build_bm25_index(subject, grade)

        bm25 = self._bm25_cache.get(cache_key)
        if not bm25 or not bm25.corpus_size:
            return []

        # Tokenize query (simple whitespace + lowercase)
        tokens = query.lower().split()
        scores = bm25.get_scores(tokens)

        # Pair with chunk IDs
        chunks_meta = self._bm25_chunk_ids.get(cache_key, [])
        ranked = sorted(
            zip(chunks_meta, scores.tolist()),
            key=lambda x: x[1], reverse=True
        )
        return [(cid, score) for cid, score in ranked[:top_k] if score > 0]

    async def _build_bm25_index(self, subject: str, grade: int):
        """Load all published chunks for subject+grade and build BM25 index."""
        cache_key = f"{subject}_{grade}"
        db = await get_supabase()
        result = await db.table(Tables.CONTENT_CHUNKS).select(
            "chunk_id, chunk_text"
        ).eq("subject", subject).eq("grade", grade).execute()

        chunks = result.data or []
        if not chunks:
            self._bm25_cache[cache_key] = BM25Okapi([[]])
            self._bm25_chunk_ids[cache_key] = []
            return

        tokenized = [chunk["chunk_text"].lower().split() for chunk in chunks]
        self._bm25_cache[cache_key] = BM25Okapi(
            tokenized, k1=1.5, b=0.75, epsilon=0.25
        )
        self._bm25_chunk_ids[cache_key] = [c["chunk_id"] for c in chunks]
        log.info("bm25_index_built", subject=subject, grade=grade,
                 chunks=len(chunks))

    _bm25_chunk_ids: dict[str, list[str]] = {}

    # ── Vector Search (pgvector) ──────────────────────────────────
    async def vector_search(
        self,
        query_embedding: list[float],
        subject: str,
        grade: int,
        top_k: int = 20,
        workspace_id: Optional[str] = None,
    ) -> list[tuple[str, float]]:
        """
        pgvector cosine similarity search on content_chunks.
        Pre-filters by subject + grade for speed.
        Uses HNSW index (O(log N) lookup).
        """
        db = await get_supabase()

        # Convert embedding to pgvector format string
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Use RPC for raw vector search (pgvector operator)
        result = await db.rpc("hybrid_vector_search", {
            "query_embedding": embedding_str,
            "target_subject": subject,
            "target_grade": grade,
            "match_count": top_k,
            "workspace_filter": workspace_id,
        }).execute()

        if not result.data:
            return []

        return [
            (row["chunk_id"], float(row["similarity"]))
            for row in result.data
        ]

    # ── Thompson Sampling: Sample chunk utility ───────────────────
    @staticmethod
    def thompson_sample(alpha: float, beta: float) -> float:
        """
        Sample from Beta(alpha, beta) distribution.
        Higher alpha/beta ratio → higher expected utility.
        """
        return float(np.random.beta(alpha, beta))

    # ── RRF Fusion ────────────────────────────────────────────────
    @staticmethod
    def reciprocal_rank_fusion(
        bm25_ranked: list[tuple[str, float]],
        vector_ranked: list[tuple[str, float]],
        alpha: float,
        k: int = 60,
    ) -> list[tuple[str, float]]:
        """
        Reciprocal Rank Fusion (RRF) combining BM25 + vector ranks.
        score(d) = alpha*(1/(k+rank_bm25)) + (1-alpha)*(1/(k+rank_vector))
        """
        bm25_rank  = {cid: i+1 for i, (cid, _) in enumerate(bm25_ranked)}
        vector_rank = {cid: i+1 for i, (cid, _) in enumerate(vector_ranked)}
        all_ids = set(bm25_rank) | set(vector_rank)

        scores = {}
        for cid in all_ids:
            bm25_score  = alpha * (1 / (k + bm25_rank.get(cid, len(bm25_ranked) + k)))
            vector_score = (1 - alpha) * (1 / (k + vector_rank.get(cid, len(vector_ranked) + k)))
            scores[cid] = bm25_score + vector_score

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # ── Full Hybrid Search ────────────────────────────────────────
    async def search(
        self,
        question: str,
        subject: str,
        grade: int,
        top_k: int = None,
        workspace_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Full hybrid search pipeline:
        1. Classify query → get alpha
        2. BM25 search
        3. Vector search
        4. RRF fusion
        5. Thompson Sampling reranking
        6. Return top_k chunks with text
        """
        top_k = top_k or settings.RAG_TOP_K

        # Step 1: Query type + alpha
        query_type, alpha = self.classify_query(question)
        log.debug("query_classified", type=query_type, alpha=alpha)

        # Step 2: Generate embedding
        query_embedding = await generate_embedding(question)

        # Step 3: BM25 + vector search in parallel
        import asyncio
        bm25_results, vector_results = await asyncio.gather(
            self.bm25_search(question, subject, grade, top_k=20),
            self.vector_search(query_embedding, subject, grade, top_k=20,
                              workspace_id=workspace_id),
        )

        # Step 4: RRF fusion
        fused = self.reciprocal_rank_fusion(bm25_results, vector_results, alpha)

        if not fused:
            log.warning("no_chunks_found", subject=subject, grade=grade)
            return []

        # Step 5: Fetch top candidate chunks with Thompson Sampling scores
        candidate_ids = [cid for cid, _ in fused[:top_k * 2]]
        db = await get_supabase()
        chunks_result = await db.table(Tables.CONTENT_CHUNKS).select(
            "chunk_id, chunk_text, alpha_score, beta_score, source_url, difficulty"
        ).in_("chunk_id", candidate_ids).execute()

        chunks_map = {c["chunk_id"]: c for c in (chunks_result.data or [])}

        # Step 6: Thompson Sampling reranking
        scored = []
        for cid, rrf_score in fused[:top_k * 2]:
            chunk = chunks_map.get(cid)
            if not chunk:
                continue
            ts_score = self.thompson_sample(
                chunk.get("alpha_score", 1.0),
                chunk.get("beta_score", 1.0)
            )
            # Combined score: 70% RRF + 30% Thompson Sampling
            final_score = 0.7 * rrf_score + 0.3 * ts_score
            scored.append((chunk, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in scored[:top_k]]


# Singleton instance
_search_engine: Optional[HybridSearchEngine] = None


def get_search_engine() -> HybridSearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = HybridSearchEngine()
    return _search_engine


# ══════════════════════════════════════════════════════════════════
# SEMANTIC CACHE
# ══════════════════════════════════════════════════════════════════

async def semantic_cache_lookup(
    question: str,
    query_embedding: list[float],
    subject: str,
    grade: int,
) -> Optional[str]:
    """
    L2 Semantic cache: cosine similarity check on semantic_cache table.
    Returns cached response text or None.
    """
    if not settings.SEMANTIC_CACHE_ENABLED:
        return None

    threshold = settings.semantic_cache_thresholds.get(subject, 0.92)

    db = await get_supabase()
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    result = await db.rpc("semantic_cache_lookup", {
        "query_embedding": embedding_str,
        "target_subject": subject,
        "target_grade": grade,
        "similarity_threshold": threshold,
    }).execute()

    if result.data:
        hit = result.data[0]
        cache_id = hit["cache_id"]

        # Update hit count async (fire and forget)
        import asyncio
        asyncio.create_task(_increment_cache_hit(cache_id))

        log.info("semantic_cache_hit",
                 similarity=round(hit["similarity"], 4),
                 subject=subject, grade=grade)
        return hit["response_text"]

    return None


async def semantic_cache_store(
    question: str,
    response: str,
    query_embedding: list[float],
    subject: str,
    grade: int,
):
    """Store Q&A pair in semantic cache."""
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.SEMANTIC_CACHE_TTL_DAYS
    )

    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    db = await get_supabase()
    await db.table(Tables.SEMANTIC_CACHE).insert({
        "question_text": question[:1000],
        "response_text": response,
        "embedding": embedding_str,
        "subject": subject,
        "grade": grade,
        "expires_at": expires_at.isoformat(),
    }).execute()


async def _increment_cache_hit(cache_id: str):
    """Async fire-and-forget cache hit counter update."""
    try:
        db = await get_supabase()
        await db.rpc("increment_cache_hit", {"p_cache_id": cache_id}).execute()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# STUDENT CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════

async def build_student_context(
    user_id: str,
    subject: str,
    grade: int,
) -> dict:
    """
    Build PRESENT + PAST + FUTURE context for LLM prompt injection.
    Fetches: recent session summary, weak topics, upcoming chapter.
    """
    db = await get_supabase()

    # PAST: Most recent session summary for this subject
    summaries = await db.table(Tables.SESSION_SUMMARIES).select(
        "summary_text"
    ).eq("user_id", user_id).eq("subject", subject).order(
        "created_at", desc=True
    ).limit(1).execute()

    past_summary = summaries.data[0]["summary_text"] if summaries.data else None

    # PAST: Weak topics from student_progress
    progress = await db.table(Tables.STUDENT_PROGRESS).select(
        "topic, knowledge_probability"
    ).eq("user_id", user_id).eq("subject", subject).eq(
        "grade", grade
    ).lt("knowledge_probability", 0.4).limit(3).execute()

    weak_topics = [p["topic"] for p in (progress.data or [])]
    weakness_note = None
    if weak_topics:
        weakness_note = f"Student struggles with: {', '.join(weak_topics)}. Don't assume prior knowledge of these."

    # FUTURE: Next chapter hint (based on chapter sequence)
    # Simplified: just return None for now, can be enhanced with exam calendar
    future_hint = None

    return {
        "past_summary": past_summary,
        "weakness_note": weakness_note,
        "future_hint": future_hint,
        "weak_topics": weak_topics,
    }


# ══════════════════════════════════════════════════════════════════
# THOMPSON SAMPLING UPDATE
# ══════════════════════════════════════════════════════════════════

async def update_chunk_utility(
    chunk_ids: list[str],
    feedback: str,  # "positive" | "negative" | "neutral"
):
    """
    Update Thompson Sampling scores for chunks used in a response.
    Called async 30s after response delivery.
    """
    if feedback == "neutral":
        return

    db = await get_supabase()
    for chunk_id in chunk_ids:
        if feedback == "positive":
            await db.rpc("increment_chunk_alpha", {"p_chunk_id": chunk_id}).execute()
        elif feedback == "negative":
            await db.rpc("increment_chunk_beta", {"p_chunk_id": chunk_id}).execute()


# ══════════════════════════════════════════════════════════════════
# DIFFICULTY CLASSIFIER
# ══════════════════════════════════════════════════════════════════

class DifficultyClassifier:
    """
    XGBoost-based difficulty classifier.
    Falls back to heuristic if model not available.
    """

    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        try:
            import pickle, os
            model_path = os.path.join(os.path.dirname(__file__), "difficulty_model.pkl")
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    self._model = pickle.load(f)
        except Exception:
            pass  # Fallback to heuristic

    def classify(self, question: str, grade: int, subject: str) -> str:
        """Returns: 'easy' | 'medium' | 'hard'"""
        if self._model:
            return self._classify_ml(question, grade, subject)
        return self._classify_heuristic(question, grade)

    def _classify_heuristic(self, question: str, grade: int) -> str:
        """Heuristic fallback when ML model unavailable."""
        q = question.lower()
        words = q.split()

        # Hard indicators
        hard = ["why", "explain", "how does", "derive", "prove", "compare",
                "analyse", "difference between", "kyun", "samjhao"]
        if any(h in q for h in hard) or len(words) > 15:
            return "hard"

        # Easy indicators
        easy = ["what is", "define", "name", "list", "kya hai", "batao",
                "how many", "kitne"]
        if any(e in q for e in easy) or len(words) < 6:
            return "easy"

        return "medium"

    def _classify_ml(self, question: str, grade: int, subject: str) -> str:
        try:
            import numpy as np
            features = self._extract_features(question, grade, subject)
            pred = self._model.predict([features])[0]
            return ["easy", "medium", "hard"][int(pred)]
        except Exception:
            return self._classify_heuristic(question, grade)

    @staticmethod
    def _extract_features(question: str, grade: int, subject: str) -> list:
        words = question.lower().split()
        has_calc = int(any(w in question.lower() for w in ["calculate", "find", "solve"]))
        has_why  = int("why" in question.lower() or "kyun" in question.lower())
        multi    = int(any(w in question.lower() for w in [" and ", " also ", " then "]))
        return [len(words) / 20, grade / 10, has_calc, has_why, multi]


_difficulty_classifier: Optional[DifficultyClassifier] = None


def get_difficulty_classifier() -> DifficultyClassifier:
    global _difficulty_classifier
    if _difficulty_classifier is None:
        _difficulty_classifier = DifficultyClassifier()
    return _difficulty_classifier
