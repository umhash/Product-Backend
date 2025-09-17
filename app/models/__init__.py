# Import all models to ensure relationships are properly configured
from .student import Student
from .eligibility import EligibilityAssessment, UKProgram
from .chat import ChatSession, ChatMessage
from .user import User
from .program_document import ProgramDocument
from .rag import RAGDocument, RAGQuery
from .application import Application, ApplicationDocument, RequiredDocument, ApplicationInterviewDocument, ApplicationCASDocument, ApplicationVisaDocument
from .document_type import DocumentType

# Make models available at package level
__all__ = ["Student", "EligibilityAssessment", "UKProgram", "ChatSession", "ChatMessage", "User", "ProgramDocument", "RAGDocument", "RAGQuery", "Application", "ApplicationDocument", "RequiredDocument", "ApplicationInterviewDocument", "ApplicationCASDocument", "ApplicationVisaDocument", "DocumentType"]