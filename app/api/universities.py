from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from app.database import get_db
from app.auth import get_current_user
from app.models import Student, UKProgram, ProgramDocument
from app.schemas.program import ProgramResponse

router = APIRouter(prefix="/universities", tags=["Universities"])


@router.get("/{university_id}", response_model=ProgramResponse)
async def get_university_details(
    university_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed university/program information with documents"""
    
    # Get program with documents
    program = db.query(UKProgram).filter(
        UKProgram.id == university_id,
        UKProgram.is_active == True
    ).first()
    
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="University program not found"
        )
    
    return program


@router.get("/documents/{document_id}/download")
async def download_university_document(
    document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a university document (student access)"""
    
    document = db.query(ProgramDocument).filter(
        ProgramDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Verify the program is active
    program = db.query(UKProgram).filter(
        UKProgram.id == document.program_id,
        UKProgram.is_active == True
    ).first()
    
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="University program not found or inactive"
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
