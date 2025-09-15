from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ChatMessageBase(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSession(ChatSessionBase):
    id: int
    student_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None  # If None, creates new session


class ChatResponse(BaseModel):
    message: str
    session_id: int
    session_title: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    sessions: List[ChatSession]


class SessionMessagesResponse(BaseModel):
    messages: List[ChatMessage]
