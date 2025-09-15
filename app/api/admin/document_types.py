from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth_admin import require_admin_role
from app.models import User, DocumentType, RequiredDocument, UKProgram
from app.schemas.document_type import (
    DocumentTypeCreate, DocumentTypeUpdate, DocumentTypeResponse, 
    DocumentTypeListResponse, ProgramDocumentRequirementCreate,
    ProgramDocumentRequirementResponse
)

router = APIRouter(prefix="/admin/api/document-types", tags=["Admin - Document Types"])


@router.get("/", response_model=DocumentTypeListResponse)
async def get_document_types(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get all available document types"""
    
    document_types = db.query(DocumentType).order_by(DocumentType.name).all()
    
    return DocumentTypeListResponse(
        document_types=document_types,
        total=len(document_types)
    )


@router.post("/", response_model=DocumentTypeResponse)
async def create_document_type(
    document_type_data: DocumentTypeCreate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Create a new document type"""
    
    # Check if document type already exists
    existing = db.query(DocumentType).filter(
        DocumentType.name == document_type_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type with this name already exists"
        )
    
    document_type = DocumentType(**document_type_data.model_dump())
    db.add(document_type)
    db.commit()
    db.refresh(document_type)
    
    return document_type


@router.put("/{document_type_id}", response_model=DocumentTypeResponse)
async def update_document_type(
    document_type_id: int,
    update_data: DocumentTypeUpdate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Update a document type"""
    
    document_type = db.query(DocumentType).filter(
        DocumentType.id == document_type_id
    ).first()
    
    if not document_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found"
        )
    
    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(document_type, field, value)
    
    db.commit()
    db.refresh(document_type)
    
    return document_type


@router.delete("/{document_type_id}")
async def delete_document_type(
    document_type_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Delete a document type"""
    
    document_type = db.query(DocumentType).filter(
        DocumentType.id == document_type_id
    ).first()
    
    if not document_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document type not found"
        )
    
    # Check if document type is in use
    in_use = db.query(RequiredDocument).filter(
        RequiredDocument.document_type == document_type.name.lower().replace(' ', '_')
    ).first()
    
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete document type that is in use by programs"
        )
    
    db.delete(document_type)
    db.commit()
    
    return {"message": "Document type deleted successfully"}


@router.get("/program/{program_id}", response_model=ProgramDocumentRequirementResponse)
async def get_program_document_requirements(
    program_id: int,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get required documents for a specific program"""
    
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    required_docs = db.query(RequiredDocument).filter(
        RequiredDocument.program_id == program_id
    ).all()
    
    # Get document type information
    document_types = []
    for req_doc in required_docs:
        # Find matching document type by converting back from document_type field
        doc_type_name = req_doc.document_name
        doc_type = db.query(DocumentType).filter(
            DocumentType.name == doc_type_name
        ).first()
        
        if not doc_type:
            # Create document type if it doesn't exist
            doc_type = DocumentType(
                name=doc_type_name,
                description=req_doc.description,
                is_common=req_doc.is_required
            )
            db.add(doc_type)
            db.commit()
            db.refresh(doc_type)
        
        document_types.append(doc_type)
    
    return ProgramDocumentRequirementResponse(
        program_id=program_id,
        required_documents=document_types
    )


@router.post("/program/{program_id}/requirements")
async def update_program_document_requirements(
    program_id: int,
    requirements_data: ProgramDocumentRequirementCreate,
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Update required documents for a program"""
    
    program = db.query(UKProgram).filter(UKProgram.id == program_id).first()
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    # Delete existing requirements
    db.query(RequiredDocument).filter(
        RequiredDocument.program_id == program_id
    ).delete()
    
    # Add new requirements
    for doc_type_id in requirements_data.document_type_ids:
        doc_type = db.query(DocumentType).filter(
            DocumentType.id == doc_type_id
        ).first()
        
        if doc_type:
            required_doc = RequiredDocument(
                program_id=program_id,
                document_type=doc_type.name.lower().replace(' ', '_'),
                document_name=doc_type.name,
                description=doc_type.description,
                is_required=True
            )
            db.add(required_doc)
    
    db.commit()
    
    return {"message": "Program document requirements updated successfully"}


# Seed default document types
@router.post("/seed")
async def seed_document_types(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Seed default document types"""
    
    default_types = [
        {
            "name": "Academic Transcript",
            "description": "Official academic transcript from your previous institution",
            "is_common": True
        },
        {
            "name": "Personal Statement",
            "description": "A personal statement explaining your motivation and goals",
            "is_common": True
        },
        {
            "name": "English Language Certificate",
            "description": "IELTS, TOEFL, or PTE certificate proving English proficiency",
            "is_common": True
        },
        {
            "name": "Passport Copy",
            "description": "Clear copy of your passport bio page",
            "is_common": True
        },
        {
            "name": "Letter of Recommendation",
            "description": "Academic or professional reference letter",
            "is_common": True
        },
        {
            "name": "CV/Resume",
            "description": "Current curriculum vitae or resume",
            "is_common": True
        },
        {
            "name": "Financial Statement",
            "description": "Bank statements or financial guarantee letter",
            "is_common": True
        },
        {
            "name": "Degree Certificate",
            "description": "Copy of your degree certificate (if graduated)",
            "is_common": False
        },
        {
            "name": "Portfolio",
            "description": "Portfolio of work (for creative programs)",
            "is_common": False
        },
        {
            "name": "Research Proposal",
            "description": "Detailed research proposal (for research programs)",
            "is_common": False
        },
        {
            "name": "Work Experience Letter",
            "description": "Letter from employer detailing work experience",
            "is_common": False
        }
    ]
    
    created_count = 0
    for doc_type_data in default_types:
        existing = db.query(DocumentType).filter(
            DocumentType.name == doc_type_data["name"]
        ).first()
        
        if not existing:
            doc_type = DocumentType(**doc_type_data)
            db.add(doc_type)
            created_count += 1
    
    db.commit()
    
    return {"message": f"Created {created_count} document types"}
