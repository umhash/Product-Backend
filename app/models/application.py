from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Application(Base):
    """Student university applications"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    program_id = Column(Integer, ForeignKey("uk_programs.id", ondelete="CASCADE"), nullable=False)
    
    # Application status
    status = Column(String, default="draft")  # draft, submitted, under_review, offer_letter_requested, offer_letter_received, interview_documents_required, interview_requested, interview_scheduled, accepted, rejected
    
    # Application metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional application data
    personal_statement = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)
    
    # Admin notes and decisions
    admin_notes = Column(Text, nullable=True)
    decision_date = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    # Offer letter management
    offer_letter_requested_at = Column(DateTime(timezone=True), nullable=True)
    offer_letter_received_at = Column(DateTime(timezone=True), nullable=True)
    offer_letter_filename = Column(String, nullable=True)
    offer_letter_original_filename = Column(String, nullable=True)
    offer_letter_path = Column(String, nullable=True)
    offer_letter_size = Column(Integer, nullable=True)
    
    # Offer letter email draft
    offer_letter_email_draft = Column(Text, nullable=True)
    offer_letter_email_generated_at = Column(DateTime(timezone=True), nullable=True)
    offer_letter_email_edited_by_admin = Column(Boolean, default=False)
    
    # Interview scheduling
    interview_documents_configured_at = Column(DateTime(timezone=True), nullable=True)
    interview_requested_at = Column(DateTime(timezone=True), nullable=True)
    interview_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    interview_date = Column(DateTime(timezone=True), nullable=True)
    interview_status = Column(String, nullable=True)  # pending, scheduled, completed, cancelled
    interview_notes = Column(Text, nullable=True)
    interview_location = Column(String, nullable=True)
    interview_meeting_link = Column(String, nullable=True)
    interview_result = Column(String, nullable=True)  # pass, fail
    interview_result_notes = Column(Text, nullable=True)
    interview_result_date = Column(DateTime(timezone=True), nullable=True)
    
    # CAS application
    cas_documents_configured_at = Column(DateTime(timezone=True), nullable=True)
    cas_documents_submitted_at = Column(DateTime(timezone=True), nullable=True)
    cas_applied_at = Column(DateTime(timezone=True), nullable=True)
    cas_received_at = Column(DateTime(timezone=True), nullable=True)
    cas_filename = Column(String, nullable=True)
    cas_original_filename = Column(String, nullable=True)
    cas_path = Column(String, nullable=True)
    cas_size = Column(Integer, nullable=True)
    cas_notes = Column(Text, nullable=True)
    
    # Visa application
    visa_application_enabled_at = Column(DateTime(timezone=True), nullable=True)
    visa_documents_configured_at = Column(DateTime(timezone=True), nullable=True)
    visa_documents_submitted_at = Column(DateTime(timezone=True), nullable=True)
    visa_applied_at = Column(DateTime(timezone=True), nullable=True)
    visa_received_at = Column(DateTime(timezone=True), nullable=True)
    visa_filename = Column(String, nullable=True)
    visa_original_filename = Column(String, nullable=True)
    visa_path = Column(String, nullable=True)
    visa_size = Column(Integer, nullable=True)
    visa_notes = Column(Text, nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="applications")
    program = relationship("UKProgram")
    documents = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")
    interview_documents = relationship("ApplicationInterviewDocument", back_populates="application", cascade="all, delete-orphan")
    cas_documents = relationship("ApplicationCASDocument", back_populates="application", cascade="all, delete-orphan")
    visa_documents = relationship("ApplicationVisaDocument", back_populates="application", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Application(id={self.id}, student_id={self.student_id}, program_id={self.program_id}, status='{self.status}')>"


class ApplicationDocument(Base):
    """Documents uploaded for applications"""
    __tablename__ = "application_documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String, nullable=False)  # academic_transcript, personal_statement, etc.
    filename = Column(String, nullable=False)  # Generated filename
    original_filename = Column(String, nullable=False)  # Original uploaded filename
    file_path = Column(String, nullable=False)  # Full path to file
    file_size = Column(Integer, nullable=False)  # File size in bytes
    content_type = Column(String, nullable=False)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="documents")
    
    def __repr__(self):
        return f"<ApplicationDocument(id={self.id}, application_id={self.application_id}, type='{self.document_type}')>"


class RequiredDocument(Base):
    """Required documents for each program"""
    __tablename__ = "required_documents"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("uk_programs.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String, nullable=False)
    document_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    program = relationship("UKProgram")
    
    def __repr__(self):
        return f"<RequiredDocument(id={self.id}, program_id={self.program_id}, type='{self.document_type}')>"


class ApplicationInterviewDocument(Base):
    """Required documents for interview scheduling per application"""
    __tablename__ = "application_interview_documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String, nullable=False)  # Copy of document type name for reference
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True)
    is_uploaded = Column(Boolean, default=False)
    uploaded_document_id = Column(Integer, ForeignKey("application_documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="interview_documents")
    document_type = relationship("DocumentType")
    uploaded_document = relationship("ApplicationDocument")
    
    def __repr__(self):
        return f"<ApplicationInterviewDocument(id={self.id}, application_id={self.application_id}, type='{self.document_name}')>"


class ApplicationCASDocument(Base):
    """Documents required for CAS application process"""
    __tablename__ = "application_cas_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String, nullable=False)  # Copy of document type name for reference
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True)
    is_uploaded = Column(Boolean, default=False)
    uploaded_document_id = Column(Integer, ForeignKey("application_documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="cas_documents")
    document_type = relationship("DocumentType")
    uploaded_document = relationship("ApplicationDocument")
    
    def __repr__(self):
        return f"<ApplicationCASDocument(id={self.id}, application_id={self.application_id}, document_name='{self.document_name}')>"


class ApplicationVisaDocument(Base):
    """Documents required for visa application process"""
    __tablename__ = "application_visa_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    document_type_id = Column(Integer, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String, nullable=False)  # Copy of document type name for reference
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True)
    is_uploaded = Column(Boolean, default=False)
    uploaded_document_id = Column(Integer, ForeignKey("application_documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    application = relationship("Application", back_populates="visa_documents")
    document_type = relationship("DocumentType")
    uploaded_document = relationship("ApplicationDocument")
    
    def __repr__(self):
        return f"<ApplicationVisaDocument(id={self.id}, application_id={self.application_id}, document_name='{self.document_name}')>"
