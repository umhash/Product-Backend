from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class DocumentType(Base):
    """Available document types for applications"""
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # e.g., "Academic Transcript"
    description = Column(Text, nullable=True)
    is_common = Column(Boolean, default=True)  # Whether commonly required
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DocumentType(id={self.id}, name='{self.name}')>"
