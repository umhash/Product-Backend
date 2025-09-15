import os
import asyncio
import time
import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import tiktoken
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# PDF processing
import PyPDF2
import re

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

# OpenAI for embeddings
from openai import OpenAI

# Local imports
from app.models.rag import RAGDocument, RAGChunk, RAGQuery
from app.models.program_document import ProgramDocument
from app.schemas.rag import (
    RAGProcessingStatus, ChunkType, RAGQueryRequest, RAGQueryResponse,
    RAGChunkWithSimilarity, RAGProcessingResponse
)


class SimpleRAGService:
    def __init__(self):
        # Initialize OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your-openai-api-key-here":
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=self.api_key)
        
        # Initialize Qdrant client
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Collection name for embeddings
        self.collection_name = "university_documents"
        
        # Initialize collection if it doesn't exist
        self._initialize_qdrant_collection()
        
        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
    def _initialize_qdrant_collection(self):
        """Initialize Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=3072,  # text-embedding-3-large dimension
                        distance=Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            print(f"Warning: Could not initialize Qdrant collection: {e}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.tokenizer.encode(text))
    
    def extract_pdf_content(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract content from PDF using PyPDF2"""
        try:
            elements = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    
                    if text.strip():
                        # Clean up text
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        # Split into paragraphs
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        
                        for para in paragraphs:
                            if len(para) > 50:  # Only include substantial paragraphs
                                elements.append({
                                    'text': para,
                                    'page_number': page_num,
                                    'type': 'text'
                                })
            
            return elements
        except Exception as e:
            raise Exception(f"Failed to extract PDF content: {str(e)}")
    
    def chunk_text(self, text: str, chunk_size: int = 1024, chunk_overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            if end >= len(tokens):
                break
                
            start = end - chunk_overlap
        
        return chunks
    
    def process_elements_to_chunks(
        self, 
        elements: List[Dict[str, Any]], 
        chunk_size: int = 1024, 
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Process extracted elements into chunks with metadata"""
        chunks = []
        current_section = None
        
        for element in elements:
            text = element['text']
            page_number = element['page_number']
            
            # Check if this looks like a title/header
            if len(text) < 200 and text.isupper() or text.count('.') < 2:
                current_section = text[:100]  # Use as section title
                chunk_type = ChunkType.HEADER
            else:
                chunk_type = ChunkType.TEXT
            
            # Split into chunks if text is too long
            if self.count_tokens(text) > chunk_size:
                sub_chunks = self.chunk_text(text, chunk_size, chunk_overlap)
                for i, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        'content': sub_chunk,
                        'page_number': page_number,
                        'section_title': current_section,
                        'chunk_type': chunk_type.value,
                        'chunk_metadata': {
                            'element_type': 'text',
                            'part': i + 1,
                            'total_parts': len(sub_chunks)
                        }
                    })
            else:
                chunks.append({
                    'content': text,
                    'page_number': page_number,
                    'section_title': current_section,
                    'chunk_type': chunk_type.value,
                    'chunk_metadata': {
                        'element_type': 'text'
                    }
                })
        
        return chunks
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def process_document(
        self, 
        db: Session, 
        program_document_id: int,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        force_reprocess: bool = False
    ) -> RAGProcessingResponse:
        """Process a document for RAG pipeline"""
        
        # Check if document exists
        program_doc = db.query(ProgramDocument).filter(
            ProgramDocument.id == program_document_id
        ).first()
        
        if not program_doc:
            raise ValueError("Program document not found")
        
        # Check if already processed
        existing_rag_doc = db.query(RAGDocument).filter(
            RAGDocument.program_document_id == program_document_id
        ).first()
        
        if existing_rag_doc and not force_reprocess:
            if existing_rag_doc.status == RAGProcessingStatus.COMPLETED:
                return RAGProcessingResponse(
                    rag_document_id=existing_rag_doc.id,
                    status=RAGProcessingStatus.COMPLETED,
                    message="Document already processed"
                )
            elif existing_rag_doc.status == RAGProcessingStatus.PROCESSING:
                return RAGProcessingResponse(
                    rag_document_id=existing_rag_doc.id,
                    status=RAGProcessingStatus.PROCESSING,
                    message="Document is currently being processed"
                )
        
        # Create or update RAG document record
        if existing_rag_doc and force_reprocess:
            rag_doc = existing_rag_doc
            # Delete existing chunks
            db.query(RAGChunk).filter(RAGChunk.rag_document_id == rag_doc.id).delete()
        else:
            rag_doc = RAGDocument(
                program_document_id=program_document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            db.add(rag_doc)
        
        # Update status to processing
        rag_doc.status = RAGProcessingStatus.PROCESSING
        rag_doc.processing_started_at = db.execute("SELECT NOW()").scalar()
        rag_doc.error_message = None
        db.commit()
        db.refresh(rag_doc)
        
        try:
            # Extract content from PDF
            elements = self.extract_pdf_content(program_doc.file_path)
            
            # Process elements into chunks
            chunks_data = self.process_elements_to_chunks(
                elements, chunk_size, chunk_overlap
            )
            
            # Generate embeddings and store chunks
            total_tokens = 0
            stored_chunks = []
            
            for i, chunk_data in enumerate(chunks_data):
                content = chunk_data['content']
                token_count = self.count_tokens(content)
                total_tokens += token_count
                
                # Generate embedding
                embedding = await self.generate_embedding(content)
                
                # Create chunk record
                chunk = RAGChunk(
                    rag_document_id=rag_doc.id,
                    content=content,
                    chunk_index=i,
                    token_count=token_count,
                    page_number=chunk_data.get('page_number'),
                    section_title=chunk_data.get('section_title'),
                    embedding_vector=embedding,
                    embedding_model="text-embedding-3-large",
                    chunk_type=chunk_data.get('chunk_type', ChunkType.TEXT.value),
                    chunk_metadata=chunk_data.get('chunk_metadata')
                )
                
                db.add(chunk)
                stored_chunks.append(chunk)
            
            # Commit chunks to database
            db.commit()
            
            # Store embeddings in Qdrant
            points = []
            for chunk in stored_chunks:
                points.append(PointStruct(
                    id=chunk.id,
                    vector=chunk.embedding_vector,
                    payload={
                        "content": chunk.content,
                        "program_document_id": program_document_id,
                        "program_id": program_doc.program_id,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title,
                        "chunk_type": chunk.chunk_type,
                        "token_count": chunk.token_count
                    }
                ))
            
            # Batch insert to Qdrant
            if points:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            
            # Update RAG document status
            rag_doc.status = RAGProcessingStatus.COMPLETED
            rag_doc.processing_completed_at = db.execute("SELECT NOW()").scalar()
            rag_doc.total_chunks = len(stored_chunks)
            rag_doc.total_tokens = total_tokens
            db.commit()
            
            return RAGProcessingResponse(
                rag_document_id=rag_doc.id,
                status=RAGProcessingStatus.COMPLETED,
                message=f"Document processed successfully. Created {len(stored_chunks)} chunks with {total_tokens} tokens."
            )
            
        except Exception as e:
            # Update status to failed
            rag_doc.status = RAGProcessingStatus.FAILED
            rag_doc.error_message = str(e)
            db.commit()
            
            return RAGProcessingResponse(
                rag_document_id=rag_doc.id,
                status=RAGProcessingStatus.FAILED,
                message=f"Document processing failed: {str(e)}"
            )
    
    async def query_documents(
        self, 
        db: Session,
        query_request: RAGQueryRequest,
        student_id: Optional[int] = None,
        chat_session_id: Optional[int] = None
    ) -> RAGQueryResponse:
        """Query documents using RAG pipeline"""
        
        start_time = time.time()
        
        # Generate query embedding
        embedding_start = time.time()
        query_embedding = await self.generate_embedding(query_request.query)
        embedding_time = (time.time() - embedding_start) * 1000
        
        # Search in Qdrant
        retrieval_start = time.time()
        
        # Build filter for specific programs if provided
        query_filter = None
        if query_request.program_ids:
            query_filter = {
                "must": [
                    {
                        "key": "program_id",
                        "match": {"any": query_request.program_ids}
                    }
                ]
            }
        
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=query_request.max_chunks,
            score_threshold=query_request.similarity_threshold
        )
        
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Get chunk details from database
        chunk_ids = [result.id for result in search_results]
        chunks = db.query(RAGChunk).filter(RAGChunk.id.in_(chunk_ids)).all() if chunk_ids else []
        
        # Create response with similarity scores
        chunks_with_similarity = []
        score_map = {result.id: result.score for result in search_results}
        
        for chunk in chunks:
            chunk_response = RAGChunkWithSimilarity(
                id=chunk.id,
                rag_document_id=chunk.rag_document_id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                chunk_type=chunk.chunk_type,
                chunk_metadata=chunk.chunk_metadata,
                embedding_model=chunk.embedding_model,
                created_at=chunk.created_at,
                similarity_score=score_map.get(chunk.id, 0.0)
            )
            chunks_with_similarity.append(chunk_response)
        
        # Sort by similarity score (descending)
        chunks_with_similarity.sort(key=lambda x: x.similarity_score, reverse=True)
        
        total_time = (time.time() - start_time) * 1000
        
        # Log query for analytics
        if student_id or chat_session_id:
            query_log = RAGQuery(
                student_id=student_id,
                chat_session_id=chat_session_id,
                query_text=query_request.query,
                query_embedding=query_embedding,
                retrieved_chunks=[{"chunk_id": chunk.id, "score": chunk.similarity_score} for chunk in chunks_with_similarity],
                total_retrieved=len(chunks_with_similarity),
                max_similarity_score=chunks_with_similarity[0].similarity_score if chunks_with_similarity else 0.0,
                embedding_time_ms=embedding_time,
                retrieval_time_ms=retrieval_time,
                total_time_ms=total_time
            )
            db.add(query_log)
            db.commit()
        
        return RAGQueryResponse(
            query=query_request.query,
            chunks=chunks_with_similarity,
            total_retrieved=len(chunks_with_similarity),
            embedding_time_ms=embedding_time,
            retrieval_time_ms=retrieval_time,
            total_time_ms=total_time
        )
    
    def get_processing_status(self, db: Session) -> Dict[str, Any]:
        """Get overall RAG processing status"""
        from sqlalchemy import func
        
        status_counts = db.query(
            RAGDocument.status,
            func.count(RAGDocument.id).label('count')
        ).group_by(RAGDocument.status).all()
        
        status_dict = {status: count for status, count in status_counts}
        
        total_chunks = db.query(func.sum(RAGDocument.total_chunks)).scalar() or 0
        total_tokens = db.query(func.sum(RAGDocument.total_tokens)).scalar() or 0
        total_documents = db.query(func.count(RAGDocument.id)).scalar() or 0
        
        return {
            "total_documents": total_documents,
            "pending_documents": status_dict.get(RAGProcessingStatus.PENDING, 0),
            "processing_documents": status_dict.get(RAGProcessingStatus.PROCESSING, 0),
            "completed_documents": status_dict.get(RAGProcessingStatus.COMPLETED, 0),
            "failed_documents": status_dict.get(RAGProcessingStatus.FAILED, 0),
            "total_chunks": total_chunks,
            "total_tokens": total_tokens
        }
    
    def delete_document_embeddings(self, db: Session, rag_document_id: int) -> bool:
        """Delete document embeddings from Qdrant"""
        try:
            # Get chunk IDs to delete from Qdrant
            chunks = db.query(RAGChunk).filter(
                RAGChunk.rag_document_id == rag_document_id
            ).all()
            
            chunk_ids = [chunk.id for chunk in chunks]
            
            if chunk_ids:
                # Delete from Qdrant
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=chunk_ids
                )
            
            return True
        except Exception as e:
            print(f"Error deleting embeddings from Qdrant: {e}")
            return False


# Global RAG service instance
try:
    rag_service = SimpleRAGService()
except Exception as e:
    rag_service = None
    print(f"Warning: RAG service not initialized - {str(e)}")


# For backward compatibility
RAGService = SimpleRAGService
