from typing import List, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from app.models import EligibilityAssessment, UKProgram
from app.schemas.eligibility import (
    EligibilityStatus, AssessmentReason, SuggestedProgram, EligibilityResult
)


class EligibilityService:
    """Service for determining UK university eligibility"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def assess_eligibility(self, assessment: EligibilityAssessment) -> EligibilityResult:
        """Main eligibility assessment function"""
        
        reasons = []
        total_score = 0
        max_score = 0
        
        # 1. Age and Passport Validity (10 points)
        age_score, age_reasons = self._assess_age_and_passport(assessment)
        reasons.extend(age_reasons)
        total_score += age_score
        max_score += 10
        
        # 2. Academic Qualifications (25 points)
        academic_score, academic_reasons = self._assess_academic_qualifications(assessment)
        reasons.extend(academic_reasons)
        total_score += academic_score
        max_score += 25
        
        # 3. English Proficiency (30 points)
        english_score, english_reasons = self._assess_english_proficiency(assessment)
        reasons.extend(english_reasons)
        total_score += english_score
        max_score += 30
        
        # 4. Financial Requirements (25 points)
        financial_score, financial_reasons = self._assess_financial_requirements(assessment)
        reasons.extend(financial_reasons)
        total_score += financial_score
        max_score += 25
        
        # 5. Program Availability (10 points)
        program_score, program_reasons = self._assess_program_availability(assessment)
        reasons.extend(program_reasons)
        total_score += program_score
        max_score += 10
        
        # Calculate final score
        final_score = (total_score / max_score) * 100 if max_score > 0 else 0
        
        # Determine eligibility status
        if final_score >= 80:
            status = EligibilityStatus.eligible
        elif final_score >= 60:
            status = EligibilityStatus.at_risk
        else:
            status = EligibilityStatus.not_eligible
        
        # Get suggested programs
        suggested_programs = self._get_suggested_programs(assessment, final_score)
        
        return EligibilityResult(
            status=status,
            score=final_score,
            reasons=reasons,
            suggested_programs=suggested_programs,
            assessment_date=datetime.utcnow()
        )
    
    def _assess_age_and_passport(self, assessment: EligibilityAssessment) -> Tuple[float, List[AssessmentReason]]:
        """Assess age and passport validity"""
        reasons = []
        score = 0
        
        if assessment.date_of_birth:
            age = (date.today() - assessment.date_of_birth).days / 365.25
            
            if 16 <= age <= 35:
                score += 7
                if age <= 25:
                    reasons.append(AssessmentReason(
                        category="Age Requirements",
                        status="pass",
                        message="Excellent age for UK study",
                        explanation=f"At {age:.0f} years old, you're in the prime age range for international study. UK universities particularly value younger students who can fully immerse in campus life and build long-term career networks. Your age gives you maximum flexibility for both undergraduate and postgraduate programs.",
                        citation="UK universities report highest success rates for students aged 18-25, with excellent integration into academic and social communities."
                    ))
                else:
                    reasons.append(AssessmentReason(
                        category="Age Requirements",
                        status="pass",
                        message="Mature student advantage",
                        explanation=f"At {age:.0f} years old, you bring valuable life experience to your studies. UK universities highly value mature students for their focus, professional background, and contribution to classroom discussions. Many programs specifically benefit from diverse age groups.",
                        citation="Research shows mature students (25-35) often outperform younger peers due to better time management and clear career goals."
                    ))
            elif age < 16:
                reasons.append(AssessmentReason(
                    category="Age Requirements",
                    status="fail",
                    message="Below minimum age for UK university admission",
                    explanation=f"At {age:.0f} years old, you may need to complete additional qualifications before university admission.",
                    citation="UK universities require students to be at least 16 years old."
                ))
            else:
                score += 3
                reasons.append(AssessmentReason(
                    category="Age Requirements",
                    status="warning",
                    message="Age may require additional consideration",
                    explanation=f"At {age:.0f} years old, some programs may have age preferences, but many options remain available.",
                    citation="While there's no upper age limit, some competitive programs prefer younger candidates."
                ))
        
        if assessment.passport_validity:
            months_valid = (assessment.passport_validity - date.today()).days / 30
            
            if months_valid >= 18:
                score += 3
                reasons.append(AssessmentReason(
                    category="Passport Validity",
                    status="pass",
                    message="Passport validity meets UK visa requirements",
                    explanation=f"Your passport is valid for {months_valid:.0f} more months, meeting the 18-month minimum requirement.",
                    citation="UK student visas require passports valid for at least 18 months from application date."
                ))
            else:
                reasons.append(AssessmentReason(
                    category="Passport Validity",
                    status="fail",
                    message="Passport needs renewal for UK visa application",
                    explanation=f"Your passport expires in {months_valid:.0f} months. You'll need to renew it before applying for a UK student visa.",
                    citation="UK student visas require passports valid for at least 18 months from application date."
                ))
        
        return score, reasons
    
    def _assess_academic_qualifications(self, assessment: EligibilityAssessment) -> Tuple[float, List[AssessmentReason]]:
        """Assess academic qualifications"""
        reasons = []
        score = 0
        
        if not assessment.highest_qualification:
            reasons.append(AssessmentReason(
                category="Academic Qualifications",
                status="fail",
                message="Academic qualification information required",
                explanation="Please provide your highest academic qualification to assess eligibility.",
                citation="UK universities require proof of academic qualifications for admission."
            ))
            return score, reasons
        
        # Qualification level assessment
        qualification_scores = {
            "high_school": 15,
            "diploma": 18,
            "bachelor": 25,
            "master": 25,
            "phd": 25
        }
        
        qual_score = qualification_scores.get(assessment.highest_qualification, 0)
        score += qual_score
        
        if assessment.highest_qualification in ["bachelor", "master", "phd"]:
            reasons.append(AssessmentReason(
                category="Academic Qualifications",
                status="pass",
                message="Qualification level meets UK university requirements",
                explanation=f"Your {assessment.highest_qualification} degree qualifies you for UK university programs.",
                citation="UK universities accept bachelor's degrees and above for postgraduate programs."
            ))
        elif assessment.highest_qualification == "diploma":
            reasons.append(AssessmentReason(
                category="Academic Qualifications",
                status="warning",
                message="Diploma may require additional assessment",
                explanation="Your diploma may qualify for some programs, but additional qualifications might be needed for others.",
                citation="UK universities evaluate diplomas case-by-case for program admission."
            ))
        else:
            reasons.append(AssessmentReason(
                category="Academic Qualifications",
                status="warning",
                message="May need foundation or pathway programs",
                explanation="High school qualifications typically require foundation programs before direct university entry.",
                citation="UK universities often require foundation programs for international high school graduates."
            ))
        
        # GPA assessment
        if assessment.gpa_score and assessment.grade_system:
            normalized_gpa = self._normalize_gpa(assessment.gpa_score, assessment.grade_system)
            
            if normalized_gpa >= 3.5:
                reasons.append(AssessmentReason(
                    category="Academic Performance",
                    status="pass",
                    message="Excellent academic performance",
                    explanation=f"Your GPA of {assessment.gpa_score} ({assessment.grade_system}) demonstrates strong academic ability.",
                    citation="UK universities typically require a minimum 3.0 GPA (4.0 scale) for admission."
                ))
            elif normalized_gpa >= 3.0:
                reasons.append(AssessmentReason(
                    category="Academic Performance",
                    status="pass",
                    message="Good academic performance meets requirements",
                    explanation=f"Your GPA of {assessment.gpa_score} ({assessment.grade_system}) meets minimum requirements.",
                    citation="UK universities typically require a minimum 3.0 GPA (4.0 scale) for admission."
                ))
            else:
                reasons.append(AssessmentReason(
                    category="Academic Performance",
                    status="warning",
                    message="GPA may limit program options",
                    explanation=f"Your GPA of {assessment.gpa_score} ({assessment.grade_system}) is below the typical 3.0 minimum.",
                    citation="UK universities typically require a minimum 3.0 GPA (4.0 scale) for admission."
                ))
        
        return score, reasons
    
    def _assess_english_proficiency(self, assessment: EligibilityAssessment) -> Tuple[float, List[AssessmentReason]]:
        """Assess English proficiency"""
        reasons = []
        score = 0
        
        if assessment.english_test_type == "not_taken":
            reasons.append(AssessmentReason(
                category="English Proficiency",
                status="warning",
                message="English proficiency test required",
                explanation="You'll need to take IELTS, TOEFL, or PTE to demonstrate English proficiency for UK universities.",
                citation="UK universities require English proficiency tests for international students."
            ))
            return score, reasons
        
        if not assessment.english_overall_score:
            reasons.append(AssessmentReason(
                category="English Proficiency",
                status="warning",
                message="English test score needed for assessment",
                explanation="Please provide your English test scores for accurate eligibility assessment.",
                citation="UK universities have specific English proficiency requirements."
            ))
            return score, reasons
        
        # IELTS assessment (most common)
        if assessment.english_test_type == "ielts":
            if assessment.english_overall_score >= 7.0:
                score += 30
                reasons.append(AssessmentReason(
                    category="English Proficiency",
                    status="pass",
                    message="Outstanding English proficiency - opens all doors",
                    explanation=f"Your IELTS score of {assessment.english_overall_score} is exceptional and qualifies you for the most competitive UK programs including Oxford, Cambridge, and Imperial College. This score demonstrates you can excel in academic discussions, research, and professional communication. You'll have no language barriers in your studies.",
                    citation="Top UK universities (Russell Group) typically require IELTS 7.0-7.5, with your score meeting or exceeding all requirements."
                ))
            elif assessment.english_overall_score >= 6.5:
                score += 25
                reasons.append(AssessmentReason(
                    category="English Proficiency",
                    status="pass",
                    message="Good IELTS score meets most requirements",
                    explanation=f"Your IELTS score of {assessment.english_overall_score} meets requirements for most UK universities.",
                    citation="Most UK universities require IELTS 6.0-6.5 for admission."
                ))
            elif assessment.english_overall_score >= 6.0:
                score += 20
                reasons.append(AssessmentReason(
                    category="English Proficiency",
                    status="pass",
                    message="IELTS score meets minimum requirements",
                    explanation=f"Your IELTS score of {assessment.english_overall_score} meets minimum requirements for many programs.",
                    citation="Many UK universities accept IELTS 6.0 for undergraduate programs."
                ))
            else:
                score += 10
                reasons.append(AssessmentReason(
                    category="English Proficiency",
                    status="warning",
                    message="IELTS score below typical requirements",
                    explanation=f"Your IELTS score of {assessment.english_overall_score} is below most university requirements. Consider retaking the test.",
                    citation="Most UK universities require IELTS 6.0+ for admission."
                ))
        
        # Similar logic for TOEFL and PTE would go here
        
        return score, reasons
    
    def _assess_financial_requirements(self, assessment: EligibilityAssessment) -> Tuple[float, List[AssessmentReason]]:
        """Assess financial requirements"""
        reasons = []
        score = 0
        
        if not assessment.liquid_funds_gbp and not assessment.liquid_funds_local:
            reasons.append(AssessmentReason(
                category="Financial Requirements",
                status="warning",
                message="Financial information needed for visa assessment",
                explanation="UK student visas require proof of financial support. Please provide funding details.",
                citation="UK student visas require proof of £1,334/month living costs plus tuition fees."
            ))
            return score, reasons
        
        # Estimate required funds (tuition + living costs)
        estimated_annual_cost = 25000  # £25k average for international students
        
        available_funds = assessment.liquid_funds_gbp or 0
        if assessment.liquid_funds_local and assessment.local_currency:
            # Simple conversion estimate (would use real exchange rates in production)
            conversion_rates = {"USD": 0.79, "EUR": 0.85, "INR": 0.012, "PKR": 0.0036}
            rate = conversion_rates.get(assessment.local_currency, 0.01)
            available_funds += assessment.liquid_funds_local * rate
        
        if available_funds >= estimated_annual_cost:
            score += 25
            reasons.append(AssessmentReason(
                category="Financial Requirements",
                status="pass",
                message="Sufficient funds for UK study",
                explanation=f"Your available funds (≈£{available_funds:,.0f}) exceed the estimated annual cost of £{estimated_annual_cost:,}.",
                citation="UK student visas require proof of tuition fees plus £1,334/month living costs."
            ))
        elif available_funds >= estimated_annual_cost * 0.7:
            score += 18
            reasons.append(AssessmentReason(
                category="Financial Requirements",
                status="warning",
                message="Funds may be sufficient with careful budgeting",
                explanation=f"Your available funds (≈£{available_funds:,.0f}) are close to requirements. Consider additional funding sources.",
                citation="UK student visas require proof of tuition fees plus £1,334/month living costs."
            ))
        else:
            score += 10
            reasons.append(AssessmentReason(
                category="Financial Requirements",
                status="warning",
                message="Additional funding sources needed",
                explanation=f"Your available funds (≈£{available_funds:,.0f}) may not meet visa requirements. Explore scholarships or loans.",
                citation="UK student visas require proof of tuition fees plus £1,334/month living costs."
            ))
        
        # Funding source assessment
        if assessment.funding_source in ["scholarship", "family"]:
            reasons.append(AssessmentReason(
                category="Funding Source",
                status="pass",
                message="Reliable funding source identified",
                explanation=f"{assessment.funding_source.title()} funding is well-regarded by UK visa officers.",
                citation="UK visa officers prefer documented funding sources like family support or scholarships."
            ))
        
        return score, reasons
    
    def _assess_program_availability(self, assessment: EligibilityAssessment) -> Tuple[float, List[AssessmentReason]]:
        """Assess program availability"""
        reasons = []
        score = 0
        
        if assessment.field_of_study and assessment.study_level:
            # Check if programs exist in our database
            programs = self.db.query(UKProgram).filter(
                UKProgram.field_of_study.ilike(f"%{assessment.field_of_study}%"),
                UKProgram.program_level == assessment.study_level,
                UKProgram.is_active == True
            ).limit(5).all()
            
            if programs:
                score += 10
                reasons.append(AssessmentReason(
                    category="Program Availability",
                    status="pass",
                    message=f"Multiple programs available in {assessment.field_of_study}",
                    explanation=f"Found {len(programs)} programs matching your preferences in UK universities.",
                    citation="UK universities offer diverse programs across multiple institutions."
                ))
            else:
                score += 5
                reasons.append(AssessmentReason(
                    category="Program Availability",
                    status="warning",
                    message="Limited programs found in specified field",
                    explanation=f"Few programs found for {assessment.field_of_study}. Consider related fields or different universities.",
                    citation="UK universities offer programs across many disciplines, with some specializations more common than others."
                ))
        
        return score, reasons
    
    def _normalize_gpa(self, gpa: float, system: str) -> float:
        """Normalize GPA to 4.0 scale"""
        if system == "4.0":
            return gpa
        elif system == "10.0":
            return (gpa / 10.0) * 4.0
        elif system == "percentage":
            return (gpa / 100.0) * 4.0
        else:
            return gpa / 4.0  # Default assumption
    
    def _get_suggested_programs(self, assessment: EligibilityAssessment, eligibility_score: float) -> List[SuggestedProgram]:
        """Get suggested programs based on assessment"""
        programs = []
        
        if not assessment.field_of_study or not assessment.study_level:
            return programs
        
        # Query matching programs - get more to ensure variety
        primary_programs = self.db.query(UKProgram).filter(
            UKProgram.field_of_study.ilike(f"%{assessment.field_of_study}%"),
            UKProgram.program_level == assessment.study_level,
            UKProgram.is_active == True
        ).limit(8).all()
        
        # If we don't have enough exact matches, get related programs
        if len(primary_programs) < 4:
            related_programs = self.db.query(UKProgram).filter(
                UKProgram.program_level == assessment.study_level,
                UKProgram.is_active == True,
                ~UKProgram.id.in_([p.id for p in primary_programs])
            ).limit(8 - len(primary_programs)).all()
            primary_programs.extend(related_programs)
        
        db_programs = primary_programs
        
        for program in db_programs:
            # Calculate match score
            match_score = self._calculate_program_match_score(assessment, program, eligibility_score)
            
            # Generate tags
            tags = self._generate_program_tags(assessment, program)
            
            # Generate reasons
            reasons = self._generate_program_reasons(assessment, program)
            
            programs.append(SuggestedProgram(
                id=program.id,
                university_name=program.university_name,
                program_name=program.program_name,
                program_level=program.program_level,
                field_of_study=program.field_of_study,
                city=program.city,
                tuition_fee_gbp=program.tuition_fee_gbp,
                match_score=match_score,
                tags=tags,
                reasons=reasons
            ))
        
        # Sort by match score and return exactly 4 programs
        programs.sort(key=lambda x: x.match_score, reverse=True)
        
        return programs[:4]  # Return exactly 4 programs
    
    def _calculate_program_match_score(self, assessment: EligibilityAssessment, program: UKProgram, base_score: float) -> float:
        """Calculate how well a program matches the student's profile"""
        match_score = base_score * 0.6  # Start with 60% of eligibility score
        
        # English proficiency match
        if assessment.english_test_type == "ielts" and assessment.english_overall_score:
            if program.min_ielts_overall and assessment.english_overall_score >= program.min_ielts_overall:
                match_score += 15
            elif program.min_ielts_overall and assessment.english_overall_score >= (program.min_ielts_overall - 0.5):
                match_score += 10
        
        # Academic match
        if assessment.gpa_score and assessment.grade_system:
            normalized_gpa = self._normalize_gpa(assessment.gpa_score, assessment.grade_system)
            if program.min_gpa_4_scale and normalized_gpa >= program.min_gpa_4_scale:
                match_score += 15
        
        # City preference
        if assessment.city_preference and program.city.lower() == assessment.city_preference.lower():
            match_score += 10
        
        return min(match_score, 100)  # Cap at 100
    
    def _generate_program_tags(self, assessment: EligibilityAssessment, program: UKProgram) -> List[str]:
        """Generate tags for a program based on student profile"""
        tags = []
        
        # English proficiency tags
        if assessment.english_test_type == "ielts" and assessment.english_overall_score:
            if program.min_ielts_overall and assessment.english_overall_score >= program.min_ielts_overall:
                tags.append("Meets IELTS")
            elif program.min_ielts_overall:
                tags.append("IELTS Gap")
        
        # Financial tags
        if program.tuition_fee_gbp and assessment.liquid_funds_gbp:
            if assessment.liquid_funds_gbp >= program.tuition_fee_gbp * 1.5:
                tags.append("Affordable")
            elif assessment.liquid_funds_gbp >= program.tuition_fee_gbp:
                tags.append("Tight Budget")
        
        # Location tags
        if assessment.city_preference and program.city.lower() == assessment.city_preference.lower():
            tags.append("Preferred City")
        
        return tags
    
    def _generate_program_reasons(self, assessment: EligibilityAssessment, program: UKProgram) -> List[str]:
        """Generate detailed, personalized reasons why this program is suggested using enhanced LLM-style reasoning"""
        reasons = []
        
        # Field match with detailed explanation
        if assessment.field_of_study:
            if program.field_of_study.lower() == assessment.field_of_study.lower():
                reasons.append(f"Perfect match for your {assessment.field_of_study} career goals - this program aligns directly with your academic interests and professional aspirations")
            elif assessment.field_of_study.lower() in program.field_of_study.lower() or program.field_of_study.lower() in assessment.field_of_study.lower():
                reasons.append(f"Strong alignment with your {assessment.field_of_study} background - offers specialized knowledge that complements your existing expertise")
        
        # English proficiency with actionable insights
        if program.min_ielts_overall and assessment.english_overall_score:
            if assessment.english_overall_score >= program.min_ielts_overall:
                reasons.append(f"You exceed the English requirements (your {assessment.english_overall_score} vs required {program.min_ielts_overall}) - no language barriers to worry about")
            else:
                gap = program.min_ielts_overall - assessment.english_overall_score
                if gap <= 0.5:
                    reasons.append(f"English requirement is within reach - just {gap:.1f} IELTS points away, achievable with focused preparation")
                else:
                    reasons.append(f"English improvement needed but manageable - {gap:.1f} IELTS points gap can be bridged with dedicated study")
        
        # Academic qualification match with confidence building
        if assessment.gpa_score and assessment.grade_system and program.min_gpa_4_scale:
            normalized_gpa = self._normalize_gpa(assessment.gpa_score, assessment.grade_system)
            if normalized_gpa >= program.min_gpa_4_scale:
                reasons.append(f"Your academic performance ({normalized_gpa:.1f}/4.0) exceeds requirements ({program.min_gpa_4_scale}/4.0) - you're a competitive candidate")
            elif normalized_gpa >= program.min_gpa_4_scale - 0.2:
                reasons.append(f"Your academics are very close to requirements - with strong supporting materials, you have good admission chances")
        
        # Financial feasibility with practical advice
        if program.tuition_fee_gbp and assessment.liquid_funds_gbp:
            total_cost = program.tuition_fee_gbp + (program.living_cost_gbp or 15000)
            if assessment.liquid_funds_gbp >= total_cost * 1.2:
                reasons.append(f"Financially comfortable choice - your funds (£{assessment.liquid_funds_gbp:,}) comfortably cover all costs with buffer")
            elif assessment.liquid_funds_gbp >= total_cost:
                reasons.append(f"Financially feasible - your budget covers the estimated total cost of £{total_cost:,} for this program")
            else:
                shortfall = total_cost - assessment.liquid_funds_gbp
                reasons.append(f"Consider scholarship opportunities - you may need additional £{shortfall:,} funding, but many options available")
        
        # Location preference with lifestyle insights
        if assessment.city_preference and program.city:
            if program.city.lower() == assessment.city_preference.lower():
                reasons.append(f"Located in your preferred city of {program.city} - you'll feel at home while studying")
            else:
                reasons.append(f"Excellent alternative to {assessment.city_preference} - {program.city} offers unique opportunities and lower living costs")
        
        # University reputation and program quality
        prestigious_unis = ["oxford", "cambridge", "imperial", "lse", "ucl", "edinburgh", "manchester", "warwick"]
        if any(uni in program.university_name.lower() for uni in prestigious_unis):
            reasons.append(f"World-class institution with global recognition - {program.university_name} degree opens doors worldwide")
        
        # Program duration and career readiness
        if program.duration_months:
            if program.duration_months <= 12:
                reasons.append(f"Efficient {program.duration_months}-month program - quick path to career advancement without extended time away from work")
            else:
                reasons.append(f"Comprehensive {program.duration_months//12}-year program - thorough preparation for leadership roles in your field")
        
        return reasons[:4]  # Limit to top 4 most relevant reasons
