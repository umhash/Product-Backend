from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


# Enums for validation
class QualificationLevel(str, Enum):
    high_school = "high_school"
    diploma = "diploma"
    bachelor = "bachelor"
    master = "master"
    phd = "phd"


class GradeSystem(str, Enum):
    gpa_4 = "4.0"
    gpa_10 = "10.0"
    percentage = "percentage"
    uk_classification = "uk_classification"
    other = "other"


class EnglishTestType(str, Enum):
    ielts = "ielts"
    toefl = "toefl"
    pte = "pte"
    duolingo = "duolingo"
    selt = "selt"
    not_taken = "not_taken"


class FundingSource(str, Enum):
    self_funded = "self"
    family = "family"
    scholarship = "scholarship"
    loan = "loan"
    employer = "employer"


class StudyLevel(str, Enum):
    undergraduate = "undergraduate"
    postgraduate = "postgraduate"


class Intake(str, Enum):
    january = "january"
    september = "september"
    both = "both"


class EligibilityStatus(str, Enum):
    eligible = "eligible"
    at_risk = "at_risk"
    not_eligible = "not_eligible"


# Step schemas
class PersonalInfoStep(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    nationality: str = Field(..., min_length=2, max_length=50)
    passport_validity: date
    city: str = Field(..., min_length=2, max_length=50)
    country: str = Field(..., min_length=2, max_length=50)


class EducationStep(BaseModel):
    highest_qualification: QualificationLevel
    gpa_score: float = Field(..., ge=0, le=100)
    grade_system: GradeSystem
    graduation_year: int = Field(..., ge=1990, le=2030)
    medium_of_instruction: str = Field(..., min_length=2, max_length=20)
    notable_coursework: Optional[str] = Field(None, max_length=500)
    discipline: Optional[str] = Field(None, max_length=100)


class EnglishProficiencyStep(BaseModel):
    test_type: EnglishTestType
    overall_score: Optional[float] = Field(None, ge=0, le=120)
    listening_score: Optional[float] = Field(None, ge=0, le=30)
    reading_score: Optional[float] = Field(None, ge=0, le=30)
    writing_score: Optional[float] = Field(None, ge=0, le=30)
    speaking_score: Optional[float] = Field(None, ge=0, le=30)


class FinancialsStep(BaseModel):
    funding_source: FundingSource
    liquid_funds_local: float = Field(..., ge=0)
    local_currency: str = Field(..., min_length=3, max_length=3)
    liquid_funds_gbp: Optional[float] = Field(None, ge=0)
    willing_to_provide_statements: bool


class PreferencesStep(BaseModel):
    field_of_study: str = Field(..., min_length=2, max_length=100)
    study_level: StudyLevel
    target_intake: Intake
    city_preference: Optional[str] = Field(None, max_length=50)


# Complete assessment data
class EligibilityAssessmentCreate(BaseModel):
    # All steps combined
    personal_info: PersonalInfoStep
    education: EducationStep
    english_proficiency: EnglishProficiencyStep
    financials: FinancialsStep
    preferences: PreferencesStep


class EligibilityAssessmentUpdate(BaseModel):
    current_step: Optional[int] = Field(None, ge=1, le=5)
    
    # Step data (all optional for partial updates)
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_validity: Optional[date] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    highest_qualification: Optional[QualificationLevel] = None
    gpa_score: Optional[float] = None
    grade_system: Optional[GradeSystem] = None
    graduation_year: Optional[int] = None
    medium_of_instruction: Optional[str] = None
    notable_coursework: Optional[str] = None
    discipline: Optional[str] = None
    
    english_test_type: Optional[EnglishTestType] = None
    english_overall_score: Optional[float] = None
    english_listening: Optional[float] = None
    english_reading: Optional[float] = None
    english_writing: Optional[float] = None
    english_speaking: Optional[float] = None
    
    funding_source: Optional[FundingSource] = None
    liquid_funds_local: Optional[float] = None
    local_currency: Optional[str] = None
    liquid_funds_gbp: Optional[float] = None
    willing_to_provide_statements: Optional[bool] = None
    
    field_of_study: Optional[str] = None
    study_level: Optional[StudyLevel] = None
    target_intake: Optional[Intake] = None
    city_preference: Optional[str] = None


# Assessment result schemas
class AssessmentReason(BaseModel):
    category: str  # e.g., "English Proficiency", "Academic Requirements"
    status: str  # "pass", "warning", "fail"
    message: str
    explanation: str
    citation: Optional[str] = None


class SuggestedProgram(BaseModel):
    id: int
    university_name: str
    program_name: str
    program_level: str
    field_of_study: str
    city: str
    tuition_fee_min_gbp: Optional[float]
    tuition_fee_max_gbp: Optional[float]
    tuition_fee_gbp: Optional[float]
    match_score: float
    tags: List[str]
    reasons: List[str]


class EligibilityResult(BaseModel):
    status: EligibilityStatus
    score: float  # 0-100
    reasons: List[AssessmentReason]
    suggested_programs: List[SuggestedProgram]
    assessment_date: datetime


class EligibilityAssessmentResponse(BaseModel):
    id: int
    student_id: int
    status: str
    current_step: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # Assessment data
    personal_info: Optional[Dict[str, Any]] = None
    education: Optional[Dict[str, Any]] = None
    english_proficiency: Optional[Dict[str, Any]] = None
    financials: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    
    # Results
    eligibility_result: Optional[EligibilityResult] = None

    class Config:
        from_attributes = True


# UK Program schemas
class UKProgramBase(BaseModel):
    university_name: str
    program_name: str
    program_level: StudyLevel
    field_of_study: str
    city: str


class UKProgramCreate(UKProgramBase):
    min_ielts_overall: Optional[float] = None
    min_ielts_components: Optional[float] = None
    min_toefl_overall: Optional[float] = None
    min_pte_overall: Optional[float] = None
    duolingo_min_score: Optional[float] = None
    min_gpa_4_scale: Optional[float] = None
    min_percentage: Optional[float] = None
    required_qualification: Optional[str] = None
    tuition_fee_min_gbp: Optional[float] = None
    tuition_fee_max_gbp: Optional[float] = None
    tuition_fee_gbp: Optional[float] = None
    living_cost_gbp: Optional[float] = None
    duration_months: Optional[int] = None
    intake_months: Optional[List[int]] = None
    program_description: Optional[str] = None
    programs_available: Optional[str] = None
    ug_entry_requirements: Optional[str] = None
    pg_entry_requirements: Optional[str] = None
    english_requirements_text: Optional[str] = None
    moi_accepted: Optional[str] = None
    initial_deposit_gbp: Optional[float] = None
    scholarships: Optional[str] = None
    study_gap_acceptable: Optional[str] = None
    special_notes: Optional[str] = None
    entry_requirements_text: Optional[str] = None


class UKProgramResponse(UKProgramBase):
    id: int
    min_ielts_overall: Optional[float]
    min_ielts_components: Optional[float]
    min_toefl_overall: Optional[float]
    min_pte_overall: Optional[float]
    duolingo_min_score: Optional[float]
    min_gpa_4_scale: Optional[float]
    min_percentage: Optional[float]
    required_qualification: Optional[str]
    tuition_fee_min_gbp: Optional[float]
    tuition_fee_max_gbp: Optional[float]
    tuition_fee_gbp: Optional[float]
    living_cost_gbp: Optional[float]
    duration_months: Optional[int]
    intake_months: Optional[List[int]]
    program_description: Optional[str]
    programs_available: Optional[str]
    ug_entry_requirements: Optional[str]
    pg_entry_requirements: Optional[str]
    english_requirements_text: Optional[str]
    moi_accepted: Optional[str]
    initial_deposit_gbp: Optional[float]
    scholarships: Optional[str]
    study_gap_acceptable: Optional[str]
    special_notes: Optional[str]
    entry_requirements_text: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
