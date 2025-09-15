#!/usr/bin/env python3
"""
Seed UK Programs data for the eligibility checker
This script adds sample UK university programs to the database
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import UKProgram

# Sample UK Programs Data
SAMPLE_PROGRAMS = [
    {
        "university_name": "University of Oxford",
        "program_name": "MSc Computer Science",
        "program_level": "postgraduate",
        "field_of_study": "Computer Science",
        "city": "Oxford",
        "min_ielts_overall": 7.5,
        "min_ielts_components": 7.0,
        "min_toefl_overall": 110,
        "min_pte_overall": 76,
        "min_gpa_4_scale": 3.7,
        "min_percentage": 85,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 29700,
        "living_cost_gbp": 15000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Advanced computer science program covering AI, machine learning, and software engineering."
    },
    {
        "university_name": "University of Cambridge",
        "program_name": "MPhil Management",
        "program_level": "postgraduate",
        "field_of_study": "Business Management",
        "city": "Cambridge",
        "min_ielts_overall": 7.5,
        "min_ielts_components": 7.0,
        "min_toefl_overall": 110,
        "min_pte_overall": 76,
        "min_gpa_4_scale": 3.8,
        "min_percentage": 87,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 31500,
        "living_cost_gbp": 15500,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Comprehensive management program with focus on strategy and leadership."
    },
    {
        "university_name": "Imperial College London",
        "program_name": "MSc Data Science",
        "program_level": "postgraduate",
        "field_of_study": "Data Science",
        "city": "London",
        "min_ielts_overall": 7.0,
        "min_ielts_components": 6.5,
        "min_toefl_overall": 100,
        "min_pte_overall": 69,
        "min_gpa_4_scale": 3.5,
        "min_percentage": 80,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 35900,
        "living_cost_gbp": 18000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Cutting-edge data science program with industry partnerships."
    },
    {
        "university_name": "London School of Economics",
        "program_name": "MSc Economics",
        "program_level": "postgraduate",
        "field_of_study": "Economics",
        "city": "London",
        "min_ielts_overall": 7.0,
        "min_ielts_components": 6.5,
        "min_toefl_overall": 100,
        "min_pte_overall": 69,
        "min_gpa_4_scale": 3.6,
        "min_percentage": 82,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 32208,
        "living_cost_gbp": 18000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "World-renowned economics program with focus on policy and research."
    },
    {
        "university_name": "University College London",
        "program_name": "MSc Engineering",
        "program_level": "postgraduate",
        "field_of_study": "Engineering",
        "city": "London",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 92,
        "min_pte_overall": 62,
        "min_gpa_4_scale": 3.3,
        "min_percentage": 75,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 31200,
        "living_cost_gbp": 17000,
        "duration_months": 12,
        "intake_months": [9, 1],
        "program_description": "Comprehensive engineering program with multiple specializations."
    },
    {
        "university_name": "University of Edinburgh",
        "program_name": "MSc Artificial Intelligence",
        "program_level": "postgraduate",
        "field_of_study": "Artificial Intelligence",
        "city": "Edinburgh",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 92,
        "min_pte_overall": 62,
        "min_gpa_4_scale": 3.4,
        "min_percentage": 77,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 34200,
        "living_cost_gbp": 12000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Leading AI program with research opportunities and industry connections."
    },
    {
        "university_name": "King's College London",
        "program_name": "MSc Digital Marketing",
        "program_level": "postgraduate",
        "field_of_study": "Marketing",
        "city": "London",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 92,
        "min_pte_overall": 62,
        "min_gpa_4_scale": 3.2,
        "min_percentage": 70,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 28350,
        "living_cost_gbp": 17000,
        "duration_months": 12,
        "intake_months": [9, 1],
        "program_description": "Modern marketing program focusing on digital strategies and analytics."
    },
    {
        "university_name": "University of Manchester",
        "program_name": "MSc Finance",
        "program_level": "postgraduate",
        "field_of_study": "Finance",
        "city": "Manchester",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 90,
        "min_pte_overall": 59,
        "min_gpa_4_scale": 3.3,
        "min_percentage": 75,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 26000,
        "living_cost_gbp": 11000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Comprehensive finance program with strong industry links."
    },
    {
        "university_name": "University of Warwick",
        "program_name": "BSc Computer Science",
        "program_level": "undergraduate",
        "field_of_study": "Computer Science",
        "city": "Coventry",
        "min_ielts_overall": 6.0,
        "min_ielts_components": 5.5,
        "min_toefl_overall": 87,
        "min_pte_overall": 57,
        "min_gpa_4_scale": 3.0,
        "min_percentage": 70,
        "required_qualification": "high_school",
        "tuition_fee_gbp": 25770,
        "living_cost_gbp": 10000,
        "duration_months": 36,
        "intake_months": [9],
        "program_description": "Undergraduate computer science with strong theoretical foundation."
    },
    {
        "university_name": "University of Bristol",
        "program_name": "BSc Business Management",
        "program_level": "undergraduate",
        "field_of_study": "Business Management",
        "city": "Bristol",
        "min_ielts_overall": 6.0,
        "min_ielts_components": 5.5,
        "min_toefl_overall": 87,
        "min_pte_overall": 57,
        "min_gpa_4_scale": 3.0,
        "min_percentage": 70,
        "required_qualification": "high_school",
        "tuition_fee_gbp": 24700,
        "living_cost_gbp": 11500,
        "duration_months": 36,
        "intake_months": [9],
        "program_description": "Comprehensive business management undergraduate program."
    },
    # Additional programs for better variety
    {
        "university_name": "University of Glasgow",
        "program_name": "MSc Computer Science",
        "program_level": "postgraduate",
        "field_of_study": "Computer Science",
        "city": "Glasgow",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 90,
        "min_pte_overall": 60,
        "min_gpa_4_scale": 3.2,
        "min_percentage": 72,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 25750,
        "living_cost_gbp": 10500,
        "duration_months": 12,
        "intake_months": [9, 1],
        "program_description": "Innovative computer science program with strong industry connections in Scotland."
    },
    {
        "university_name": "University of Birmingham",
        "program_name": "MSc Data Science",
        "program_level": "postgraduate",
        "field_of_study": "Data Science",
        "city": "Birmingham",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 88,
        "min_pte_overall": 59,
        "min_gpa_4_scale": 3.3,
        "min_percentage": 75,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 27540,
        "living_cost_gbp": 12000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Comprehensive data science program with practical industry applications."
    },
    {
        "university_name": "University of Leeds",
        "program_name": "MSc Business Management",
        "program_level": "postgraduate",
        "field_of_study": "Business Management",
        "city": "Leeds",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 92,
        "min_pte_overall": 62,
        "min_gpa_4_scale": 3.2,
        "min_percentage": 70,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 24500,
        "living_cost_gbp": 11000,
        "duration_months": 12,
        "intake_months": [9, 1],
        "program_description": "Dynamic business management program with strong career support."
    },
    {
        "university_name": "University of Sheffield",
        "program_name": "MSc Engineering",
        "program_level": "postgraduate",
        "field_of_study": "Engineering",
        "city": "Sheffield",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 88,
        "min_pte_overall": 59,
        "min_gpa_4_scale": 3.1,
        "min_percentage": 68,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 26950,
        "living_cost_gbp": 10000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Excellent engineering program with state-of-the-art facilities."
    },
    {
        "university_name": "Queen Mary University of London",
        "program_name": "MSc Artificial Intelligence",
        "program_level": "postgraduate",
        "field_of_study": "Artificial Intelligence",
        "city": "London",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 92,
        "min_pte_overall": 62,
        "min_gpa_4_scale": 3.3,
        "min_percentage": 75,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 29000,
        "living_cost_gbp": 17000,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Cutting-edge AI program in the heart of London's tech scene."
    },
    {
        "university_name": "University of Nottingham",
        "program_name": "MSc Finance",
        "program_level": "postgraduate",
        "field_of_study": "Finance",
        "city": "Nottingham",
        "min_ielts_overall": 6.5,
        "min_ielts_components": 6.0,
        "min_toefl_overall": 87,
        "min_pte_overall": 58,
        "min_gpa_4_scale": 3.2,
        "min_percentage": 72,
        "required_qualification": "bachelor",
        "tuition_fee_gbp": 22000,
        "living_cost_gbp": 9500,
        "duration_months": 12,
        "intake_months": [9],
        "program_description": "Comprehensive finance program with excellent value for money."
    }
]

def seed_programs():
    """Seed the database with sample UK programs"""
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if programs already exist
        existing_count = db.query(UKProgram).count()
        if existing_count > 0:
            print(f"✅ Database already has {existing_count} programs. Skipping seed.")
            return
        
        print("🌱 Seeding UK Programs database...")
        
        # Add sample programs
        for program_data in SAMPLE_PROGRAMS:
            program = UKProgram(**program_data)
            db.add(program)
        
        db.commit()
        
        # Verify
        total_programs = db.query(UKProgram).count()
        print(f"✅ Successfully seeded {total_programs} UK programs!")
        
        # Show summary by field
        from sqlalchemy import func
        summary = db.query(
            UKProgram.field_of_study,
            func.count(UKProgram.id).label('count')
        ).group_by(UKProgram.field_of_study).all()
        
        print("\n📊 Programs by field:")
        for field, count in summary:
            print(f"   {field}: {count} programs")
            
    except Exception as e:
        print(f"❌ Error seeding programs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_programs()
