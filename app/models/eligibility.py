from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class EligibilityAssessment(Base):
    __tablename__ = "eligibility_assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    # Assessment metadata
    status = Column(String, default="in_progress")  # in_progress, completed, expired
    current_step = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Step 1: Personal Information
    full_name = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String, nullable=True)
    passport_validity = Column(Date, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Step 2: Education
    highest_qualification = Column(String, nullable=True)  # bachelor, master, diploma, etc.
    gpa_score = Column(Float, nullable=True)
    grade_system = Column(String, nullable=True)  # 4.0, 10.0, percentage, etc.
    graduation_year = Column(Integer, nullable=True)
    medium_of_instruction = Column(String, nullable=True)  # english, local, mixed
    notable_coursework = Column(Text, nullable=True)
    discipline = Column(String, nullable=True)
    
    # Step 3: English Proficiency
    english_test_type = Column(String, nullable=True)  # ielts, toefl, pte, not_taken
    english_overall_score = Column(Float, nullable=True)
    english_listening = Column(Float, nullable=True)
    english_reading = Column(Float, nullable=True)
    english_writing = Column(Float, nullable=True)
    english_speaking = Column(Float, nullable=True)
    
    # Step 4: Financials
    funding_source = Column(String, nullable=True)  # self, family, scholarship, loan
    liquid_funds_local = Column(Float, nullable=True)
    liquid_funds_gbp = Column(Float, nullable=True)
    local_currency = Column(String, nullable=True)
    willing_to_provide_statements = Column(Boolean, nullable=True)
    
    # Step 5: Preferences
    field_of_study = Column(String, nullable=True)
    study_level = Column(String, nullable=True)  # undergraduate, postgraduate
    target_intake = Column(String, nullable=True)  # january, september
    city_preference = Column(String, nullable=True)
    
    # Assessment Results
    eligibility_status = Column(String, nullable=True)  # eligible, at_risk, not_eligible
    eligibility_score = Column(Float, nullable=True)  # 0-100 score
    assessment_reasons = Column(JSON, nullable=True)  # List of reasons with explanations
    suggested_programs = Column(JSON, nullable=True)  # List of suggested programs
    
    # Relationships
    student = relationship("Student", back_populates="eligibility_assessments")
    
    def __repr__(self):
        return f"<EligibilityAssessment(id={self.id}, student_id={self.student_id}, status='{self.status}')>"


class UKProgram(Base):
    __tablename__ = "uk_programs"

    id = Column(Integer, primary_key=True, index=True)
    university_name = Column(String, nullable=False, index=True)
    program_name = Column(String, nullable=False)
    program_level = Column(String, nullable=False, index=True)
    field_of_study = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False)
    
    min_ielts_overall = Column(Float, nullable=True)
    min_ielts_components = Column(Float, nullable=True)
    min_toefl_overall = Column(Float, nullable=True)
    min_pte_overall = Column(Float, nullable=True)
    duolingo_min_score = Column(Float, nullable=True)
    
    min_gpa_4_scale = Column(Float, nullable=True)
    min_percentage = Column(Float, nullable=True)
    required_qualification = Column(String, nullable=True)
    
    tuition_fee_min_gbp = Column(Float, nullable=True)
    tuition_fee_max_gbp = Column(Float, nullable=True)
    tuition_fee_gbp = Column(Float, nullable=True)
    living_cost_gbp = Column(Float, nullable=True)
    
    duration_months = Column(Integer, nullable=True)
    intake_months = Column(JSON, nullable=True)
    program_description = Column(Text, nullable=True)
    
    programs_available = Column(Text, nullable=True)
    ug_entry_requirements = Column(Text, nullable=True)
    pg_entry_requirements = Column(Text, nullable=True)
    english_requirements_text = Column(Text, nullable=True)
    moi_accepted = Column(String, nullable=True)
    initial_deposit_gbp = Column(Float, nullable=True)
    scholarships = Column(Text, nullable=True)
    study_gap_acceptable = Column(String, nullable=True)
    special_notes = Column(Text, nullable=True)
    entry_requirements_text = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    documents = relationship("ProgramDocument", back_populates="program", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UKProgram(id={self.id}, university='{self.university_name}', program='{self.program_name}')>"
