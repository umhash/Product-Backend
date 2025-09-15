from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ProgramDocument(Base):
    """Document storage for UK programs (PDFs only)"""
    __tablename__ = "program_documents"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("uk_programs.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)  # Generated filename
    original_filename = Column(String, nullable=False)  # Original uploaded filename
    file_path = Column(String, nullable=False)  # Full path to file
    file_size = Column(Integer, nullable=False)  # File size in bytes
    content_type = Column(String, default="application/pdf")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    program = relationship("UKProgram", back_populates="documents")
    rag_document = relationship("RAGDocument", back_populates="program_document", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProgramDocument(id={self.id}, program_id={self.program_id}, filename='{self.filename}')>"
