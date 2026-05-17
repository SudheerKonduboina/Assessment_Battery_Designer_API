import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..core.agent import Agent
from app.models import build_chat_response, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Global Agent Instance
agent: Optional[Agent] = None

# ── Defensive Constants ──────────────────────────────────────────
VALID_ROLES = {"user", "assistant", "system"}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    # ── 0. Empty Message Guard (Critical) ────────────────────────
    if not request.messages:
        return build_chat_response({
            "reply": "Please describe the hiring role.",
            "recommendations": [],
            "end_of_conversation": False
        })

    # ── 1. Role Normalization (Defensive) ────────────────────────
    clean_messages: List[dict] = []
    for m in request.messages:
        role = m.role.strip().lower()
        if role not in VALID_ROLES:
            role = "user"  # safe fallback for unknown roles
        clean_messages.append({
            "role": role,
            "content": m.content or ""
        })

    # ── 2. Stateless Turn Tracking ───────────────────────────────
    user_messages = [m for m in clean_messages if m["role"] == "user"]
    turn_count = len(user_messages) - 1

    # ── 3. Recommender Detection (Stateless) ─────────────────────
    last_reply_was_recs = False
    if len(clean_messages) > 1:
        # Check previous assistant message in history
        last_bot_reply = [m for m in clean_messages[:-1] if m["role"] == "assistant"]
        if last_bot_reply:
             content = last_bot_reply[-1]["content"].lower()
             # Section 9/15 compliant recommendation patterns
             rec_patterns = ["identified", "shortlist", "top 4", "based on the jd", "top shl", "recommend"]
             last_reply_was_recs = any(p in content for p in rec_patterns)

    # ── 4. Execute Agent Pipeline (Crash-safe) ───────────────────
    try:
        reply, recs, end_conv = agent.handle_chat(
            clean_messages, turn_count, last_reply_was_recs
        )
    except Exception:
        logger.exception("handle_chat failed")
        return build_chat_response({
            "reply": "Unable to process request. Please refine the hiring requirement.",
            "recommendations": [],
            "end_of_conversation": False
        })

    # ── 5. Strict Schema Compliance (Section 5) ──────────────────
    result = {
        "reply": reply,
        "recommendations": recs or [],
        "end_of_conversation": end_conv
    }
    return build_chat_response(result)
