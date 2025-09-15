import os
import asyncio
import time
import json
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import tiktoken
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# LlamaIndex imports
from llama_index.core import Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import TitleExtractor
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext

# Unstructured imports
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Element, Table, Title, Text

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

# Local imports
from app.models.rag import RAGDocument, RAGChunk, RAGQuery
from app.models.program_document import ProgramDocument
from app.schemas.rag import (
    RAGProcessingStatus, ChunkType, RAGQueryRequest, RAGQueryResponse,
    RAGChunkWithSimilarity, RAGProcessingResponse
)


class RAGService:
    def __init__(self):
        # Initialize OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your-openai-api-key-here":
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize embedding model
        self.embedding_model = OpenAIEmbedding(
            model="text-embedding-3-large",
            api_key=self.api_key
        )
        
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
        
        # Configure LlamaIndex settings
        Settings.embed_model = self.embedding_model
        
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
    
    def extract_pdf_content(self, file_path: str) -> List[Element]:
        """Extract content from PDF using Unstructured"""
        try:
            elements = partition_pdf(
                filename=file_path,
                strategy="hi_res",  # High resolution for better table extraction
                infer_table_structure=True,
                model_name="yolox",  # For table detection
                extract_images_in_pdf=False,
                chunking_strategy="by_title",
                max_characters=2000,
                combine_text_under_n_chars=500,
            )
            return elements
        except Exception as e:
            raise Exception(f"Failed to extract PDF content: {str(e)}")
    
    def process_elements_to_chunks(
        self, 
        elements: List[Element], 
        chunk_size: int = 1024, 
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Process extracted elements into chunks with metadata"""
        chunks = []
        current_page = 1
        current_section = None
        
        # Initialize sentence splitter for text elements
        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        for element in elements:
            # Extract metadata
            page_number = getattr(element.metadata, 'page_number', current_page)
            if page_number:
                current_page = page_number
            
            # Handle different element types
            if isinstance(element, Title):
                current_section = element.text
                chunk_type = ChunkType.HEADER
                content = element.text
                
                # Don't split titles, keep as single chunks
                chunks.append({
                    'content': content,
                    'page_number': page_number,
                    'section_title': current_section,
                    'chunk_type': chunk_type.value,
                    'chunk_metadata': {
                        'element_type': 'title',
                        'coordinates': getattr(element.metadata, 'coordinates', None)
                    }
                })
                
            elif isinstance(element, Table):
                chunk_type = ChunkType.TABLE
                # Convert table to markdown format
                content = self._table_to_markdown(element)
                
                # Split large tables if needed
                if self.count_tokens(content) > chunk_size:
                    sub_chunks = splitter.split_text(content)
                    for i, sub_chunk in enumerate(sub_chunks):
                        chunks.append({
                            'content': sub_chunk,
                            'page_number': page_number,
                            'section_title': current_section,
                            'chunk_type': chunk_type.value,
                            'chunk_metadata': {
                                'element_type': 'table',
                                'table_part': i + 1,
                                'total_parts': len(sub_chunks),
                                'coordinates': getattr(element.metadata, 'coordinates', None)
                            }
                        })
                else:
                    chunks.append({
                        'content': content,
                        'page_number': page_number,
                        'section_title': current_section,
                        'chunk_type': chunk_type.value,
                        'chunk_metadata': {
                            'element_type': 'table',
                            'coordinates': getattr(element.metadata, 'coordinates', None)
                        }
                    })
                    
            elif isinstance(element, Text):
                chunk_type = ChunkType.TEXT
                content = element.text
                
                # Split text into smaller chunks
                if self.count_tokens(content) > chunk_size:
                    sub_chunks = splitter.split_text(content)
                    for i, sub_chunk in enumerate(sub_chunks):
                        chunks.append({
                            'content': sub_chunk,
                            'page_number': page_number,
                            'section_title': current_section,
                            'chunk_type': chunk_type.value,
                            'chunk_metadata': {
                                'element_type': 'text',
                                'text_part': i + 1,
                                'total_parts': len(sub_chunks),
                                'coordinates': getattr(element.metadata, 'coordinates', None)
                            }
                        })
                else:
                    chunks.append({
                        'content': content,
                        'page_number': page_number,
                        'section_title': current_section,
                        'chunk_type': chunk_type.value,
                        'chunk_metadata': {
                            'element_type': 'text',
                            'coordinates': getattr(element.metadata, 'coordinates', None)
                        }
                    })
        
        return chunks
    
    def _table_to_markdown(self, table_element: Table) -> str:
        """Convert table element to markdown format"""
        try:
            # Try to get table as HTML first
            if hasattr(table_element, 'metadata') and hasattr(table_element.metadata, 'text_as_html'):
                html_content = table_element.metadata.text_as_html
                # Simple HTML to markdown conversion for tables
                # This is a basic implementation - could be enhanced
                return f"**Table:**\n\n{table_element.text}\n\n"
            else:
                return f"**Table:**\n\n{table_element.text}\n\n"
        except Exception:
            return f"**Table:**\n\n{table_element.text}\n\n"
    
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
                embedding = await self.embedding_model.aget_text_embedding(content)
                
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
        query_embedding = await self.embedding_model.aget_text_embedding(query_request.query)
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
        chunks = db.query(RAGChunk).filter(RAGChunk.id.in_(chunk_ids)).all()
        
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
    rag_service = RAGService()
except Exception as e:
    rag_service = None
    print(f"Warning: RAG service not initialized - {str(e)}")
