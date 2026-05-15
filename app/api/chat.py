from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from ..core.agent import Agent
from ..models import ChatResponse, RecommendationItem

router = APIRouter()

# Global Agent Instance
agent: Optional[Agent] = None

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

    # 1. Stateless Turn Tracking
    msg_dicts = [m.dict() for m in request.messages]
    user_messages = [m for m in msg_dicts if m["role"] == "user"]
    turn_count = len(user_messages) - 1
    
    # 2. Recommender Detection (Stateless)
    last_reply_was_recs = False
    if len(msg_dicts) > 1:
        # Check previous assistant message in history
        last_bot_reply = [m for m in msg_dicts[:-1] if m["role"] == "assistant"]
        if last_bot_reply:
             content = last_bot_reply[-1]["content"].lower()
             # Section 9/15 compliant recommendation patterns
             rec_patterns = ["identified", "shortlist", "top 4", "based on the jd", "top shl", "recommend"]
             last_reply_was_recs = any(p in content for p in rec_patterns)

    # 3. Execute Agent Pipeline
    reply, recs, end_conv = agent.handle_chat(msg_dicts, turn_count, last_reply_was_recs)

    # 4. Strict Schema Compliance (Section 5)
    safe_recs = [
        RecommendationItem(
            name=r["name"],
            url=r.get("url") or r.get("link", ""),
            test_type=r.get("test_type", "K")
        )
        for r in (recs or [])
    ]

    response = ChatResponse(
        reply=reply,
        recommendations=safe_recs,
        end_of_conversation=end_conv
    )

    return response.model_dump()
