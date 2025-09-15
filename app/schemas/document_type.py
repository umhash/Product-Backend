from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_common: bool = True  # Whether this document type is commonly used


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_common: Optional[bool] = None


class DocumentTypeResponse(DocumentTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentTypeListResponse(BaseModel):
    document_types: List[DocumentTypeResponse]
    total: int


class ProgramDocumentRequirementCreate(BaseModel):
    program_id: int
    document_type_ids: List[int]  # List of required document type IDs


class ProgramDocumentRequirementResponse(BaseModel):
    program_id: int
    required_documents: List[DocumentTypeResponse]


class RequiredDocumentUpdate(BaseModel):
    document_type: str
    document_name: str
    description: Optional[str] = None
    is_required: bool = True
