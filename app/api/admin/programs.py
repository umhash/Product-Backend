from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app.database import get_db
from app.models import User, UKProgram, ProgramDocument
from app.schemas.program import (
    ProgramCreate, ProgramUpdate, ProgramResponse, 
    ProgramListResponse, ProgramsListResponse
)
from app.schemas.document import DocumentUploadResponse
from app.auth_admin import require_admin_role
from app.services.file_service import file_service
from app.services.rag_service import rag_service
import math
import asyncio

router = APIRouter(prefix="/admin/api/programs", tags=["Admin - Programs"])


@router.get("/", response_model=ProgramsListResponse)
async def get_programs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in university or program name"),
    level: Optional[str] = Query(None, description="Filter by program level"),
    city: Optional[str] = Query(None, description="Filter by city"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Get paginated list of programs with search and filters"""
    
    # Build query
    query = db.query(UKProgram)
    
    # Apply filters
    if search:
        search_filter = or_(
            UKProgram.university_name.ilike(f"%{search}%"),
            UKProgram.program_name.ilike(f"%{search}%"),
            UKProgram.field_of_study.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if level:
        query = query.filter(UKProgram.program_level == level)
    
    if city:
        query = query.filter(UKProgram.city.ilike(f"%{city}%"))
    
    if is_active is not None:
        query = query.filter(UKProgram.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    programs = query.offset(offset).limit(per_page).all()
    
    # Get document counts for each program
    program_list = []
    for program in programs:
        document_count = db.query(ProgramDocument).filter(
            ProgramDocument.program_id == program.id
        ).count()
        
        program_data = ProgramListResponse.model_validate(program)
        program_data.document_count = document_count
        program_list.append(program_data)
    
    # Calculate pagination info
    pages = math.ceil(total / per_page)
    
    return ProgramsListResponse(
        programs=program_list,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.post("/", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    program: ProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Create a new program"""
    
    # Check if program already exists
    existing_program = db.query(UKProgram).filter(
        UKProgram.university_name == program.university_name,
        UKProgram.program_name == program.program_name
    ).first()
    
    if existing_program:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Program with this name already exists for this university"
        )
    
    # Create program
    db_program = UKProgram(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    
    return ProgramResponse.model_validate(db_program)


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Get a specific program with documents"""
    
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    return ProgramResponse.model_validate(program)


@router.put("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    program_update: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Update a program"""
    
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    # Update fields
    update_data = program_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)
    
    db.commit()
    db.refresh(program)
    
    return ProgramResponse.model_validate(program)


@router.delete("/{program_id}")
async def delete_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Delete a program and all its documents"""
    
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    # Delete associated document files
    documents = db.query(ProgramDocument).filter(
        ProgramDocument.program_id == program_id
    ).all()
    
    for doc in documents:
        file_service.delete_document_file(doc.file_path)
    
    # Delete program (documents will be deleted by CASCADE)
    db.delete(program)
    db.commit()
    
    return {"message": "Program deleted successfully"}


async def process_document_for_rag(program_document_id: int, db: Session):
    """Background task to process document for RAG"""
    if rag_service:
        try:
            await rag_service.process_document(
                db=db,
                program_document_id=program_document_id,
                chunk_size=1024,
                chunk_overlap=200,
                force_reprocess=False
            )
        except Exception as e:
            print(f"Error processing document {program_document_id} for RAG: {e}")


@router.post("/{program_id}/documents", response_model=List[DocumentUploadResponse])
async def upload_program_documents(
    program_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_process_rag: bool = Query(True, description="Automatically process documents for RAG"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Upload PDF documents for a program"""
    
    # Check if program exists
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    uploaded_docs = []
    
    for file in files:
        try:
            # Save file
            filename, file_path, file_size = await file_service.save_program_document(
                file, program_id
            )
            
            # Create database record
            doc = ProgramDocument(
                program_id=program_id,
                filename=filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                content_type=file.content_type or "application/pdf"
            )
            
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            uploaded_docs.append(DocumentUploadResponse(
                id=doc.id,
                filename=doc.filename,
                original_filename=doc.original_filename,
                file_size=doc.file_size
            ))
            
            # Schedule RAG processing in background if enabled
            if auto_process_rag and rag_service:
                background_tasks.add_task(process_document_for_rag, doc.id, db)
            
        except HTTPException:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Handle other errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )
    
    return uploaded_docs
