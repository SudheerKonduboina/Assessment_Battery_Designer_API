from typing import Dict, List, Any

# Key: conversation_id (str)
# Value: Dict containing 'history' and 'pagination_offset'
sessions: Dict[str, Dict[str, Any]] = {}

def save_session(conversation_id: str, history: List[Dict[str, str]], offset: int = 0):
    """Saves/Updates the conversation session."""
    sessions[conversation_id] = {
        "history": history,
        "pagination_offset": offset
    }

def load_session(conversation_id: str) -> Dict[str, Any]:
    """Loads the conversation session. Returns default if not found."""
    return sessions.get(conversation_id, {
        "history": [],
        "pagination_offset": 0
    })

def clear_session(conversation_id: str):
    """Removes a session from memory."""
    if conversation_id in sessions:
        del sessions[conversation_id]
