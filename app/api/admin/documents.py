from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ProgramDocument
from app.schemas.document import DocumentListResponse, ProgramDocumentResponse
from app.auth_admin import require_admin_role
from app.services.file_service import file_service
from pathlib import Path

router = APIRouter(prefix="/admin/api/documents", tags=["Admin - Documents"])


@router.get("/program/{program_id}", response_model=DocumentListResponse)
async def get_program_documents(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Get all documents for a specific program"""
    
    documents = db.query(ProgramDocument).filter(
        ProgramDocument.program_id == program_id
    ).all()
    
    document_responses = [
        ProgramDocumentResponse.model_validate(doc) for doc in documents
    ]
    
    return DocumentListResponse(
        documents=document_responses,
        total=len(document_responses)
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Download a specific document"""
    
    document = db.query(ProgramDocument).filter(
        ProgramDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on disk"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=document.original_filename,
        media_type=document.content_type
    )


@router.get("/{document_id}", response_model=ProgramDocumentResponse)
async def get_document_info(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Get document information"""
    
    document = db.query(ProgramDocument).filter(
        ProgramDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return ProgramDocumentResponse.model_validate(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Delete a specific document"""
    
    document = db.query(ProgramDocument).filter(
        ProgramDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from filesystem
    file_deleted = file_service.delete_document_file(document.file_path)
    
    # Delete database record
    db.delete(document)
    db.commit()
    
    return {
        "message": "Document deleted successfully",
        "file_deleted": file_deleted
    }


@router.get("/")
async def get_all_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Get all documents across all programs (for admin overview)"""
    
    documents = db.query(ProgramDocument).all()
    
    document_responses = [
        ProgramDocumentResponse.model_validate(doc) for doc in documents
    ]
    
    return DocumentListResponse(
        documents=document_responses,
        total=len(document_responses)
    )
