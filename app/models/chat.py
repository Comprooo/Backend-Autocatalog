from beanie import Document, PydanticObjectId
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Dict

class ChatHistory(Document):
    session_id: str
    user_id: PydanticObjectId
    messages: List[Dict[str, str]] = [] # [{"role": "user/assistant", "content": "..."}]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "chat_histories"
        indexes = ["session_id", "user_id"]
