from pydantic import BaseModel, field_validator
from typing import List, Optional

class RecommendationItem(BaseModel):
    """
    Strict output model for a single assessment recommendation.
    Contains EXACTLY 3 fields. Any extra fields are silently dropped.
    """
    name: str
    url: str
    test_type: str

    model_config = {
        "extra": "ignore",          # silently drop any extra fields — never raise
        "str_strip_whitespace": True,
    }

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        allowed = {"K", "A", "P", "B", "S"}
        if v not in allowed:
            raise ValueError(f"test_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("https://www.shl.com/"):
            raise ValueError(f"url must start with https://www.shl.com/, got '{v}'")
        return v


class ChatResponse(BaseModel):
    """
    Top-level response envelope for POST /chat.
    Schema is non-negotiable — evaluator parses exactly these 3 keys.
    """
    reply: str
    recommendations: List[RecommendationItem] = []
    end_of_conversation: bool = False

    model_config = {
        "extra": "ignore",
    }

    @field_validator("reply")
    @classmethod
    def reply_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reply must be a non-empty string")
        return v.strip()

    @field_validator("recommendations")
    @classmethod
    def recs_max_10(cls, v: list) -> list:
        if len(v) > 10:
            return v[:10]       # silently cap — never crash
        return v
