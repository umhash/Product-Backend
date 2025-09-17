from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class RAGDocument(Base):
    """RAG document metadata and processing status"""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    program_document_id = Column(Integer, ForeignKey("program_documents.id", ondelete="CASCADE"), nullable=False)
    
    # Processing status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Document metadata
    total_chunks = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Processing configuration
    chunk_size = Column(Integer, default=1024)
    chunk_overlap = Column(Integer, default=200)
    embedding_model = Column(String, default="text-embedding-3-large")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    program_document = relationship("ProgramDocument", back_populates="rag_document")
    
    def __repr__(self):
        return f"<RAGDocument(id={self.id}, status='{self.status}', chunks={self.total_chunks})>"


# RAGChunk table removed - all chunk data now stored in Qdrant vector database


class RAGQuery(Base):
    """Track RAG queries for analytics and optimization"""
    __tablename__ = "rag_queries"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    chat_session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    
    # Query information
    query_text = Column(Text, nullable=False)
    query_embedding = Column(JSON, nullable=True)  # Store as JSON array
    
    # Retrieval results
    retrieved_chunks = Column(JSON, nullable=True)  # Array of chunk IDs and scores
    total_retrieved = Column(Integer, default=0)
    max_similarity_score = Column(Float, nullable=True)
    
    # Performance metrics
    embedding_time_ms = Column(Float, nullable=True)
    retrieval_time_ms = Column(Float, nullable=True)
    total_time_ms = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<RAGQuery(id={self.id}, retrieved={self.total_retrieved}, score={self.max_similarity_score})>"
