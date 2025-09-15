from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.auth_admin import require_admin_role
from app.models import User, Application, ApplicationDocument, Student, UKProgram, ApplicationInterviewDocument, ApplicationCASDocument, ApplicationVisaDocument, DocumentType
from sqlalchemy.orm import joinedload
from app.schemas.application import (
    ApplicationListResponse, ApplicationUpdate, OfferLetterUploadResponse,
    InterviewDocumentConfigRequest, InterviewDocumentConfigResponse,
    ApplicationInterviewDocumentResponse, InterviewScheduleRequest,
    InterviewScheduleResponse, InterviewResultRequest, InterviewResultResponse,
    CASUploadResponse, CASDocumentConfigRequest, ApplicationCASDocumentResponse,
    VisaDocumentConfigRequest, ApplicationVisaDocumentResponse, VisaUploadResponse
)

router = APIRouter(prefix="/admin/api/applications", tags=["Admin - Applications"])


@router.get("/", response_model=ApplicationListResponse)
async def get_all_applications(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    program_id: Optional[int] = Query(None),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get all applications for admin review"""
    
    offset = (page - 1) * per_page
    
    # Build query with proper joins to avoid N+1 queries
    query = db.query(Application).options(
        joinedload(Application.student),
        joinedload(Application.program),
        joinedload(Application.documents)
    )
    
    # Apply filters
    if status:
        query = query.filter(Application.status == status)
    if program_id:
        query = query.filter(Application.program_id == program_id)
    
    # Only show submitted applications by default
    if not status:
        query = query.filter(Application.status.in_([
            'submitted', 'under_review', 'offer_letter_requested', 'offer_letter_received', 
            'interview_documents_required', 'interview_requested', 'interview_scheduled', 
            'accepted', 'rejected', 'cas_documents_required', 'cas_application_in_progress',
            'visa_documents_required', 'visa_application_ready', 'visa_application_in_progress', 
            'completed'
        ]))
    
    query = query.order_by(desc(Application.submitted_at))
    
    total = query.count()
    applications = query.offset(offset).limit(per_page).all()
    
    # Format response with student and program details
    formatted_applications = []
    for app in applications:
        
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
            "student": {
                "id": app.student.id,
                "full_name": app.student.full_name,
                "email": app.student.email
            } if app.student else None,
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
async def get_application_details(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get detailed application information for admin review"""
    
    application = db.query(Application).options(
        joinedload(Application.student),
        joinedload(Application.program),
        joinedload(Application.documents)
    ).filter(Application.id == application_id).first()
    
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
        "student": {
            "id": application.student.id,
            "full_name": application.student.full_name,
            "email": application.student.email,
            "phone_number": application.student.phone_number,
            "country_of_origin": application.student.country_of_origin,
            "created_at": application.student.created_at
        } if application.student else None,
        "program": {
            "id": application.program.id,
            "university_name": application.program.university_name,
            "program_name": application.program.program_name,
            "program_level": application.program.program_level,
            "city": application.program.city,
            "field_of_study": application.program.field_of_study,
            "tuition_fee_gbp": application.program.tuition_fee_gbp,
            "duration_months": application.program.duration_months
        } if application.program else None
    }


@router.put("/{application_id}")
async def update_application_status(
    application_id: int,
    update_data: ApplicationUpdate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Update application status and admin notes"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Update fields
    if update_data.status:
        application.status = update_data.status
        if update_data.status in ['accepted', 'rejected']:
            application.decision_date = datetime.utcnow()
    
    if update_data.admin_notes is not None:
        application.admin_notes = update_data.admin_notes
    
    if update_data.decision_reason is not None:
        application.decision_reason = update_data.decision_reason
    
    db.commit()
    db.refresh(application)
    
    return {"message": "Application updated successfully", "application": application}


@router.get("/stats/summary")
async def get_application_stats(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get application statistics for admin dashboard"""
    
    total_applications = db.query(Application).filter(Application.status != 'draft').count()
    submitted_applications = db.query(Application).filter(Application.status == 'submitted').count()
    under_review = db.query(Application).filter(Application.status == 'under_review').count()
    offer_letter_requested = db.query(Application).filter(Application.status == 'offer_letter_requested').count()
    offer_letter_received = db.query(Application).filter(Application.status == 'offer_letter_received').count()
    accepted = db.query(Application).filter(Application.status == 'accepted').count()
    rejected = db.query(Application).filter(Application.status == 'rejected').count()
    
    return {
        "total_applications": total_applications,
        "submitted": submitted_applications,
        "under_review": under_review,
        "offer_letter_requested": offer_letter_requested,
        "offer_letter_received": offer_letter_received,
        "accepted": accepted,
        "rejected": rejected
    }


@router.post("/{application_id}/request-offer-letter")
async def request_offer_letter(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin requests offer letter for application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status not in ['submitted', 'under_review']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in submitted or under_review status to request offer letter"
        )
    
    # Update application status and timestamp
    application.status = "offer_letter_requested"
    application.offer_letter_requested_at = datetime.utcnow()
    
    db.commit()
    db.refresh(application)
    
    return {
        "message": "Offer letter request submitted successfully",
        "application_id": application.id,
        "status": application.status,
        "requested_at": application.offer_letter_requested_at
    }


@router.post("/{application_id}/upload-offer-letter", response_model=OfferLetterUploadResponse)
async def upload_offer_letter(
    application_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin uploads offer letter for application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "offer_letter_requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in offer_letter_requested status to upload offer letter"
        )
    
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPEG, and PNG files are allowed"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path("uploads/offer_letters")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Update application
        application.status = "offer_letter_received"
        application.offer_letter_received_at = datetime.utcnow()
        application.offer_letter_filename = unique_filename
        application.offer_letter_original_filename = file.filename
        application.offer_letter_path = str(file_path)
        application.offer_letter_size = len(content)
        
        db.commit()
        db.refresh(application)
        
        return OfferLetterUploadResponse(
            message="Offer letter uploaded successfully",
            application_id=application.id,
            offer_letter_filename=unique_filename,
            offer_letter_original_filename=file.filename,
            offer_letter_size=len(content),
            uploaded_at=application.offer_letter_received_at
        )
        
    except Exception as e:
        # Clean up file if database update fails
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload offer letter: {str(e)}"
        )


@router.get("/{application_id}/offer-letter/download")
async def download_offer_letter_admin(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin downloads offer letter for an application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.post("/{application_id}/configure-interview-documents", response_model=InterviewDocumentConfigResponse)
async def configure_interview_documents(
    application_id: int,
    config_request: InterviewDocumentConfigRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin configures required documents for interview scheduling"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "offer_letter_received":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in offer_letter_received status to configure interview documents"
        )
    
    # Clear existing interview document requirements
    db.query(ApplicationInterviewDocument).filter(
        ApplicationInterviewDocument.application_id == application_id
    ).delete()
    
    # Create new interview document requirements
    interview_docs = []
    for doc_type_id in config_request.document_type_ids:
        # Get document type details
        doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document type with id {doc_type_id} not found"
            )
        
        interview_doc = ApplicationInterviewDocument(
            application_id=application_id,
            document_type_id=doc_type_id,
            document_name=doc_type.name,
            description=doc_type.description,
            is_required=True,
            is_uploaded=False
        )
        db.add(interview_doc)
        interview_docs.append(interview_doc)
    
    # Update application status and timestamp
    application.status = "interview_documents_required"
    application.interview_documents_configured_at = datetime.utcnow()
    if config_request.notes:
        application.interview_notes = config_request.notes
    
    db.commit()
    
    # Refresh objects to get IDs
    for doc in interview_docs:
        db.refresh(doc)
    
    return InterviewDocumentConfigResponse(
        message="Interview documents configured successfully",
        application_id=application_id,
        documents_configured=[
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
        ],
        configured_at=application.interview_documents_configured_at
    )


@router.get("/{application_id}/interview-documents", response_model=List[ApplicationInterviewDocumentResponse])
async def get_interview_documents(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get interview document requirements for an application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.get("/interview-requests", response_model=ApplicationListResponse)
async def get_interview_requests(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get applications requesting interviews"""
    
    offset = (page - 1) * per_page
    
    # Build query for interview requests
    query = db.query(Application).options(
        joinedload(Application.student),
        joinedload(Application.program),
        joinedload(Application.documents)
    ).filter(Application.status == "interview_requested")
    
    query = query.order_by(desc(Application.interview_requested_at))
    
    total = query.count()
    applications = query.offset(offset).limit(per_page).all()
    
    # Format response with student and program details
    formatted_applications = []
    for app in applications:
        formatted_applications.append({
            **app.__dict__,
            "student": {
                "id": app.student.id,
                "full_name": app.student.full_name,
                "email": app.student.email,
                "phone": app.student.phone
            },
            "program": {
                "id": app.program.id,
                "name": app.program.name,
                "university": app.program.university,
                "degree_level": app.program.degree_level,
                "field_of_study": app.program.field_of_study
            } if app.program else None
        })
    
    return ApplicationListResponse(
        applications=formatted_applications,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.post("/{application_id}/schedule-interview", response_model=InterviewScheduleResponse)
async def schedule_interview(
    application_id: int,
    schedule_data: InterviewScheduleRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin schedules interview with date, time, and location details"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "interview_requested":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in interview_requested status to schedule interview"
        )
    
    # Update application with interview details
    application.status = "interview_scheduled"
    application.interview_scheduled_at = datetime.utcnow()
    application.interview_date = schedule_data.interview_date
    application.interview_location = schedule_data.interview_location
    application.interview_meeting_link = schedule_data.interview_meeting_link
    application.interview_status = "scheduled"
    
    if schedule_data.interview_notes:
        application.interview_notes = schedule_data.interview_notes
    
    db.commit()
    db.refresh(application)
    
    return InterviewScheduleResponse(
        message="Interview scheduled successfully",
        application_id=application_id,
        interview_date=application.interview_date,
        interview_location=application.interview_location,
        interview_meeting_link=application.interview_meeting_link,
        scheduled_at=application.interview_scheduled_at
    )


@router.post("/{application_id}/interview-result", response_model=InterviewResultResponse)
async def mark_interview_result(
    application_id: int,
    result_data: InterviewResultRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin marks interview result as pass or fail"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "interview_scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application must be in interview_scheduled status to mark result"
        )
    
    if result_data.result not in ["pass", "fail"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result must be either 'pass' or 'fail'"
        )
    
    # Update application with interview result
    application.interview_result = result_data.result
    application.interview_result_notes = result_data.result_notes
    application.interview_result_date = datetime.utcnow()
    application.interview_status = "completed"
    
    # Update application status based on result
    if result_data.result == "pass":
        application.status = "accepted"  # Enable CAS application
    else:
        application.status = "rejected"
        application.decision_date = datetime.utcnow()
        application.decision_reason = "Failed interview"
    
    db.commit()
    db.refresh(application)
    
    return InterviewResultResponse(
        message=f"Interview result marked as {result_data.result}",
        application_id=application_id,
        result=application.interview_result,
        result_notes=application.interview_result_notes,
        result_date=application.interview_result_date
    )


@router.post("/{application_id}/upload-cas", response_model=CASUploadResponse)
async def upload_cas_document(
    application_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin uploads CAS document for application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if not application.cas_applied_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student must apply for CAS first"
        )
    
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPEG, and PNG files are allowed"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = Path("uploads/cas")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Update application
        application.cas_received_at = datetime.utcnow()
        application.cas_filename = unique_filename
        application.cas_original_filename = file.filename
        application.cas_path = str(file_path)
        application.cas_size = len(content)
        # Enable visa application when CAS is received
        application.visa_application_enabled_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        return CASUploadResponse(
            message="CAS document uploaded successfully. Visa application is now enabled for student.",
            application_id=application.id,
            cas_filename=unique_filename,
            cas_original_filename=file.filename,
            cas_size=len(content),
            uploaded_at=application.cas_received_at
        )
        
    except Exception as e:
        # Clean up file if database update fails
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload CAS document: {str(e)}"
        )


@router.get("/{application_id}/cas/download")
async def download_cas_admin(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin downloads CAS document for an application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.get("/{application_id}/documents/{document_id}/download")
async def download_application_document_admin(
    application_id: int,
    document_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin downloads an application document"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.post("/{application_id}/configure-cas-documents")
async def configure_cas_documents(
    application_id: int,
    config_request: CASDocumentConfigRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin configures required documents for CAS application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if application status allows CAS document configuration
    if application.status != 'accepted':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAS documents can only be configured for accepted applications"
        )
    
    # Clear existing CAS documents for this application
    db.query(ApplicationCASDocument).filter(
        ApplicationCASDocument.application_id == application_id
    ).delete()
    
    # Create new CAS document requirements
    cas_docs = []
    for doc_type_id in config_request.document_type_ids:
        # Get document type details
        doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
        if not doc_type:
            continue
            
        cas_doc = ApplicationCASDocument(
            application_id=application_id,
            document_type_id=doc_type_id,
            document_name=doc_type.name,
            description=doc_type.description,
            is_required=True,
            is_uploaded=False
        )
        db.add(cas_doc)
        cas_docs.append(cas_doc)
    
    # Update application
    application.cas_documents_configured_at = datetime.utcnow()
    application.cas_notes = config_request.notes
    application.status = 'cas_documents_required'
    
    db.commit()
    
    return {
        "message": "CAS documents configured successfully",
        "application_id": application_id,
        "configured_at": application.cas_documents_configured_at,
        "required_documents": len(cas_docs)
    }


@router.get("/{application_id}/cas-documents", response_model=List[ApplicationCASDocumentResponse])
async def get_cas_documents(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get CAS documents for an application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.post("/{application_id}/configure-visa-documents")
async def configure_visa_documents(
    application_id: int,
    config_request: VisaDocumentConfigRequest,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin configures required documents for visa application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if visa application is enabled
    if not application.visa_application_enabled_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visa application is not enabled for this application"
        )
    
    # Clear existing visa documents for this application
    db.query(ApplicationVisaDocument).filter(
        ApplicationVisaDocument.application_id == application_id
    ).delete()
    
    # Create new visa document requirements
    visa_docs = []
    for doc_type_id in config_request.document_type_ids:
        # Get document type details
        doc_type = db.query(DocumentType).filter(DocumentType.id == doc_type_id).first()
        if not doc_type:
            continue
            
        visa_doc = ApplicationVisaDocument(
            application_id=application_id,
            document_type_id=doc_type_id,
            document_name=doc_type.name,
            description=doc_type.description,
            is_required=True,
            is_uploaded=False
        )
        db.add(visa_doc)
        visa_docs.append(visa_doc)
    
    # Update application
    application.visa_documents_configured_at = datetime.utcnow()
    application.visa_notes = config_request.notes
    application.status = 'visa_documents_required'
    
    db.commit()
    
    return {
        "message": "Visa documents configured successfully",
        "application_id": application_id,
        "configured_at": application.visa_documents_configured_at,
        "required_documents": len(visa_docs)
    }


@router.get("/{application_id}/visa-documents", response_model=List[ApplicationVisaDocumentResponse])
async def get_visa_documents(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get visa documents for an application"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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


@router.post("/{application_id}/upload-visa", response_model=VisaUploadResponse)
async def upload_visa_document(
    application_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin uploads visa document"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if not application.visa_applied_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has not applied for visa yet"
        )
    
    # Create upload directory
    upload_dir = Path("uploads/applications") / str(application_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"visa_{uuid.uuid4()}.{file_extension}"
    file_path = upload_dir / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Update application
        application.visa_received_at = datetime.utcnow()
        application.visa_filename = unique_filename
        application.visa_original_filename = file.filename
        application.visa_path = str(file_path)
        application.visa_size = len(content)
        # Mark application as completed
        application.status = 'completed'
        
        db.commit()
        db.refresh(application)
        
        return VisaUploadResponse(
            message="Visa document uploaded successfully. Application is now completed.",
            application_id=application.id,
            visa_filename=unique_filename,
            visa_original_filename=file.filename,
            visa_size=len(content),
            uploaded_at=application.visa_received_at
        )
        
    except Exception as e:
        # Clean up file if database update fails
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload visa document"
        )


@router.get("/{application_id}/visa/download")
async def download_visa_admin(
    application_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Admin downloads visa document"""
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
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
