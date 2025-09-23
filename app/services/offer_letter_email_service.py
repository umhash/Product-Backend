import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import io

import PyPDF2
import docx
import pytesseract
from PIL import Image
import tiktoken
from sqlalchemy.orm import Session
from app.services.llm_providers.factory import create_chat_and_embeddings

from app.models.application import Application, ApplicationDocument
from app.models.student import Student
from app.models.eligibility import UKProgram

logger = logging.getLogger(__name__)


class OfferLetterEmailService:
    """Service for generating offer letter request emails using LLM"""
    
    def __init__(self):
        # Initialize providers (env-driven; default OpenAI)
        self.chat_llm, _ = create_chat_and_embeddings()
        
        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Maximum tokens for context (leaving room for response)
        self.max_context_tokens = 3500
        
    def generate_offer_letter_email(
        self, 
        db: Session, 
        application: Application,
        admin_name: str = "Admissions Team"
    ) -> Dict[str, Any]:
        """Generate offer letter request email for an application"""
        
        try:
            # Extract application data
            student = application.student
            program = application.program
            
            if not student or not program:
                raise ValueError("Application must have associated student and program")
            
            # Process documents to get summaries
            document_summaries = self._process_application_documents(application)
            
            # Build the LLM prompt
            prompt = self._build_email_prompt(
                student=student,
                program=program,
                application=application,
                document_summaries=document_summaries,
                admin_name=admin_name
            )
            
            # Generate email using OpenAI
            start_time = datetime.utcnow()
            email_content = self._generate_email_with_llm(prompt)
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Count tokens used
            token_usage = len(self.tokenizer.encode(prompt))
            
            return {
                "email_draft": email_content,
                "documents_processed": [doc.document_type for doc in application.documents],
                "generation_time_seconds": generation_time,
                "token_usage": token_usage,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to generate offer letter email for application {application.id}: {str(e)}")
            return {
                "email_draft": None,
                "error": str(e),
                "success": False
            }
    
    def _process_application_documents(self, application: Application) -> List[Dict[str, str]]:
        """Process uploaded documents to extract content summaries"""
        
        document_summaries = []
        
        for doc in application.documents:
            try:
                # Skip certain document types that aren't relevant for offer letter requests
                if doc.document_type in ['offer_letter', 'cas_document', 'visa_document']:
                    continue
                
                summary = self._extract_document_content(doc)
                if summary:
                    document_summaries.append({
                        "type": doc.document_type,
                        "original_filename": doc.original_filename,
                        "content_summary": summary
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to process document {doc.id}: {str(e)}")
                # Add metadata-only summary if content extraction fails
                document_summaries.append({
                    "type": doc.document_type,
                    "original_filename": doc.original_filename,
                    "content_summary": f"Document uploaded: {doc.original_filename} ({doc.file_size} bytes)"
                })
        
        return document_summaries
    
    def _extract_document_content(self, document: ApplicationDocument) -> Optional[str]:
        """Extract text content from a document file"""
        
        try:
            file_path = Path(document.file_path)
            
            if not file_path.exists():
                return f"File not found: {document.original_filename}"
            
            # Determine file type and extract content
            if document.content_type == "application/pdf":
                return self._extract_pdf_content(file_path)
            elif document.content_type in [
                "application/msword", 
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]:
                return self._extract_docx_content(file_path)
            elif document.content_type.startswith("image/"):
                return self._extract_image_content(file_path)
            else:
                return f"Document type: {document.document_type} - {document.original_filename}"
                
        except Exception as e:
            logger.warning(f"Failed to extract content from {document.original_filename}: {str(e)}")
            return None
    
    def _extract_pdf_content(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract text from first few pages (limit for performance)
                max_pages = min(5, len(pdf_reader.pages))
                for page_num in range(max_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                # Summarize if too long
                return self._summarize_content(text, max_words=200)
                
        except Exception as e:
            logger.warning(f"Failed to extract PDF content from {file_path}: {str(e)}")
            return f"PDF document: {file_path.name}"
    
    def _extract_docx_content(self, file_path: Path) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            # Summarize if too long
            return self._summarize_content(text, max_words=200)
            
        except Exception as e:
            logger.warning(f"Failed to extract DOCX content from {file_path}: {str(e)}")
            return f"Word document: {file_path.name}"
    
    def _extract_image_content(self, file_path: Path) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            if text.strip():
                return self._summarize_content(text, max_words=150)
            else:
                return f"Image document: {file_path.name} (no text detected)"
                
        except Exception as e:
            logger.warning(f"Failed to extract image content from {file_path}: {str(e)}")
            return f"Image document: {file_path.name}"
    
    def _summarize_content(self, text: str, max_words: int = 200) -> str:
        """Summarize content if it's too long"""
        words = text.strip().split()
        
        if len(words) <= max_words:
            return text.strip()
        
        # Take first part and add summary indicator
        summarized = " ".join(words[:max_words])
        return f"{summarized}... [Content summarized - {len(words)} total words]"
    
    def _build_email_prompt(
        self,
        student: Student,
        program: UKProgram,
        application: Application,
        document_summaries: List[Dict[str, str]],
        admin_name: str
    ) -> str:
        """Build the prompt for LLM email generation"""
        
        # Build document summaries text
        documents_text = ""
        if document_summaries:
            documents_text = "\n".join([
                f"- {doc['type'].replace('_', ' ').title()}: {doc['content_summary']}"
                for doc in document_summaries
            ])
        else:
            documents_text = "No documents processed (documents may be pending or unavailable)"
        
        # Build personal statement text
        personal_statement = application.personal_statement or "Not provided"
        if len(personal_statement) > 500:
            personal_statement = personal_statement[:500] + "... [truncated]"
        
        # Build additional notes text
        additional_notes = application.additional_notes or "None"
        if len(additional_notes) > 300:
            additional_notes = additional_notes[:300] + "... [truncated]"
        
        prompt = f"""You are a professional university admissions consultant. Generate a formal, professional email to request an offer letter from a university on behalf of a student. The email should be comprehensive, persuasive, and follow business email standards.

UNIVERSITY & PROGRAM DETAILS:
- University: {program.university_name}
- Program: {program.program_name} ({program.program_level})
- Field of Study: {program.field_of_study}
- Location: {program.city}
- Duration: {program.duration_months or 'Not specified'} months
- Tuition Fee: £{program.tuition_fee_gbp or 'Not specified'}

STUDENT INFORMATION:
- Name: {student.full_name}
- Email: {student.email}
- Phone: {student.phone_number or 'Not provided'}
- Country of Origin: {student.country_of_origin or 'Not provided'}

STUDENT DOCUMENTS SUMMARY:
{documents_text}

STUDENT APPLICATION DETAILS:
Personal Statement: {personal_statement}

Additional Notes: {additional_notes}

REQUIREMENTS:
1. Create a professional business email with proper subject line
2. Use formal salutation appropriate for university admissions
3. Clearly state the purpose: requesting an offer letter
4. Highlight student's qualifications based on the provided information
5. Include all relevant student details for processing
6. Request specific items in the offer letter (program details, tuition, duration, start date, conditions)
7. Provide clear contact information for follow-up
8. Use professional closing
9. Keep the email concise but comprehensive (300-500 words)
10. Maintain a confident but respectful tone

Generate the complete email including subject line, salutation, body, and signature. The email should be ready to send to the university admissions office."""

        # Check token count and truncate if necessary
        token_count = len(self.tokenizer.encode(prompt))
        if token_count > self.max_context_tokens:
            # Truncate document summaries if prompt is too long
            truncated_docs = documents_text[:1000] + "... [Content truncated due to length]"
            prompt = prompt.replace(documents_text, truncated_docs)
        
        return prompt
    
    def _generate_email_with_llm(self, prompt: str) -> str:
        """Generate email content using configured LLM provider"""
        
        try:
            email_content = self.chat_llm.generate(
                messages=[
                    {"role": "system", "content": "You are a professional university admissions consultant who writes formal, persuasive emails to universities requesting offer letters for students."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                top_p=0.9,
            ).strip()
            
            # Basic validation
            if not email_content or len(email_content) < 100:
                raise ValueError("Generated email content is too short or empty")
            
            return email_content
            
        except Exception as e:
            logger.error(f"Failed to generate email with LLM: {str(e)}")
            raise Exception(f"LLM generation failed: {str(e)}")
    
    def save_email_draft(
        self, 
        db: Session, 
        application: Application, 
        email_content: str,
        is_edited_by_admin: bool = False
    ) -> bool:
        """Save email draft to database"""
        
        try:
            application.offer_letter_email_draft = email_content
            application.offer_letter_email_generated_at = datetime.utcnow()
            application.offer_letter_email_edited_by_admin = is_edited_by_admin
            
            db.commit()
            db.refresh(application)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save email draft for application {application.id}: {str(e)}")
            db.rollback()
            return False
