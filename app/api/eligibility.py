from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import Student, EligibilityAssessment, UKProgram
from app.schemas.eligibility import (
    EligibilityAssessmentUpdate, EligibilityAssessmentResponse,
    EligibilityResult, UKProgramCreate, UKProgramResponse
)
from app.services.eligibility_service import EligibilityService

router = APIRouter(prefix="/eligibility", tags=["Eligibility Checker"])


@router.post("/start", response_model=EligibilityAssessmentResponse)
async def start_assessment(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new eligibility assessment"""
    
    # Check if user has an existing in-progress assessment
    existing = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id,
        EligibilityAssessment.status == "in_progress"
    ).first()
    
    if existing:
        return _format_assessment_response(existing)
    
    # Create new assessment
    assessment = EligibilityAssessment(
        student_id=current_user.id,
        status="in_progress",
        current_step=1
    )
    
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    
    return _format_assessment_response(assessment)


@router.get("/current", response_model=EligibilityAssessmentResponse)
async def get_current_assessment(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current assessment for the user"""
    
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id
    ).order_by(EligibilityAssessment.created_at.desc()).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assessment found. Please start a new assessment."
        )
    
    return _format_assessment_response(assessment)


@router.put("/update", response_model=EligibilityAssessmentResponse)
async def update_assessment(
    update_data: EligibilityAssessmentUpdate,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update assessment data (autosave functionality)"""
    
    # Get current assessment
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id,
        EligibilityAssessment.status == "in_progress"
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active assessment found. Please start a new assessment."
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if hasattr(assessment, field):
            setattr(assessment, field, value)
    
    assessment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(assessment)
    
    return _format_assessment_response(assessment)


@router.post("/submit", response_model=EligibilityResult)
async def submit_assessment(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit assessment for final evaluation"""
    
    # Get current assessment
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id,
        EligibilityAssessment.status == "in_progress"
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active assessment found."
        )
    
    # Validate that all required fields are completed
    required_fields = [
        'full_name', 'date_of_birth', 'nationality', 'passport_validity',
        'highest_qualification', 'gpa_score', 'grade_system', 'graduation_year',
        'discipline',
        'english_test_type', 'funding_source', 'field_of_study', 'study_level'
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(assessment, field):
            missing_fields.append(field)
    
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    # Run eligibility assessment
    eligibility_service = EligibilityService(db)
    result = eligibility_service.assess_eligibility(assessment)
    
    # Update assessment with results
    assessment.status = "completed"
    assessment.completed_at = datetime.utcnow()
    assessment.eligibility_status = result.status.value
    assessment.eligibility_score = result.score
    assessment.assessment_reasons = [reason.model_dump() for reason in result.reasons]
    assessment.suggested_programs = [program.model_dump() for program in result.suggested_programs]
    
    db.commit()
    
    return result


@router.get("/result", response_model=EligibilityResult)
async def get_assessment_result(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest assessment result"""
    
    assessment = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id,
        EligibilityAssessment.status == "completed"
    ).order_by(EligibilityAssessment.completed_at.desc()).first()
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed assessment found."
        )
    
    # Reconstruct result from stored data
    from app.schemas.eligibility import EligibilityStatus, AssessmentReason, SuggestedProgram
    
    reasons = [AssessmentReason(**reason) for reason in assessment.assessment_reasons or []]
    programs = [SuggestedProgram(**program) for program in assessment.suggested_programs or []]
    
    return EligibilityResult(
        status=EligibilityStatus(assessment.eligibility_status),
        score=assessment.eligibility_score or 0,
        reasons=reasons,
        suggested_programs=programs,
        assessment_date=assessment.completed_at or assessment.updated_at
    )


@router.get("/history", response_model=List[EligibilityAssessmentResponse])
async def get_assessment_history(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's assessment history"""
    
    assessments = db.query(EligibilityAssessment).filter(
        EligibilityAssessment.student_id == current_user.id
    ).order_by(EligibilityAssessment.created_at.desc()).all()
    
    return [_format_assessment_response(assessment) for assessment in assessments]


# UK Programs endpoints (for admin/seeding)
@router.post("/programs", response_model=UKProgramResponse)
async def create_program(
    program_data: UKProgramCreate,
    db: Session = Depends(get_db)
):
    """Create a new UK program (admin endpoint)"""
    
    program = UKProgram(**program_data.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    
    return program


@router.get("/programs", response_model=List[UKProgramResponse])
async def get_programs(
    field: Optional[str] = None,
    level: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get UK programs with optional filtering"""
    
    query = db.query(UKProgram).filter(UKProgram.is_active == True)
    
    if field:
        query = query.filter(UKProgram.field_of_study.ilike(f"%{field}%"))
    if level:
        query = query.filter(UKProgram.program_level == level)
    if city:
        query = query.filter(UKProgram.city.ilike(f"%{city}%"))
    
    programs = query.limit(limit).all()
    return programs


def _format_assessment_response(assessment: EligibilityAssessment) -> EligibilityAssessmentResponse:
    """Format assessment for response"""
    
    # Group related fields
    personal_info = None
    if assessment.full_name or assessment.date_of_birth:
        personal_info = {
            "full_name": assessment.full_name,
            "date_of_birth": assessment.date_of_birth.isoformat() if assessment.date_of_birth else None,
            "nationality": assessment.nationality,
            "passport_validity": assessment.passport_validity.isoformat() if assessment.passport_validity else None,
            "city": assessment.city,
            "country": assessment.country
        }
    
    education = None
    if assessment.highest_qualification:
        education = {
            "highest_qualification": assessment.highest_qualification,
            "gpa_score": assessment.gpa_score,
            "grade_system": assessment.grade_system,
            "graduation_year": assessment.graduation_year,
            "medium_of_instruction": assessment.medium_of_instruction,
            "notable_coursework": assessment.notable_coursework,
            "discipline": assessment.discipline
        }
    
    english_proficiency = None
    if assessment.english_test_type:
        english_proficiency = {
            "test_type": assessment.english_test_type,
            "overall_score": assessment.english_overall_score,
            "listening_score": assessment.english_listening,
            "reading_score": assessment.english_reading,
            "writing_score": assessment.english_writing,
            "speaking_score": assessment.english_speaking
        }
    
    financials = None
    if assessment.funding_source:
        financials = {
            "funding_source": assessment.funding_source,
            "liquid_funds_local": assessment.liquid_funds_local,
            "local_currency": assessment.local_currency,
            "liquid_funds_gbp": assessment.liquid_funds_gbp,
            "willing_to_provide_statements": assessment.willing_to_provide_statements
        }
    
    preferences = None
    if assessment.field_of_study:
        preferences = {
            "field_of_study": assessment.field_of_study,
            "study_level": assessment.study_level,
            "target_intake": assessment.target_intake,
            "city_preference": assessment.city_preference
        }
    
    # Format eligibility result if completed
    eligibility_result = None
    if assessment.status == "completed" and assessment.eligibility_status:
        from app.schemas.eligibility import EligibilityStatus, AssessmentReason, SuggestedProgram
        
        reasons = [AssessmentReason(**reason) for reason in assessment.assessment_reasons or []]
        programs = [SuggestedProgram(**program) for program in assessment.suggested_programs or []]
        
        eligibility_result = EligibilityResult(
            status=EligibilityStatus(assessment.eligibility_status),
            score=assessment.eligibility_score or 0,
            reasons=reasons,
            suggested_programs=programs,
            assessment_date=assessment.completed_at or assessment.updated_at
        )
    
    return EligibilityAssessmentResponse(
        id=assessment.id,
        student_id=assessment.student_id,
        status=assessment.status,
        current_step=assessment.current_step,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
        completed_at=assessment.completed_at,
        personal_info=personal_info,
        education=education,
        english_proficiency=english_proficiency,
        financials=financials,
        preferences=preferences,
        eligibility_result=eligibility_result
    )
