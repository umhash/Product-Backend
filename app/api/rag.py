from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math

from app.database import get_db
from app.models import Student, RAGDocument, ProgramDocument
from app.schemas.rag import (
    RAGProcessingRequest, RAGProcessingResponse, RAGQueryRequest, RAGQueryResponse,
    RAGDocumentResponse, RAGDocumentListResponse, RAGStatusResponse
)
from app.services.rag_service import rag_service
from app.auth import get_current_user
from app.auth_admin import require_admin_role
from app.models import User

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/process", response_model=RAGProcessingResponse)
async def process_document(
    request: RAGProcessingRequest,
    background_tasks: BackgroundTasks,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a document for RAG pipeline"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    # Check if document exists and user has access
    program_doc = db.query(ProgramDocument).filter(
        ProgramDocument.id == request.program_document_id
    ).first()
    
    if not program_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program document not found"
        )
    
    try:
        # Process document
        response = await rag_service.process_document(
            db=db,
            program_document_id=request.program_document_id,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            force_reprocess=request.force_reprocess
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Query documents using hybrid search"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    try:
        response = await rag_service.hybrid_search(
            db=db,
            query_request=request,
            student_id=current_user.id
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query documents: {str(e)}"
        )


@router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status(
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get RAG processing status overview"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    try:
        status_data = rag_service.get_processing_status(db)
        return RAGStatusResponse(**status_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG status: {str(e)}"
        )


@router.get("/documents", response_model=RAGDocumentListResponse)
async def get_rag_documents(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by processing status"),
    current_user: User = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get paginated list of RAG documents"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    try:
        # Build query
        query = db.query(RAGDocument)
        
        # Apply status filter
        if status_filter:
            query = query.filter(RAGDocument.status == status_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        documents = query.offset(offset).limit(per_page).all()
        
        # Convert to response models
        document_responses = [
            RAGDocumentResponse.model_validate(doc) for doc in documents
        ]
        
        # Calculate pagination info
        pages = math.ceil(total / per_page)
        
        return RAGDocumentListResponse(
            documents=document_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG documents: {str(e)}"
        )


@router.get("/documents/{rag_document_id}", response_model=RAGDocumentResponse)
async def get_rag_document(
    rag_document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific RAG document details"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    document = db.query(RAGDocument).filter(
        RAGDocument.id == rag_document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAG document not found"
        )
    
    return RAGDocumentResponse.model_validate(document)


@router.delete("/documents/{rag_document_id}")
async def delete_rag_document(
    rag_document_id: int,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete RAG document and its embeddings"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    document = db.query(RAGDocument).filter(
        RAGDocument.id == rag_document_id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RAG document not found"
        )
    
    try:
        # Delete embeddings from Qdrant
        embeddings_deleted = await rag_service.delete_document_embeddings(db, rag_document_id)
        
        # Delete from database (cascades to chunks)
        db.delete(document)
        db.commit()
        
        return {
            "message": "RAG document deleted successfully",
            "embeddings_deleted": embeddings_deleted
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete RAG document: {str(e)}"
        )


# Admin endpoints
admin_router = APIRouter(prefix="/admin/api/rag", tags=["Admin - RAG"])


@admin_router.post("/process-batch")
async def process_documents_batch(
    program_ids: List[int],
    background_tasks: BackgroundTasks,
    chunk_size: int = Query(1024, ge=256, le=2048),
    chunk_overlap: int = Query(200, ge=0, le=512),
    force_reprocess: bool = Query(False),
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Process multiple documents in batch (Admin only)"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    # Get all documents for the specified programs
    documents = db.query(ProgramDocument).filter(
        ProgramDocument.program_id.in_(program_ids)
    ).all()
    
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents found for specified programs"
        )
    
    # Process each document
    results = []
    for doc in documents:
        try:
            response = await rag_service.process_document(
                db=db,
                program_document_id=doc.id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                force_reprocess=force_reprocess
            )
            results.append({
                "document_id": doc.id,
                "filename": doc.original_filename,
                "status": response.status,
                "message": response.message
            })
        except Exception as e:
            results.append({
                "document_id": doc.id,
                "filename": doc.original_filename,
                "status": "failed",
                "message": f"Error: {str(e)}"
            })
    
    return {
        "message": f"Batch processing completed for {len(documents)} documents",
        "results": results
    }


@admin_router.get("/analytics")
async def get_rag_analytics(
    current_user = Depends(require_admin_role),
    db: Session = Depends(get_db)
):
    """Get RAG analytics and usage statistics (Admin only)"""
    if rag_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is not available. Please check configuration."
        )
    
    try:
        from sqlalchemy import func
        from app.models.rag import RAGQuery
        
        # Get processing status
        status_data = rag_service.get_processing_status(db)
        
        # Get query statistics
        total_queries = db.query(func.count(RAGQuery.id)).scalar() or 0
        avg_retrieval_time = db.query(func.avg(RAGQuery.retrieval_time_ms)).scalar() or 0
        avg_similarity_score = db.query(func.avg(RAGQuery.max_similarity_score)).scalar() or 0
        
        # Get top queried chunks
        top_chunks = db.query(
            RAGQuery.retrieved_chunks,
            func.count(RAGQuery.id).label('query_count')
        ).group_by(RAGQuery.retrieved_chunks).limit(10).all()
        
        return {
            "processing_status": status_data,
            "query_analytics": {
                "total_queries": total_queries,
                "average_retrieval_time_ms": float(avg_retrieval_time) if avg_retrieval_time else 0,
                "average_similarity_score": float(avg_similarity_score) if avg_similarity_score else 0
            },
            "performance_metrics": {
                "top_chunks": [{"chunks": chunk[0], "count": chunk[1]} for chunk in top_chunks]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG analytics: {str(e)}"
        )


# Include admin router
router.include_router(admin_router)
