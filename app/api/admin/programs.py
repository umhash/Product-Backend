from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any
import csv
import io
import json
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


@router.get("/{program_id:int}", response_model=ProgramResponse)
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


@router.put("/{program_id:int}", response_model=ProgramResponse)
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


@router.delete("/{program_id:int}")
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


@router.get("/csv-template")
async def download_programs_csv_template(
    current_user: User = Depends(require_admin_role)
):
    """Provide a blank CSV template with column headers for bulk upload."""
    columns = [
        "university_name",
        "program_name",
        "program_level",
        "field_of_study",
        "min_ielts_overall",
        "min_ielts_components",
        "min_toefl_overall",
        "min_pte_overall",
        "min_gpa_4_scale",
        "min_percentage",
        "required_qualification",
        "tuition_fee_gbp",
        "living_cost_gbp",
        "duration_months",
        "intake_months",
        "city",
        "program_description",
        "is_active",
    ]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=uk_programs_template.csv"
        },
    )


def _parse_bool(value: Optional[str], default: bool = True) -> bool:
    if value is None or str(value).strip() == "":
        return default
    val = str(value).strip().lower()
    if val in {"true", "1", "yes", "y"}:
        return True
    if val in {"false", "0", "no", "n"}:
        return False
    return default


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid float: '{value}'")


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Invalid integer: '{value}'")


def _parse_int_list(value: Optional[str]) -> Optional[List[int]]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    # Allow JSON array or comma-separated values
    try:
        if s.startswith("[") and s.endswith("]"):
            data = json.loads(s)
            if not isinstance(data, list):
                raise ValueError
            return [int(x) for x in data]
    except Exception:
        raise ValueError(f"Invalid JSON array for intake_months: '{value}'")

    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    try:
        return [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid comma-separated integers for intake_months: '{value}'")


@router.post("/bulk-upload")
async def bulk_upload_programs(
    file: UploadFile = File(..., description="CSV file with uk_programs data"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_role)
):
    """Bulk upload programs from a CSV file. Skips duplicates by university+program name.

    Returns a summary with inserted, skipped_duplicates, and row-level errors.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file")

    try:
        raw = await file.read()
        text = raw.decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {str(e)}")

    reader = csv.DictReader(io.StringIO(text))

    required_columns = {"university_name", "program_name", "program_level", "field_of_study", "city"}
    provided_columns = set(reader.fieldnames or [])
    missing = required_columns - provided_columns
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(sorted(missing))}"
        )

    # Preload existing keys to avoid duplicates and reduce DB roundtrips
    existing_pairs = set(
        (u.lower(), p.lower())
        for (u, p) in db.query(UKProgram.university_name, UKProgram.program_name).all()
    )
    seen_in_batch = set()

    inserted = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    row_index = 1  # header is row 1; first data row will be 2
    for row in reader:
        row_index += 1
        try:
            # Trim whitespace
            for k, v in list(row.items()):
                if isinstance(v, str):
                    row[k] = v.strip()

            key = (row.get("university_name", "").lower(), row.get("program_name", "").lower())
            if not key[0] or not key[1]:
                raise ValueError("university_name and program_name are required")

            if key in existing_pairs or key in seen_in_batch:
                skipped += 1
                continue

            data: Dict[str, Any] = {
                "university_name": row.get("university_name") or "",
                "program_name": row.get("program_name") or "",
                "program_level": row.get("program_level") or "",
                "field_of_study": row.get("field_of_study") or "",
                "min_ielts_overall": _parse_float(row.get("min_ielts_overall")),
                "min_ielts_components": _parse_float(row.get("min_ielts_components")),
                "min_toefl_overall": _parse_float(row.get("min_toefl_overall")),
                "min_pte_overall": _parse_float(row.get("min_pte_overall")),
                "min_gpa_4_scale": _parse_float(row.get("min_gpa_4_scale")),
                "min_percentage": _parse_float(row.get("min_percentage")),
                "required_qualification": row.get("required_qualification") or None,
                "tuition_fee_gbp": _parse_float(row.get("tuition_fee_gbp")),
                "living_cost_gbp": _parse_float(row.get("living_cost_gbp")),
                "duration_months": _parse_int(row.get("duration_months")),
                "intake_months": _parse_int_list(row.get("intake_months")),
                "city": row.get("city") or "",
                "program_description": row.get("program_description") or None,
                "is_active": _parse_bool(row.get("is_active"), True),
            }

            # Basic required validation
            for req in ["university_name", "program_name", "program_level", "field_of_study", "city"]:
                if not data[req]:
                    raise ValueError(f"Missing required field: {req}")

            db.add(UKProgram(**data))
            seen_in_batch.add(key)
            inserted += 1
        except Exception as e:
            errors.append({"row": row_index, "error": str(e)})

    try:
        if inserted:
            db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save records: {str(e)}")

    return {
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "errors": errors,
    }


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


@router.post("/{program_id:int}/documents", response_model=List[DocumentUploadResponse])
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
