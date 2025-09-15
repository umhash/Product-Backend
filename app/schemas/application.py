from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class RequiredDocumentBase(BaseModel):
    document_type: str
    document_name: str
    description: Optional[str] = None
    is_required: bool = True


class RequiredDocumentResponse(RequiredDocumentBase):
    id: int
    program_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationDocumentBase(BaseModel):
    document_type: str
    original_filename: str
    is_required: bool = True


class ApplicationDocumentResponse(ApplicationDocumentBase):
    id: int
    application_id: int
    filename: str
    file_path: str
    file_size: int
    content_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationBase(BaseModel):
    program_id: int
    personal_statement: Optional[str] = None
    additional_notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    personal_statement: Optional[str] = None
    additional_notes: Optional[str] = None
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    decision_reason: Optional[str] = None


class ApplicationResponse(ApplicationBase):
    id: int
    student_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    decision_date: Optional[datetime] = None
    decision_reason: Optional[str] = None
    offer_letter_requested_at: Optional[datetime] = None
    offer_letter_received_at: Optional[datetime] = None
    offer_letter_filename: Optional[str] = None
    offer_letter_original_filename: Optional[str] = None
    # Interview fields
    interview_documents_configured_at: Optional[datetime] = None
    interview_requested_at: Optional[datetime] = None
    interview_scheduled_at: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    interview_status: Optional[str] = None
    interview_notes: Optional[str] = None
    interview_location: Optional[str] = None
    interview_meeting_link: Optional[str] = None
    interview_result: Optional[str] = None
    interview_result_notes: Optional[str] = None
    interview_result_date: Optional[datetime] = None
    
    # CAS fields
    cas_documents_configured_at: Optional[datetime] = None
    cas_documents_submitted_at: Optional[datetime] = None
    cas_applied_at: Optional[datetime] = None
    cas_received_at: Optional[datetime] = None
    cas_filename: Optional[str] = None
    cas_original_filename: Optional[str] = None
    cas_notes: Optional[str] = None
    
    # Visa application fields
    visa_application_enabled_at: Optional[datetime] = None
    visa_documents_configured_at: Optional[datetime] = None
    visa_documents_submitted_at: Optional[datetime] = None
    visa_applied_at: Optional[datetime] = None
    visa_received_at: Optional[datetime] = None
    visa_filename: Optional[str] = None
    visa_original_filename: Optional[str] = None
    visa_notes: Optional[str] = None
    documents: List[ApplicationDocumentResponse] = []

    class Config:
        from_attributes = True


class ApplicationWithProgramResponse(ApplicationResponse):
    student: dict = None  # Will include student details
    program: dict = None  # Will include program details

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationWithProgramResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ApplicationSubmitRequest(BaseModel):
    personal_statement: Optional[str] = None
    additional_notes: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    id: int
    document_type: str
    filename: str
    original_filename: str
    file_size: int


class OfferLetterUploadResponse(BaseModel):
    message: str
    application_id: int
    offer_letter_filename: str
    offer_letter_original_filename: str
    offer_letter_size: int
    uploaded_at: datetime


class ApplicationInterviewDocumentBase(BaseModel):
    document_type_id: int
    document_name: str
    description: Optional[str] = None
    is_required: bool = True


class ApplicationInterviewDocumentResponse(ApplicationInterviewDocumentBase):
    id: int
    application_id: int
    is_uploaded: bool
    uploaded_document_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewDocumentConfigRequest(BaseModel):
    document_type_ids: List[int]
    notes: Optional[str] = None


class ApplicationCASDocumentBase(BaseModel):
    document_type_id: int
    document_name: str
    description: Optional[str] = None
    is_required: bool = True
    is_uploaded: bool = False


class ApplicationCASDocumentCreate(ApplicationCASDocumentBase):
    application_id: int


class ApplicationCASDocumentResponse(ApplicationCASDocumentBase):
    id: int
    application_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CASDocumentConfigRequest(BaseModel):
    document_type_ids: List[int]
    notes: Optional[str] = None


class CASDocumentSubmissionResponse(BaseModel):
    message: str
    application_id: int
    submitted_at: datetime


class ApplicationVisaDocumentBase(BaseModel):
    document_type_id: int
    document_name: str
    description: Optional[str] = None
    is_required: bool = True
    is_uploaded: bool = False


class ApplicationVisaDocumentCreate(ApplicationVisaDocumentBase):
    application_id: int


class ApplicationVisaDocumentResponse(ApplicationVisaDocumentBase):
    id: int
    application_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VisaDocumentConfigRequest(BaseModel):
    document_type_ids: List[int]
    notes: Optional[str] = None


class VisaDocumentSubmissionResponse(BaseModel):
    message: str
    application_id: int
    submitted_at: datetime


class VisaApplicationResponse(BaseModel):
    message: str
    application_id: int
    applied_at: datetime


class VisaUploadResponse(BaseModel):
    message: str
    application_id: int
    visa_filename: str
    visa_original_filename: str
    visa_size: int
    uploaded_at: datetime


class InterviewDocumentConfigResponse(BaseModel):
    message: str
    application_id: int
    documents_configured: List[ApplicationInterviewDocumentResponse]
    configured_at: datetime


class InterviewRequestResponse(BaseModel):
    message: str
    application_id: int
    requested_at: datetime
    status: str


class InterviewScheduleRequest(BaseModel):
    interview_date: datetime
    interview_location: Optional[str] = None
    interview_meeting_link: Optional[str] = None
    interview_notes: Optional[str] = None


class InterviewScheduleResponse(BaseModel):
    message: str
    application_id: int
    interview_date: datetime
    interview_location: Optional[str] = None
    interview_meeting_link: Optional[str] = None
    scheduled_at: datetime


class InterviewResultRequest(BaseModel):
    result: str  # pass or fail
    result_notes: Optional[str] = None


class InterviewResultResponse(BaseModel):
    message: str
    application_id: int
    result: str
    result_notes: Optional[str] = None
    result_date: datetime


class CASApplicationResponse(BaseModel):
    message: str
    application_id: int
    applied_at: datetime


class CASUploadResponse(BaseModel):
    message: str
    application_id: int
    cas_filename: str
    cas_original_filename: str
    cas_size: int
    uploaded_at: datetime
