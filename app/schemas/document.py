from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentBase(BaseModel):
    original_filename: str
    file_size: int
    content_type: str = "application/pdf"


class DocumentCreate(DocumentBase):
    program_id: int
    filename: str
    file_path: str


class ProgramDocumentResponse(DocumentBase):
    id: int
    program_id: int
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    message: str = "Document uploaded successfully"


class DocumentListResponse(BaseModel):
    documents: list[ProgramDocumentResponse]
    total: int
