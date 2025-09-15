from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pathlib import Path
from typing import List, Optional
import uuid
import os
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import Student, Application, ApplicationDocument, UKProgram, RequiredDocument, ApplicationInterviewDocument, ApplicationCASDocument, ApplicationVisaDocument, DocumentType
from sqlalchemy.orm import joinedload
from app.schemas.application import (
    ApplicationResponse, ApplicationCreate, ApplicationSubmitRequest, 
    ApplicationListResponse, DocumentUploadResponse, RequiredDocumentResponse,
    ApplicationWithProgramResponse, ApplicationInterviewDocumentResponse,
    InterviewRequestResponse, CASApplicationResponse, ApplicationCASDocumentResponse,
    CASDocumentSubmissionResponse, ApplicationVisaDocumentResponse,
    VisaDocumentSubmissionResponse, VisaApplicationResponse
)

router = APIRouter(prefix="/applications", tags=["Applications"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/applications")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new application for a program"""
    
    # Check if program exists
    program = db.query(UKProgram).filter(
        UKProgram.id == application_data.program_id,
        UKProgram.is_active == True
    ).first()
    
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    # Check if user already has an application for this program
    existing_app = db.query(Application).filter(
        Application.student_id == current_user.id,
        Application.program_id == application_data.program_id
    ).first()
    
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an application for this program"
        )
    
    # Create new application
    application = Application(
        student_id=current_user.id,
        program_id=application_data.program_id,
        personal_statement=application_data.personal_statement,
        additional_notes=application_data.additional_notes,
        status="draft"
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application


@router.get("/", response_model=ApplicationListResponse)
async def get_my_applications(
    page: int = 1,
    per_page: int = 10,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's applications"""
    
    offset = (page - 1) * per_page
    
    # Get applications with program details using proper joins
    applications_query = db.query(Application).options(
        joinedload(Application.program),
        joinedload(Application.documents)
    ).filter(
        Application.student_id == current_user.id
    ).order_by(desc(Application.created_at))
    
    total = applications_query.count()
    applications = applications_query.offset(offset).limit(per_page).all()
    
    # Format response with program details
    formatted_applications = []
    for app in applications:
        
        # Convert application to dict
        app_dict = {
            "id": app.id,
            "student_id": app.student_id,
            "program_id": app.program_id,
            "status": app.status,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "submitted_at": app.submitted_at,
            "personal_statement": app.personal_statement,
            "additional_notes": app.additional_notes,
            "admin_notes": app.admin_notes,
            "decision_date": app.decision_date,
            "decision_reason": app.decision_reason,
            "offer_letter_requested_at": app.offer_letter_requested_at,
            "offer_letter_received_at": app.offer_letter_received_at,
            "offer_letter_filename": app.offer_letter_filename,
            "offer_letter_original_filename": app.offer_letter_original_filename,
            "offer_letter_size": app.offer_letter_size,
            # Interview fields
            "interview_documents_configured_at": app.interview_documents_configured_at,
            "interview_requested_at": app.interview_requested_at,
            "interview_scheduled_at": app.interview_scheduled_at,
            "interview_date": app.interview_date,
            "interview_status": app.interview_status,
            "interview_notes": app.interview_notes,
            "interview_location": app.interview_location,
            "interview_meeting_link": app.interview_meeting_link,
            "interview_result": app.interview_result,
            "interview_result_notes": app.interview_result_notes,
            "interview_result_date": app.interview_result_date,
            # CAS fields
            "cas_documents_configured_at": app.cas_documents_configured_at,
            "cas_documents_submitted_at": app.cas_documents_submitted_at,
            "cas_applied_at": app.cas_applied_at,
            "cas_received_at": app.cas_received_at,
            "cas_filename": app.cas_filename,
            "cas_original_filename": app.cas_original_filename,
            "cas_notes": app.cas_notes,
            # Visa fields
            "visa_application_enabled_at": app.visa_application_enabled_at,
            "visa_documents_configured_at": app.visa_documents_configured_at,
            "visa_documents_submitted_at": app.visa_documents_submitted_at,
            "visa_applied_at": app.visa_applied_at,
            "visa_received_at": app.visa_received_at,
            "visa_filename": app.visa_filename,
            "visa_original_filename": app.visa_original_filename,
            "visa_notes": app.visa_notes,
            "documents": [
                {
                    "id": doc.id,
                    "application_id": doc.application_id,
                    "document_type": doc.document_type,
                    "filename": doc.filename,
                    "original_filename": doc.original_filename,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "content_type": doc.content_type,
                    "is_required": doc.is_required,
                    "created_at": doc.created_at
                } for doc in app.documents
            ],
            "program": {
                "id": app.program.id,
                "university_name": app.program.university_name,
                "program_name": app.program.program_name,
                "program_level": app.program.program_level,
                "city": app.program.city,
                "field_of_study": app.program.field_of_study
            } if app.program else None
        }
        formatted_applications.append(app_dict)
    
    pages = (total + per_page - 1) // per_page
    
    return ApplicationListResponse(
        applications=formatted_applications,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{application_id}")
async def get_application(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific application details"""
    
    application = db.query(Application).options(
        joinedload(Application.program),
        joinedload(Application.documents)
    ).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return {
        "id": application.id,
        "student_id": application.student_id,
        "program_id": application.program_id,
        "status": application.status,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "submitted_at": application.submitted_at,
        "personal_statement": application.personal_statement,
        "additional_notes": application.additional_notes,
        "admin_notes": application.admin_notes,
        "decision_date": application.decision_date,
        "decision_reason": application.decision_reason,
        "offer_letter_requested_at": application.offer_letter_requested_at,
        "offer_letter_received_at": application.offer_letter_received_at,
        "offer_letter_filename": application.offer_letter_filename,
        "offer_letter_original_filename": application.offer_letter_original_filename,
        "offer_letter_size": application.offer_letter_size,
        # Interview fields
        "interview_documents_configured_at": application.interview_documents_configured_at,
        "interview_requested_at": application.interview_requested_at,
        "interview_scheduled_at": application.interview_scheduled_at,
        "interview_date": application.interview_date,
        "interview_status": application.interview_status,
        "interview_notes": application.interview_notes,
        "interview_location": application.interview_location,
        "interview_meeting_link": application.interview_meeting_link,
        "interview_result": application.interview_result,
        "interview_result_notes": application.interview_result_notes,
        "interview_result_date": application.interview_result_date,
        # CAS fields
        "cas_documents_configured_at": application.cas_documents_configured_at,
        "cas_documents_submitted_at": application.cas_documents_submitted_at,
        "cas_applied_at": application.cas_applied_at,
        "cas_received_at": application.cas_received_at,
        "cas_filename": application.cas_filename,
        "cas_original_filename": application.cas_original_filename,
        "cas_notes": application.cas_notes,
        # Visa fields
        "visa_application_enabled_at": application.visa_application_enabled_at,
        "visa_documents_configured_at": application.visa_documents_configured_at,
        "visa_documents_submitted_at": application.visa_documents_submitted_at,
        "visa_applied_at": application.visa_applied_at,
        "visa_received_at": application.visa_received_at,
        "visa_filename": application.visa_filename,
        "visa_original_filename": application.visa_original_filename,
        "visa_notes": application.visa_notes,
        "documents": [
            {
                "id": doc.id,
                "application_id": doc.application_id,
                "document_type": doc.document_type,
                "filename": doc.filename,
                "original_filename": doc.original_filename,
                "file_path": doc.file_path,
                "file_size": doc.file_size,
                "content_type": doc.content_type,
                "is_required": doc.is_required,
                "created_at": doc.created_at
            } for doc in application.documents
        ],
        "program": {
            "id": application.program.id,
            "university_name": application.program.university_name,
            "program_name": application.program.program_name,
            "program_level": application.program.program_level,
            "city": application.program.city,
            "field_of_study": application.program.field_of_study
        } if application.program else None
    }


@router.get("/{application_id}/required-documents", response_model=List[RequiredDocumentResponse])
async def get_required_documents(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get required documents for an application"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    required_docs = db.query(RequiredDocument).filter(
        RequiredDocument.program_id == application.program_id
    ).all()
    
    return required_docs


@router.post("/{application_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    application_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document for an application"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload documents to a submitted application"
        )
    
    # Validate file type (allow common document formats)
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png"
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF, Word, and image files are allowed."
        )
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / str(application_id) / unique_filename
    
    # Create directory for this application
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Check if document of this type already exists
    existing_doc = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id,
        ApplicationDocument.document_type == document_type
    ).first()
    
    if existing_doc:
        # Delete old file
        old_path = Path(existing_doc.file_path)
        if old_path.exists():
            old_path.unlink()
        
        # Update existing document
        existing_doc.filename = unique_filename
        existing_doc.original_filename = file.filename
        existing_doc.file_path = str(file_path)
        existing_doc.file_size = len(content)
        existing_doc.content_type = file.content_type
        
        db.commit()
        db.refresh(existing_doc)
        
        return DocumentUploadResponse(
            id=existing_doc.id,
            document_type=existing_doc.document_type,
            filename=existing_doc.filename,
            original_filename=existing_doc.original_filename,
            file_size=existing_doc.file_size
        )
    else:
        # Create new document record
        document = ApplicationDocument(
            application_id=application_id,
            document_type=document_type,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return DocumentUploadResponse(
            id=document.id,
            document_type=document.document_type,
            filename=document.filename,
            original_filename=document.original_filename,
            file_size=document.file_size
        )


@router.get("/{application_id}/documents/{document_id}/download")
async def download_document(
    application_id: int,
    document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download an application document"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Get document
    document = db.query(ApplicationDocument).filter(
        ApplicationDocument.id == document_id,
        ApplicationDocument.application_id == application_id
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


@router.post("/{application_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    application_id: int,
    submit_data: ApplicationSubmitRequest,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit an application"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application already submitted"
        )
    
    # Check if all required documents are uploaded
    required_docs = db.query(RequiredDocument).filter(
        RequiredDocument.program_id == application.program_id,
        RequiredDocument.is_required == True
    ).all()
    
    uploaded_docs = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id
    ).all()
    
    uploaded_types = {doc.document_type for doc in uploaded_docs}
    required_types = {doc.document_type for doc in required_docs}
    
    missing_docs = required_types - uploaded_types
    if missing_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required documents: {', '.join(missing_docs)}"
        )
    
    # Update application
    application.status = "submitted"
    application.submitted_at = datetime.utcnow()
    if submit_data.personal_statement:
        application.personal_statement = submit_data.personal_statement
    if submit_data.additional_notes:
        application.additional_notes = submit_data.additional_notes
    
    db.commit()
    db.refresh(application)
    
    return application


@router.delete("/{application_id}/documents/{document_id}")
async def delete_document(
    application_id: int,
    document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an application document"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete documents from a submitted application"
        )
    
    # Get and delete document
    document = db.query(ApplicationDocument).filter(
        ApplicationDocument.id == document_id,
        ApplicationDocument.application_id == application_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file from disk
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.get("/{application_id}/offer-letter/download")
async def download_offer_letter(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download offer letter for an application"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if offer letter is available
    if not application.offer_letter_path or not application.offer_letter_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer letter not available yet"
        )
    
    file_path = Path(application.offer_letter_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer letter file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=application.offer_letter_original_filename,
        media_type="application/pdf"
    )


@router.get("/{application_id}/interview-documents", response_model=List[ApplicationInterviewDocumentResponse])
async def get_interview_documents(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview document requirements for student's application"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    interview_docs = db.query(ApplicationInterviewDocument).filter(
        ApplicationInterviewDocument.application_id == application_id
    ).all()
    
    return [
        ApplicationInterviewDocumentResponse(
            id=doc.id,
            application_id=doc.application_id,
            document_type_id=doc.document_type_id,
            document_name=doc.document_name,
            description=doc.description,
            is_required=doc.is_required,
            is_uploaded=doc.is_uploaded,
            uploaded_document_id=doc.uploaded_document_id,
            created_at=doc.created_at
        ) for doc in interview_docs
    ]


@router.post("/{application_id}/upload-interview-document", response_model=DocumentUploadResponse)
async def upload_interview_document(
    application_id: int,
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document for interview requirements"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status not in ["interview_documents_required"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in interview_documents_required status to upload interview documents"
        )
    
    # Check if this document type is required for interview
    interview_doc = db.query(ApplicationInterviewDocument).filter(
        ApplicationInterviewDocument.application_id == application_id,
        ApplicationInterviewDocument.document_type_id == document_type_id
    ).first()
    
    if not interview_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This document type is not required for interview"
        )
    
    # Validate file type (allow common document formats)
    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png"
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF, Word, and image files are allowed."
        )
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / str(application_id) / unique_filename
    
    # Create directory for this application
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Check if document of this type already exists
    existing_doc = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id,
        ApplicationDocument.document_type == interview_doc.document_name
    ).first()
    
    if existing_doc:
        # Delete old file
        old_path = Path(existing_doc.file_path)
        if old_path.exists():
            old_path.unlink()
        
        # Update existing document
        existing_doc.filename = unique_filename
        existing_doc.original_filename = file.filename
        existing_doc.file_path = str(file_path)
        existing_doc.file_size = len(content)
        existing_doc.content_type = file.content_type
        
        # Update interview document tracking
        interview_doc.is_uploaded = True
        interview_doc.uploaded_document_id = existing_doc.id
        
        db.commit()
        db.refresh(existing_doc)
        
        return DocumentUploadResponse(
            id=existing_doc.id,
            document_type=existing_doc.document_type,
            filename=existing_doc.filename,
            original_filename=existing_doc.original_filename,
            file_size=existing_doc.file_size
        )
    else:
        # Create new document record
        document = ApplicationDocument(
            application_id=application_id,
            document_type=interview_doc.document_name,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Update interview document tracking
        interview_doc.is_uploaded = True
        interview_doc.uploaded_document_id = document.id
        db.commit()
        
        return DocumentUploadResponse(
            id=document.id,
            document_type=document.document_type,
            filename=document.filename,
            original_filename=document.original_filename,
            file_size=document.file_size
        )


@router.post("/{application_id}/request-interview", response_model=InterviewRequestResponse)
async def request_interview(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student requests interview after uploading all required documents"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "interview_documents_required":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in interview_documents_required status to request interview"
        )
    
    # Check if all required interview documents are uploaded
    interview_docs = db.query(ApplicationInterviewDocument).filter(
        ApplicationInterviewDocument.application_id == application_id,
        ApplicationInterviewDocument.is_required == True
    ).all()
    
    missing_docs = [doc for doc in interview_docs if not doc.is_uploaded]
    if missing_docs:
        missing_names = [doc.document_name for doc in missing_docs]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please upload all required documents: {', '.join(missing_names)}"
        )
    
    # Update application status
    application.status = "interview_requested"
    application.interview_requested_at = datetime.utcnow()
    application.interview_status = "pending"
    
    db.commit()
    db.refresh(application)
    
    return InterviewRequestResponse(
        message="Interview request submitted successfully",
        application_id=application_id,
        requested_at=application.interview_requested_at,
        status=application.status
    )


@router.post("/{application_id}/apply-cas", response_model=CASApplicationResponse)
async def apply_for_cas(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student applies for CAS after interview acceptance"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be accepted to apply for CAS"
        )
    
    if application.cas_applied_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAS application already submitted"
        )
    
    # Update application with CAS application
    application.cas_applied_at = datetime.utcnow()
    
    db.commit()
    db.refresh(application)
    
    return CASApplicationResponse(
        message="CAS application submitted successfully",
        application_id=application_id,
        applied_at=application.cas_applied_at
    )


@router.get("/{application_id}/cas/download")
async def download_cas(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download CAS document for an application"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if CAS is available
    if not application.cas_path or not application.cas_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAS document not available yet"
        )
    
    file_path = Path(application.cas_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAS document file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=application.cas_original_filename,
        media_type="application/pdf"
    )


@router.get("/{application_id}/cas-documents", response_model=List[ApplicationCASDocumentResponse])
async def get_cas_documents_student(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get CAS documents required for student's application"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    cas_docs = db.query(ApplicationCASDocument).filter(
        ApplicationCASDocument.application_id == application_id
    ).all()
    
    # Update upload status based on actual document uploads
    for cas_doc in cas_docs:
        uploaded_doc = db.query(ApplicationDocument).filter(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type == cas_doc.document_name
        ).first()
        
        if uploaded_doc:
            cas_doc.is_uploaded = True
            cas_doc.uploaded_document_id = uploaded_doc.id
        else:
            cas_doc.is_uploaded = False
            cas_doc.uploaded_document_id = None
    
    db.commit()
    
    return [
        {
            "id": doc.id,
            "application_id": doc.application_id,
            "document_type_id": doc.document_type_id,
            "document_name": doc.document_name,
            "description": doc.description,
            "is_required": doc.is_required,
            "is_uploaded": doc.is_uploaded,
            "created_at": doc.created_at
        } for doc in cas_docs
    ]


@router.post("/{application_id}/upload-cas-document")
async def upload_cas_document(
    application_id: int,
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student uploads a CAS document"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != 'cas_documents_required':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not in CAS documents required status"
        )
    
    # Get CAS document requirement
    cas_doc = db.query(ApplicationCASDocument).filter(
        ApplicationCASDocument.application_id == application_id,
        ApplicationCASDocument.document_type_id == document_type_id
    ).first()
    
    if not cas_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAS document requirement not found"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = UPLOAD_DIR / str(application_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Check if document already exists and update or create
    existing_doc = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id,
        ApplicationDocument.document_type == cas_doc.document_name
    ).first()
    
    if existing_doc:
        # Remove old file
        if os.path.exists(existing_doc.file_path):
            os.remove(existing_doc.file_path)
        
        # Update existing document
        existing_doc.filename = unique_filename
        existing_doc.original_filename = file.filename
        existing_doc.file_path = str(file_path)
        existing_doc.file_size = len(content)
        existing_doc.content_type = file.content_type
        existing_doc.created_at = datetime.utcnow()
        
        return {
            "id": existing_doc.id,
            "document_type": existing_doc.document_type,
            "filename": existing_doc.filename,
            "original_filename": existing_doc.original_filename,
            "file_size": existing_doc.file_size
        }
    else:
        # Create new document
        document = ApplicationDocument(
            application_id=application_id,
            document_type=cas_doc.document_name,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "id": document.id,
            "document_type": document.document_type,
            "filename": document.filename,
            "original_filename": document.original_filename,
            "file_size": document.file_size
        }


@router.post("/{application_id}/submit-cas-documents", response_model=CASDocumentSubmissionResponse)
async def submit_cas_documents(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student submits CAS documents and requests CAS application"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != 'cas_documents_required':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAS documents are not required for this application"
        )
    
    # Check if all required CAS documents are uploaded
    required_docs = db.query(ApplicationCASDocument).filter(
        ApplicationCASDocument.application_id == application_id,
        ApplicationCASDocument.is_required == True
    ).all()
    
    uploaded_docs = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id
    ).all()
    
    uploaded_types = {doc.document_type for doc in uploaded_docs}
    required_types = {doc.document_name for doc in required_docs}
    
    missing_docs = required_types - uploaded_types
    if missing_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required documents: {', '.join(missing_docs)}"
        )
    
    # Update application status
    application.cas_documents_submitted_at = datetime.utcnow()
    application.status = 'cas_application_in_progress'
    
    db.commit()
    
    return {
        "message": "CAS documents submitted successfully. Admin will now process your CAS application.",
        "application_id": application_id,
        "submitted_at": application.cas_documents_submitted_at
    }


@router.get("/{application_id}/visa-documents", response_model=List[ApplicationVisaDocumentResponse])
async def get_visa_documents_student(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get visa documents required for student's application"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    visa_docs = db.query(ApplicationVisaDocument).filter(
        ApplicationVisaDocument.application_id == application_id
    ).all()
    
    # Update upload status based on actual document uploads
    for visa_doc in visa_docs:
        uploaded_doc = db.query(ApplicationDocument).filter(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type == visa_doc.document_name
        ).first()
        
        if uploaded_doc:
            visa_doc.is_uploaded = True
            visa_doc.uploaded_document_id = uploaded_doc.id
        else:
            visa_doc.is_uploaded = False
            visa_doc.uploaded_document_id = None
    
    db.commit()
    
    return [
        {
            "id": doc.id,
            "application_id": doc.application_id,
            "document_type_id": doc.document_type_id,
            "document_name": doc.document_name,
            "description": doc.description,
            "is_required": doc.is_required,
            "is_uploaded": doc.is_uploaded,
            "created_at": doc.created_at
        } for doc in visa_docs
    ]


@router.post("/{application_id}/upload-visa-document")
async def upload_visa_document(
    application_id: int,
    document_type_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student uploads a visa document"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != 'visa_documents_required':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not in visa documents required status"
        )
    
    # Get visa document requirement
    visa_doc = db.query(ApplicationVisaDocument).filter(
        ApplicationVisaDocument.application_id == application_id,
        ApplicationVisaDocument.document_type_id == document_type_id
    ).first()
    
    if not visa_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visa document requirement not found"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = UPLOAD_DIR / str(application_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Check if document already exists and update or create
    existing_doc = db.query(ApplicationDocument).filter(
        ApplicationDocument.application_id == application_id,
        ApplicationDocument.document_type == visa_doc.document_name
    ).first()
    
    if existing_doc:
        # Remove old file
        if os.path.exists(existing_doc.file_path):
            os.remove(existing_doc.file_path)
        
        # Update existing document
        existing_doc.filename = unique_filename
        existing_doc.original_filename = file.filename
        existing_doc.file_path = str(file_path)
        existing_doc.file_size = len(content)
        existing_doc.content_type = file.content_type
        existing_doc.created_at = datetime.utcnow()
        
        return {
            "id": existing_doc.id,
            "document_type": existing_doc.document_type,
            "filename": existing_doc.filename,
            "original_filename": existing_doc.original_filename,
            "file_size": existing_doc.file_size
        }
    else:
        # Create new document
        document = ApplicationDocument(
            application_id=application_id,
            document_type=visa_doc.document_name,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "id": document.id,
            "document_type": document.document_type,
            "filename": document.filename,
            "original_filename": document.original_filename,
            "file_size": document.file_size
        }


@router.post("/{application_id}/submit-visa-documents", response_model=VisaDocumentSubmissionResponse)
async def submit_visa_documents(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student submits visa documents"""
    
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != 'visa_documents_required':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application status is '{application.status}', must be 'visa_documents_required' to submit visa documents. Admin must configure visa documents first."
        )
    
    # Check if all required visa documents are uploaded
    required_docs = db.query(ApplicationVisaDocument).filter(
        ApplicationVisaDocument.application_id == application_id,
        ApplicationVisaDocument.is_required == True
    ).all()
    
    # Check if each required document is uploaded
    missing_docs = []
    for required_doc in required_docs:
        if not required_doc.is_uploaded:
            missing_docs.append(required_doc.document_name)
    
    if missing_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required documents: {', '.join(missing_docs)}"
        )
    
    # Update application status
    application.visa_documents_submitted_at = datetime.utcnow()
    application.status = 'visa_application_ready'
    
    db.commit()
    
    return {
        "message": "Visa documents submitted successfully. You can now apply for visa.",
        "application_id": application_id,
        "submitted_at": application.visa_documents_submitted_at
    }


@router.post("/{application_id}/apply-visa", response_model=VisaApplicationResponse)
async def apply_for_visa(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student applies for visa after submitting required documents"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "visa_application_ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application status is '{application.status}', must be 'visa_application_ready' to apply for visa. Please ensure visa documents are configured and uploaded."
        )
    
    if application.visa_applied_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visa application already submitted"
        )
    
    # Update application with visa application
    application.visa_applied_at = datetime.utcnow()
    application.status = 'visa_application_in_progress'
    
    db.commit()
    db.refresh(application)
    
    return VisaApplicationResponse(
        message="Visa application submitted successfully. Admin will process your visa application.",
        application_id=application_id,
        applied_at=application.visa_applied_at
    )


@router.get("/{application_id}/visa/download")
async def download_visa(
    application_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Student downloads visa document"""
    
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.student_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if not application.visa_path or not application.visa_original_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visa document not found"
        )
    
    file_path = Path(application.visa_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visa document file not found"
        )
    
    return FileResponse(
        path=str(file_path),
        filename=application.visa_original_filename,
        media_type="application/pdf"
    )
