from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .document import ProgramDocumentResponse


class ProgramBase(BaseModel):
    university_name: str
    program_name: str
    program_level: str  # undergraduate, postgraduate
    field_of_study: str
    
    # Entry requirements
    min_ielts_overall: Optional[float] = None
    min_ielts_components: Optional[float] = None
    min_toefl_overall: Optional[float] = None
    min_pte_overall: Optional[float] = None
    
    # Academic requirements
    min_gpa_4_scale: Optional[float] = None
    min_percentage: Optional[float] = None
    required_qualification: Optional[str] = None
    
    # Financial requirements
    tuition_fee_gbp: Optional[float] = None
    living_cost_gbp: Optional[float] = None
    
    # Program details
    duration_months: Optional[int] = None
    intake_months: Optional[List[int]] = None  # [1, 9] for Jan/Sep
    city: str
    program_description: Optional[str] = None
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
    min_gpa_4_scale: Optional[float] = None
    min_percentage: Optional[float] = None
    required_qualification: Optional[str] = None
    tuition_fee_gbp: Optional[float] = None
    living_cost_gbp: Optional[float] = None
    duration_months: Optional[int] = None
    intake_months: Optional[List[int]] = None
    city: Optional[str] = None
    program_description: Optional[str] = None
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
