from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Student
from app.schemas.student import StudentCreate, StudentResponse, StudentLogin, Token
from app.auth import get_password_hash, authenticate_student, create_access_token, get_current_user
from datetime import timedelta
import os

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(student_data: StudentCreate, db: Session = Depends(get_db)):
    """Register a new student"""
    
    # Check if student already exists
    existing_student = db.query(Student).filter(Student.email == student_data.email).first()
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new student
    hashed_password = get_password_hash(student_data.password)
    db_student = Student(
        full_name=student_data.full_name,
        email=student_data.email,
        hashed_password=hashed_password
    )
    
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_student.email}, 
        expires_delta=access_token_expires
    )
    
    # Convert to response model
    student_response = StudentResponse.model_validate(db_student)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=student_response
    )


@router.post("/login", response_model=Token)
async def login(login_data: StudentLogin, db: Session = Depends(get_db)):
    """Authenticate and login a student"""
    
    # Authenticate student
    student = authenticate_student(db, login_data.email, login_data.password)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if student is active
    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive account"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": student.email}, 
        expires_delta=access_token_expires
    )
    
    # Convert to response model
    student_response = StudentResponse.model_validate(student)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=student_response
    )


@router.get("/me", response_model=StudentResponse)
async def get_current_user_info(current_user: Student = Depends(get_current_user)):
    """Get current authenticated user information"""
    return StudentResponse.model_validate(current_user)
