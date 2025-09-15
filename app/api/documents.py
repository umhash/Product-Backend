from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List
from app.database import get_db
from app.auth import get_current_user
from app.models import Student, ApplicationDocument, Application, UKProgram

router = APIRouter(prefix="/documents", tags=["Student Documents"])


@router.get("/")
async def get_my_documents(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents uploaded by the current student"""
    
    # Get all applications by the student
    applications = db.query(Application).filter(
        Application.student_id == current_user.id
    ).all()
    
    # Get all documents from these applications
    all_documents = []
    for application in applications:
        program = db.query(UKProgram).filter(UKProgram.id == application.program_id).first()
        
        for document in application.documents:
            all_documents.append({
                "id": document.id,
                "document_type": document.document_type,
                "original_filename": document.original_filename,
                "file_size": document.file_size,
                "content_type": document.content_type,
                "created_at": document.created_at,
                "application": {
                    "id": application.id,
                    "status": application.status,
                    "program": {
                        "university_name": program.university_name,
                        "program_name": program.program_name,
                        "city": program.city
                    } if program else None
                }
            })
    
    # Sort by creation date (newest first)
    all_documents.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "documents": all_documents,
        "total": len(all_documents)
    }


@router.get("/{document_id}/download")
async def download_my_document(
    document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a document uploaded by the current student"""
    
    # Get document and verify it belongs to the current student
    document = db.query(ApplicationDocument).join(Application).filter(
        ApplicationDocument.id == document_id,
        Application.student_id == current_user.id
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
            detail="Document file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=document.original_filename,
        media_type=document.content_type
    )


@router.get("/stats")
async def get_document_stats(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document statistics for the current student"""
    
    # Get all applications by the student
    applications = db.query(Application).filter(
        Application.student_id == current_user.id
    ).all()
    
    total_documents = 0
    total_size = 0
    document_types = {}
    
    for application in applications:
        for document in application.documents:
            total_documents += 1
            total_size += document.file_size
            
            doc_type = document.document_type.replace('_', ' ').title()
            document_types[doc_type] = document_types.get(doc_type, 0) + 1
    
    return {
        "total_documents": total_documents,
        "total_size_bytes": total_size,
        "document_types": document_types,
        "applications_count": len(applications)
    }
