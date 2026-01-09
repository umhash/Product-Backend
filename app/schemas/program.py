from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .document import ProgramDocumentResponse


class ProgramBase(BaseModel):
    university_name: str
    program_name: str
    program_level: str
    field_of_study: str
    
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
    city: str
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
    
    is_active: bool = True


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(BaseModel):
    university_name: Optional[str] = None
    program_name: Optional[str] = None
    program_level: Optional[str] = None
    field_of_study: Optional[str] = None
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
    city: Optional[str] = None
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
    is_active: Optional[bool] = None


class ProgramResponse(ProgramBase):
    id: int
    created_at: datetime
    documents: List[ProgramDocumentResponse] = []

    class Config:
        from_attributes = True


class ProgramListResponse(BaseModel):
    id: int
    university_name: str
    program_name: str
    program_level: str
    field_of_study: str
    city: str
    is_active: bool
    created_at: datetime
    document_count: int = 0

    class Config:
        from_attributes = True


class ProgramsListResponse(BaseModel):
    programs: List[ProgramListResponse]
    total: int
    page: int
    per_page: int
    pages: int
