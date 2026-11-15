"""
EduCat AI — Gemini AI Service
Handles: streaming chat, embeddings, quiz generation, session summaries.
"""
import asyncio
import json
import re
from typing import AsyncGenerator, Optional
from uuid import uuid4

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from app.core.config import settings
import structlog

log = structlog.get_logger()

# ── Safety Settings ───────────────────────────────────────────────
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}

# ── Init ──────────────────────────────────────────────────────────
genai.configure(api_key=settings.GEMINI_API_KEY)


def _get_model(tier: str) -> genai.GenerativeModel:
    model_name = (
        settings.GEMINI_MODEL_PAID
        if tier in ("smart", "genius", "teacher")
        else settings.GEMINI_MODEL_FREE
    )
    return genai.GenerativeModel(
        model_name=model_name,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
            temperature=0.7,
            top_p=0.9,
            top_k=40,
        ),
    )


# ── System Prompt Builder ─────────────────────────────────────────
def build_system_prompt(
    grade: int,
    subject: str,
    language: str,
    difficulty: str,
    past_summary: Optional[str],
    future_hint: Optional[str],
    weakness_note: Optional[str],
) -> str:
    lang_instruction = (
        "Respond ONLY in Hindi (Devanagari script). Use simple, clear Hindi suitable for school students."
        if language == "hi"
        else "Respond ONLY in English. Use simple, clear English suitable for school students."
    )

    verbosity = {
        "easy": "Give a concise 2-3 sentence answer. Use simple vocabulary.",
        "medium": "Give a 4-6 sentence answer with one example.",
        "hard": "Give a full explanation with step-by-step breakdown, analogy, and worked example.",
    }.get(difficulty, "Give a clear, helpful explanation.")

    past_context = f"\n\nPREVIOUS SESSION SUMMARY: {past_summary}" if past_summary else ""
    future_context = f"\n\nUPCOMING TOPICS (for context): {future_hint}" if future_hint else ""
    weakness_context = f"\n\nNOTE: {weakness_note}" if weakness_note else ""

    return f"""You are Billi, an intelligent and friendly AI tutor for Class {grade} students in India.
Your subject today is: {subject.upper()}

STRICT RULES (never break these):
1. ONLY discuss {subject} topics relevant to Class {grade} NCERT curriculum.
2. REFUSE any question not related to school subjects. Say: "Main sirf padhai ke sawaal jaanta hoon! 🐱"
3. NEVER discuss: politics, religion, adult content, violence, or anything inappropriate for children.
4. Always be encouraging, patient, and supportive.
5. If a student seems confused, simplify further. Never make them feel bad.

LANGUAGE: {lang_instruction}
RESPONSE LENGTH: {verbosity}
{past_context}{future_context}{weakness_context}

Always end with: one follow-up question OR a quick quiz question to check understanding.
Use emojis occasionally to make learning fun! 🌟"""


# ── Streaming Chat ────────────────────────────────────────────────
async def stream_chat_response(
    question: str,
    context_chunks: list[str],
    conversation_history: list[dict],
    grade: int,
    subject: str,
    language: str,
    tier: str,
    difficulty: str = "medium",
    past_summary: Optional[str] = None,
    future_hint: Optional[str] = None,
    weakness_note: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream Gemini response as SSE events.
    Yields: JSON strings for each SSE event type.
    """
    model = _get_model(tier)

    system_prompt = build_system_prompt(
        grade, subject, language, difficulty,
        past_summary, future_hint, weakness_note
    )

    # Build context string from RAG chunks
    context_str = "\n\n---\n\n".join(
        [f"[Reference {i+1}]\n{chunk}" for i, chunk in enumerate(context_chunks)]
    ) if context_chunks else "No specific reference material found."

    # Build conversation messages for Gemini
    messages = []

    # Add history (last 15 messages)
    for msg in conversation_history[-15:]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [msg["content"]]})

    # Current question with context
    user_message = f"""REFERENCE MATERIAL (from NCERT curriculum):
{context_str}

STUDENT'S QUESTION: {question}"""

    messages.append({"role": "user", "parts": [user_message]})

    # Create chat with system instruction
    chat = model.start_chat(history=messages[:-1])

    try:
        # Signal: Billi is thinking
        yield f"data: {json.dumps({'type': 'billi_state', 'state': 'thinking'})}\n\n"

        # Stream response
        response = await asyncio.to_thread(
            lambda: chat.send_message(
                messages[-1]["parts"][0],
                stream=True,
                generation_config=genai.GenerationConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                ),
            )
        )

        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"
                await asyncio.sleep(0)  # Yield control to event loop

        # Signal: complete
        yield f"data: {json.dumps({'type': 'complete', 'billi_state': 'happy', 'full_text': full_text})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        log.error("gemini_stream_failed", error=str(e), grade=grade, subject=subject)
        error_msg = (
            "Billi abhi thodi busy hai. Ek minute mein wapas try karein! 🐱"
            if language == "hi"
            else "Billi is a bit busy right now. Please try again in a moment! 🐱"
        )
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        yield "data: [DONE]\n\n"


# ── Embeddings ────────────────────────────────────────────────────
async def generate_embedding(text: str) -> list[float]:
    """Generate 1536-dim embedding for text."""
    try:
        result = await asyncio.to_thread(
            genai.embed_content,
            model=settings.GEMINI_EMBED_MODEL,
            content=text,
            task_type="retrieval_query",
            output_dimensionality=settings.GEMINI_EMBED_DIMENSIONS,
        )
        return result["embedding"]
    except Exception as e:
        log.error("embedding_failed", error=str(e), text_preview=text[:50])
        raise


async def generate_document_embedding(text: str) -> list[float]:
    """Generate embedding for document storage (different task type)."""
    result = await asyncio.to_thread(
        genai.embed_content,
        model=settings.GEMINI_EMBED_MODEL,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=settings.GEMINI_EMBED_DIMENSIONS,
    )
    return result["embedding"]


# ── Quiz Generation ───────────────────────────────────────────────
async def generate_quiz(
    topic: str,
    subject: str,
    grade: int,
    language: str,
    difficulty: str = "mixed",
    count: int = 5,
) -> list[dict]:
    """
    Generate MCQ quiz using Gemini.
    Returns: list of question dicts.
    """
    model = _get_model("smart")  # Always use Flash for quiz generation

    lang_instruction = (
        "Generate ALL content in Hindi (Devanagari script)."
        if language == "hi"
        else "Generate ALL content in English."
    )

    difficulty_instruction = {
        "easy":   f"All questions should be EASY (Class {grade-1} level concepts).",
        "medium": f"All questions should be MEDIUM (standard Class {grade} level).",
        "hard":   f"All questions should be HARD (challenge questions for Class {grade}).",
        "mixed":  f"Mix of 2 easy, 2 medium, 1 hard questions.",
    }.get(difficulty, "Mix of difficulties.")

    prompt = f"""Generate exactly {count} multiple-choice questions about "{topic}" for Class {grade} {subject.upper()}.

{lang_instruction}
{difficulty_instruction}

Return ONLY a valid JSON array. No other text. Format:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 1,
    "explanation": "Brief explanation of why option B is correct.",
    "difficulty": "easy|medium|hard",
    "ncert_reference": "Class {grade} {subject} Chapter X, Page Y (or null)"
  }}
]

Rules:
- Each question must have EXACTLY 4 options
- correct_index is 0-based (0=A, 1=B, 2=C, 3=D)
- Explanations should be educational and clear
- Questions must be from NCERT Class {grade} {subject} curriculum
- No trick questions — test understanding, not memory tricks"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        raw = response.text.strip()

        # Clean JSON from markdown code blocks if present
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip("` \n")

        questions = json.loads(raw)
        # Validate and add IDs
        validated = []
        for q in questions[:count]:
            if (
                isinstance(q.get("options"), list)
                and len(q["options"]) == 4
                and isinstance(q.get("correct_index"), int)
                and 0 <= q["correct_index"] <= 3
            ):
                q["q_id"] = str(uuid4())
                validated.append(q)

        if not validated:
            raise ValueError("No valid questions generated")

        return validated

    except (json.JSONDecodeError, ValueError) as e:
        log.error("quiz_generation_failed", error=str(e), topic=topic, grade=grade)
        return _fallback_questions(topic, language, grade)


def _fallback_questions(topic: str, language: str, grade: int) -> list[dict]:
    """Return generic fallback questions if Gemini fails."""
    if language == "hi":
        return [{
            "q_id": str(uuid4()),
            "question": f"{topic} के बारे में सही कथन क्या है?",
            "options": ["विकल्प A", "विकल्प B", "विकल्प C", "विकल्प D"],
            "correct_index": 0,
            "explanation": "कृपया पाठ्यपुस्तक देखें।",
            "difficulty": "medium",
            "ncert_reference": None,
        }]
    return [{
        "q_id": str(uuid4()),
        "question": f"Which statement about {topic} is correct?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_index": 0,
        "explanation": "Please refer to your textbook.",
        "difficulty": "medium",
        "ncert_reference": None,
    }]


# ── Session Summary ───────────────────────────────────────────────
async def generate_session_summary(
    messages: list[dict],
    subject: str,
    grade: int,
    language: str,
) -> str:
    """Generate 100-token summary of a session for past context injection."""
    model = _get_model("smart")

    transcript = "\n".join([
        f"{'Student' if m['role']=='user' else 'Billi'}: {m['content']}"
        for m in messages[-20:]  # Last 20 messages max
    ])

    lang_instruction = "Respond in Hindi." if language == "hi" else "Respond in English."

    prompt = f"""Summarise this Class {grade} {subject} tutoring session in 2-3 sentences.
{lang_instruction}
Focus on: what was taught, key concepts covered, any gaps or confusion observed.
Keep it under 100 words.

SESSION TRANSCRIPT:
{transcript}"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()[:500]  # Cap at 500 chars
    except Exception:
        return f"Discussed {subject} topics for Class {grade}."


# ── Video Curation ────────────────────────────────────────────────
async def curate_video_for_topic(
    topic: str,
    subject: str,
    grade: int,
    language: str,
) -> Optional[str]:
    """
    Use Gemini to suggest best YouTube search query for a topic.
    Frontend then uses YouTube Data API to find the actual video.
    """
    model = _get_model("free")
    lang = "Hindi" if language == "hi" else "English"

    prompt = f"""Suggest the best YouTube search query to find an educational video about "{topic}" 
for Class {grade} {subject} students in India. The video should be in {lang}.
Reply with ONLY the search query, nothing else. Maximum 10 words."""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()
    except Exception:
        return f"{topic} class {grade} {subject} {language}"
