from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RAGProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    HEADER = "header"
    LIST = "list"


class RAGDocumentBase(BaseModel):
    chunk_size: int = Field(default=1024, ge=256, le=2048)
    chunk_overlap: int = Field(default=200, ge=0, le=512)
    embedding_model: str = Field(default="text-embedding-3-large")


class RAGDocumentCreate(RAGDocumentBase):
    program_document_id: int


class RAGDocumentResponse(RAGDocumentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    program_document_id: int
    status: RAGProcessingStatus
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_chunks: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime


class RAGChunkResponse(BaseModel):
    """Chunk data retrieved from Qdrant vector database"""
    content: str
    chunk_index: int
    token_count: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    chunk_type: ChunkType = ChunkType.TEXT
    chunk_metadata: Optional[Dict[str, Any]] = None
    similarity_score: float
    
    # University-specific metadata
    program_document_id: int
    program_id: int
    university_name: Optional[str] = None
    program_name: Optional[str] = None
    program_level: Optional[str] = None
    field_of_study: Optional[str] = None
    document_type: Optional[str] = None


class RAGProcessingRequest(BaseModel):
    program_document_id: int
    chunk_size: Optional[int] = Field(default=1024, ge=256, le=2048)
    chunk_overlap: Optional[int] = Field(default=200, ge=0, le=512)
    force_reprocess: bool = Field(default=False)


class RAGProcessingResponse(BaseModel):
    rag_document_id: int
    status: RAGProcessingStatus
    message: str


class RAGQueryRequest(BaseModel):
    query: str
    max_chunks: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class RAGQueryResponse(BaseModel):
    query: str
    chunks: List[RAGChunkResponse]
    total_retrieved: int
    embedding_time_ms: float
    retrieval_time_ms: float
    total_time_ms: float
    search_method: str = "hybrid"  # hybrid, dense, sparse


class RAGStatusResponse(BaseModel):
    total_documents: int
    pending_documents: int
    processing_documents: int
    completed_documents: int
    failed_documents: int
    total_chunks: int
    total_tokens: int


class RAGDocumentListResponse(BaseModel):
    documents: List[RAGDocumentResponse]
    total: int
    page: int
    per_page: int
    pages: int
