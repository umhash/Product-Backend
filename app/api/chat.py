from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student
from app.schemas.chat import (
    ChatRequest, 
    ChatResponse, 
    ChatHistoryResponse, 
    SessionMessagesResponse
)
from app.services.chat_service import ChatService
from app.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])

# Initialize chat service with error handling
try:
    chat_service = ChatService()
except ValueError as e:
    chat_service = None
    print(f"Warning: Chat service not initialized - {str(e)}")


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the AI assistant"""
    if chat_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please ensure OPENAI_API_KEY is configured in environment variables."
        )
    
    try:
        response = await chat_service.send_message(db, current_user.id, request)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for the current user"""
    if chat_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please ensure OPENAI_API_KEY is configured in environment variables."
        )
    return chat_service.get_chat_history(db, current_user.id)


@router.get("/session/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a specific chat session"""
    if chat_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please ensure OPENAI_API_KEY is configured in environment variables."
        )
    try:
        return chat_service.get_session_messages(db, session_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages"""
    if chat_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. Please ensure OPENAI_API_KEY is configured in environment variables."
        )
    success = chat_service.delete_session(db, session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return {"message": "Session deleted successfully"}


@router.get("/debug/auth")
async def debug_auth(current_user: Student = Depends(get_current_user)):
    """Debug endpoint to check authentication status"""
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "user_name": current_user.full_name
    }
