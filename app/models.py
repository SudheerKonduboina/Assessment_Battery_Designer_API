# app/models.py
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic v2 output models for POST /chat.
#
# SCHEMA CONTRACT (non-negotiable):
#   Top-level keys:           reply, recommendations, end_of_conversation
#   Each recommendation key:  name, url, test_type  ← EXACTLY THESE THREE
#   Extra fields:             silently dropped via extra="ignore"
#   test_type allowed values: K, A, P, B, S
#
# Any deviation = immediate evaluator schema failure.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from pydantic import BaseModel, field_validator


class RecommendationItem(BaseModel):
    """
    Single assessment recommendation.
    Contains EXACTLY 3 fields.
    All extra fields (entity_id, duration, keys, etc.) are silently dropped.
    """
    name:      str
    url:       str
    test_type: str

    model_config = {
        "extra": "ignore",             # silently drop any extra catalogue fields
        "str_strip_whitespace": True,
    }

    @field_validator("test_type")
    @classmethod
    def coerce_test_type(cls, v: str) -> str:
        """
        Coerce to valid type code rather than crash.
        Crashing here would empty the recommendations list for the whole response.
        """
        allowed = {"K", "A", "P", "B", "S"}
        return v if v in allowed else "K"

    @field_validator("url")
    @classmethod
    def strip_url(cls, v: str) -> str:
        return v.strip()


class ChatResponse(BaseModel):
    """
    Top-level response envelope for POST /chat.
    Exactly 3 keys: reply, recommendations, end_of_conversation.
    """
    reply:               str
    recommendations:     list[RecommendationItem] = []
    end_of_conversation: bool = False

    model_config = {
        "extra": "ignore",
    }

    @field_validator("reply")
    @classmethod
    def reply_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            return "I'm ready to help you find the right SHL assessment."
        return v.strip()

    @field_validator("recommendations")
    @classmethod
    def cap_at_ten(cls, v: list) -> list:
        """Silently cap at 10 — never crash, never reject."""
        return v[:10]


def build_chat_response(raw: dict) -> dict:
    """
    Convert raw agent output into a schema-safe, evaluator-ready response dict.

    Call this function at the end of the POST /chat route handler,
    wrapping whatever dict the agent currently returns.

    Handles:
      - "link" → "url" field rename (catalogue uses "link", API must output "url")
      - Silent stripping of all extra fields (entity_id, duration, keys, etc.)
      - test_type coercion to K/A/P/B/S
      - recommendations silently capped at 10
      - reply guaranteed non-empty

    Args:
        raw: dict — the agent's current output, with keys:
               reply               (str)
               recommendations     (list of dicts — may have extra fields)
               end_of_conversation (bool)

    Returns:
        dict — safe to return directly from the FastAPI endpoint.
               Contains exactly: reply, recommendations, end_of_conversation.
    """
    raw_recs = raw.get("recommendations", [])

    safe_recs: list[RecommendationItem] = []
    for r in raw_recs:
        if not isinstance(r, dict):
            continue
        # Handle both "url" (if already mapped) and "link" (raw from catalogue)
        url = r.get("url") or r.get("link", "")
        name = r.get("name", "")
        if not name or not url:
            continue   # skip malformed entries — never crash
        item = RecommendationItem(
            name=name,
            url=url,
            test_type=r.get("test_type", "K"),
        )
        safe_recs.append(item)

    response = ChatResponse(
        reply=raw.get("reply", ""),
        recommendations=safe_recs,
        end_of_conversation=bool(raw.get("end_of_conversation", False)),
    )

    return response.model_dump()
