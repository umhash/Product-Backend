from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Additional student-specific fields
    phone_number = Column(String, nullable=True)
    country_of_origin = Column(String, nullable=True)
    preferred_universities = Column(String, nullable=True)  # JSON string for now
    academic_level = Column(String, nullable=True)  # undergraduate, postgraduate, etc.
    
    # Relationships
    eligibility_assessments = relationship("EligibilityAssessment", back_populates="student")
    chat_sessions = relationship("ChatSession", back_populates="student", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="student", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Student(id={self.id}, email='{self.email}', full_name='{self.full_name}')>"
