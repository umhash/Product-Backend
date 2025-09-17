import os
from typing import List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse, SessionMessagesResponse
from app.schemas.rag import RAGQueryRequest
from datetime import datetime


class ChatService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-openai-api-key-here":
            raise ValueError("OPENAI_API_KEY environment variable is required but not set to a valid API key. Please add your actual OpenAI API key to your .env file.")
        
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}. Please check your OPENAI_API_KEY in the .env file.")
        self.system_prompt = """
You are an Expert UK University Study Consultant and Student Advisor. 
Your role is to guide students through the entire process of selecting, applying to, and securing admission at UK universities. 
You act like a professional human consultant: supportive, knowledgeable, and structured in your guidance.

CORE EXPERTISE:
- UK university rankings, reputations, and subject specializations
- Admission requirements for undergraduate and postgraduate programs
- UCAS application process, deadlines, and strategy
- UK student visa requirements (Tier 4 / Student Visa)
- Tuition fees, scholarships, and funding opportunities
- Academic entry requirements (A-Levels, IB, international equivalents)
- English language proficiency (IELTS, TOEFL, PTE, etc.)
- University accommodation, campus life, and cultural integration
- Career prospects, graduate employability rates, and alumni outcomes

RESPONSE GUIDELINES:
1. STRUCTURED & READABLE FORMAT
   - Always organize responses with clear headings and subheadings.
   - Use bullet points and numbered steps for clarity.
   - Use tables for comparisons (e.g., tuition fees, rankings, scholarships).
   - Present pros & cons when suggesting options.
   - Include timelines and checklists where applicable.

2. PERSONALIZED & ACTIONABLE ADVICE
   - Tailor recommendations to the student’s academic history, financial capacity, and career goals.
   - Suggest multiple suitable universities/programs with clear justifications.
   - Highlight eligibility gaps or additional requirements if any.
   - Always conclude with next steps the student should take.

3. CREDIBILITY & SOURCES
   - Provide official links (UCAS, gov.uk, university websites) when relevant.
   - If referencing university-specific details, cite the source.

4. CONSULTANT TONE
   - Be encouraging, approachable, and professional.
   - Balance realistic advice with motivation.
   - Ask clarifying questions if student context is incomplete.

MANDATORY UNIVERSITY INFORMATION:
Whenever recommending a university, always include:
- Entry requirements
- Application deadlines
- Notable programs or specializations
- Graduate employment rates (if available)
- Scholarships and funding options

YOUR ROLE IN PRACTICE:
- Think like a decision-making assistant for the student.
- Present information in a way that helps them compare, evaluate, and decide.
- Always conclude with:
  - Summary of best options
  - Next steps / action plan
"""


    async def get_relevant_context(self, db: Session, query: str, student_id: int) -> str:
        """Get relevant context from RAG system for the query"""
        try:
            from app.services.rag_service import rag_service
            
            if not rag_service:
                return ""
            
            # Query RAG system for relevant context
            rag_request = RAGQueryRequest(
                query=query,
                max_chunks=5,
                similarity_threshold=0.7
            )
            
            rag_response = await rag_service.hybrid_search(
                db=db,
                query_request=rag_request,
                student_id=student_id
            )
            
            if not rag_response.chunks:
                return ""
            
            # Format context from retrieved chunks
            context_parts = []
            context_parts.append("=== RELEVANT UNIVERSITY INFORMATION ===")
            
            for chunk in rag_response.chunks:
                context_parts.append(f"\n--- Source: {chunk.section_title or 'University Document'} ---")
                context_parts.append(f"Page: {chunk.page_number or 'N/A'}")
                context_parts.append(f"Content: {chunk.content}")
                context_parts.append(f"Relevance Score: {chunk.similarity_score:.2f}")
            
            context_parts.append("\n=== END UNIVERSITY INFORMATION ===\n")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error retrieving RAG context: {e}")
            return ""

    def get_chat_history(self, db: Session, student_id: int) -> ChatHistoryResponse:
        """Get all chat sessions for a student"""
        sessions = db.query(ChatSession).filter(
            ChatSession.student_id == student_id
        ).order_by(desc(ChatSession.updated_at)).all()
        
        return ChatHistoryResponse(sessions=sessions)

    def get_session_messages(self, db: Session, session_id: int, student_id: int) -> SessionMessagesResponse:
        """Get all messages for a specific session"""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.student_id == student_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        
        return SessionMessagesResponse(messages=messages)

    def create_session_title(self, first_message: str) -> str:
        """Generate a title for the chat session based on the first message"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Generate a short, descriptive title (max 50 characters) for a student consultation chat based on their first message. Focus on the main topic (e.g., 'Computer Science Programs', 'Visa Requirements', 'Oxford Application Help')."},
                    {"role": "user", "content": first_message}
                ],
                max_tokens=20,
                temperature=0.3
            )
            title = response.choices[0].message.content.strip().strip('"')
            return title[:50]  # Ensure max 50 characters
        except Exception:
            # Fallback title
            return "Student Consultation"

    def get_conversation_context(self, db: Session, session_id: int) -> List[dict]:
        """Get the last 10 messages from the session for context"""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(desc(ChatMessage.created_at)).limit(10).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

    async def send_message(self, db: Session, student_id: int, request: ChatRequest) -> ChatResponse:
        """Send a message and get AI response"""
        session_id = request.session_id
        session_title = None
        
        # Create new session if none provided
        if not session_id:
            new_session = ChatSession(student_id=student_id)
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session_id = new_session.id
            
            # Generate title from first message
            session_title = self.create_session_title(request.message)
            new_session.title = session_title
            db.commit()
        
        # Get existing session if provided
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.student_id == student_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        # Save user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        
        # Get conversation context (last 10 messages)
        context_messages = self.get_conversation_context(db, session_id)
        
        # Get relevant context from RAG system
        rag_context = await self.get_relevant_context(db, request.message, student_id)
        
        # Prepare system prompt with RAG context if available
        system_content = self.system_prompt
        if rag_context:
            system_content = f"{self.system_prompt}\n\n{rag_context}"
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_content}]
        messages.extend(context_messages)
        
        try:
            # Get AI response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Save AI response
            assistant_message = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=ai_response
            )
            db.add(assistant_message)
            
            # Update session timestamp
            session.updated_at = datetime.utcnow()
            db.commit()
            
            return ChatResponse(
                message=ai_response,
                session_id=session_id,
                session_title=session_title or session.title
            )
            
        except Exception as e:
            # If AI fails, still save user message but return error
            db.rollback()
            raise Exception(f"Failed to get AI response: {str(e)}")

    def delete_session(self, db: Session, session_id: int, student_id: int) -> bool:
        """Delete a chat session and all its messages"""
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.student_id == student_id
        ).first()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        return True
