import os
import time
import json
import re
from typing import List, Optional, Dict, Any, Tuple
import tiktoken
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

# PDF processing
import PyPDF2

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import UnexpectedResponse

from app.services.llm_providers.factory import create_chat_and_embeddings, get_llm_backend

# Simple keyword matching implementation
from collections import Counter
import math

# Local imports
from app.models.rag import RAGDocument, RAGQuery
from app.models.program_document import ProgramDocument
from app.models.eligibility import UKProgram
from app.schemas.rag import (
    RAGProcessingStatus, ChunkType, RAGQueryRequest, RAGQueryResponse,
    RAGChunkResponse, RAGProcessingResponse
)


class RAGService:
    """RAG service with hybrid search and university-specific processing"""
    
    def __init__(self):
        # Initialize providers (use embeddings provider; chat not needed here)
        _, self.embeddings = create_chat_and_embeddings()
        
        # Initialize Qdrant client
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Collection name for embeddings (separate per backend for dimension compatibility)
        backend = get_llm_backend()
        if backend == "local":
            self.collection_name = "university_documents_bge_m3"
        else:
            self.collection_name = "university_documents"
        
        # Initialize collection if it doesn't exist
        self._initialize_qdrant_collection()
        
        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Initialize stop words for keyword search
        self.stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one',
            'our', 'had', 'but', 'words', 'use', 'each', 'which', 'she', 'how', 'will', 'other',
            'this', 'that', 'with', 'have', 'from', 'they', 'been', 'said', 'what', 'were',
            'there', 'when', 'more', 'some', 'time', 'very', 'into', 'just', 'than', 'only'
        }
        
    def _initialize_qdrant_collection(self):
        """Initialize Qdrant collection if it doesn't exist"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embeddings.embedding_dim,
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
        """Extract content from PDF using PyPDF2 with university-specific processing"""
        try:
            chunks = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    # Extract text from page
                    text = page.extract_text()
                    
                    if text.strip():
                        # Clean and normalize text
                        text = self._clean_text(text)
                        
                        # Detect section type for university documents
                        section_info = self._detect_section_type(text)
                        
                        # Split into meaningful chunks based on content
                        page_chunks = self._create_university_chunks(
                            text, page_num, section_info
                        )
                        
                        chunks.extend(page_chunks)
            
            return chunks
            
        except Exception as e:
            raise Exception(f"Failed to extract PDF content: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers patterns
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Fix common PDF extraction issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        return text.strip()
    
    def _detect_section_type(self, text: str) -> Dict[str, Any]:
        """Detect section type for university documents"""
        text_lower = text.lower()
        
        section_keywords = {
            "admission": ["admission", "entry requirement", "application", "qualification"],
            "fees": ["fee", "tuition", "cost", "payment", "scholarship"],
            "curriculum": ["course", "module", "syllabus", "curriculum", "program structure"],
            "accommodation": ["accommodation", "housing", "residence", "dormitory"],
            "career": ["career", "employment", "graduate", "job", "placement"],
            "about": ["about", "overview", "introduction", "university"],
        }
        
        detected_sections = []
        for section, keywords in section_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_sections.append(section)
        
        return {
            "primary_section": detected_sections[0] if detected_sections else "general",
            "all_sections": detected_sections,
            "document_type": "prospectus"  # Default for university documents
        }
    
    def _create_university_chunks(
        self, 
        text: str, 
        page_number: int, 
        section_info: Dict[str, Any],
        chunk_size: int = 1024,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """Create chunks with university-specific logic"""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            # Check if adding this paragraph exceeds chunk size
            if self.count_tokens(current_chunk + " " + paragraph) > chunk_size:
                if current_chunk:
                    # Create chunk from current content
                    chunks.append(self._create_chunk_dict(
                        current_chunk,
                        chunk_index,
                        page_number,
                        section_info
                    ))
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    if chunk_overlap > 0:
                        overlap_text = current_chunk[-chunk_overlap:]
                        current_chunk = overlap_text + " " + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk += " " + paragraph if current_chunk else paragraph
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk_dict(
                current_chunk,
                chunk_index,
                page_number,
                section_info
            ))
        
        return chunks
    
    def _create_chunk_dict(
        self,
        content: str,
        chunk_index: int,
        page_number: int,
        section_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk dictionary with metadata"""
        # Extract keywords for hybrid search
        keywords = self._extract_keywords(content)
        
        return {
            "content": content.strip(),
            "chunk_index": chunk_index,
            "page_number": page_number,
            "token_count": self.count_tokens(content),
            "section_title": section_info.get("primary_section", "general"),
            "chunk_type": ChunkType.TEXT.value,
            "keywords": keywords,
            "section_metadata": section_info,
            "chunk_metadata": {
                "content_length": len(content),
                "keyword_count": len(keywords)
            }
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for hybrid search"""
        # Simple keyword extraction - can be improved with NLP
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common stop words and get unique keywords
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 
            'our', 'had', 'but', 'words', 'use', 'each', 'which', 'she', 'how', 'will', 'other'
        }
        
        keywords = [word for word in set(words) if word not in stop_words and len(word) > 3]
        return keywords[:20]  # Limit to top 20 keywords
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using configured provider"""
        try:
            return self.embeddings.embed([text])[0]
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
        
        # Get program details for metadata
        program = db.query(UKProgram).filter(
            UKProgram.id == program_doc.program_id
        ).first()
        
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
            # Delete existing embeddings from Qdrant
            await self._delete_document_embeddings(program_document_id)
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
            chunks_data = self.extract_pdf_content(program_doc.file_path)
            
            # Generate embeddings and store in Qdrant
            total_tokens = 0
            points = []
            
            for i, chunk_data in enumerate(chunks_data):
                content = chunk_data['content']
                token_count = chunk_data['token_count']
                total_tokens += token_count
                
                # Generate embedding
                embedding = await self.generate_embedding(content)
                
                # Create point for Qdrant with rich payload
                point_id = f"{program_document_id}_{i}"
                points.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        # Content and basic info
                        "content": content,
                        "chunk_index": i,
                        "token_count": token_count,
                        "page_number": chunk_data.get('page_number'),
                        "section_title": chunk_data.get('section_title'),
                        "chunk_type": chunk_data.get('chunk_type', ChunkType.TEXT.value),
                        
                        # Document association
                        "program_document_id": program_document_id,
                        "program_id": program_doc.program_id,
                        
                        # University metadata
                        "university_name": program.university_name if program else None,
                        "program_name": program.program_name if program else None,
                        "program_level": program.program_level if program else None,
                        "field_of_study": program.field_of_study if program else None,
                        "document_type": chunk_data.get('section_metadata', {}).get('document_type', 'prospectus'),
                        
                        # Search enhancement
                        "keywords": chunk_data.get('keywords', []),
                        "section_metadata": chunk_data.get('section_metadata', {}),
                        "chunk_metadata": chunk_data.get('chunk_metadata', {})
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
            rag_doc.total_chunks = len(chunks_data)
            rag_doc.total_tokens = total_tokens
            db.commit()
            
            return RAGProcessingResponse(
                rag_document_id=rag_doc.id,
                status=RAGProcessingStatus.COMPLETED,
                message=f"Document processed successfully. Created {len(chunks_data)} chunks with {total_tokens} tokens."
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
    
    async def _delete_document_embeddings(self, program_document_id: int) -> bool:
        """Delete document embeddings from Qdrant"""
        try:
            # Delete all points with matching program_document_id
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="program_document_id",
                            match=MatchValue(value=program_document_id)
                        )
                    ]
                )
            )
            return True
        except Exception as e:
            print(f"Error deleting embeddings from Qdrant: {e}")
            return False
    
    async def hybrid_search(
        self, 
        db: Session,
        query_request: RAGQueryRequest,
        student_id: Optional[int] = None,
        chat_session_id: Optional[int] = None
    ) -> RAGQueryResponse:
        """Hybrid search with dense vector search and keyword matching"""
        
        start_time = time.time()
        
        # Generate query embedding for dense search
        embedding_start = time.time()
        query_embedding = await self.generate_embedding(query_request.query)
        embedding_time = (time.time() - embedding_start) * 1000
        
        # Perform hybrid search
        retrieval_start = time.time()
        
        # Dense vector search
        dense_results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=query_request.max_chunks * 2,  # Get more for fusion
            score_threshold=query_request.similarity_threshold,
            with_payload=True
        )
        
        # Keyword-based sparse search
        sparse_results = self._simple_keyword_search(
            query_request.query,
            limit=query_request.max_chunks * 2
        )
        
        # Fuse results using Reciprocal Rank Fusion
        fused_results = self._fuse_search_results(
            dense_results, 
            sparse_results, 
            query_request.max_chunks
        )
        
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Convert to response format
        chunks_response = []
        for result in fused_results:
            payload = result.get('payload', {})
            chunks_response.append(RAGChunkResponse(
                content=payload.get('content', ''),
                chunk_index=payload.get('chunk_index', 0),
                token_count=payload.get('token_count', 0),
                page_number=payload.get('page_number'),
                section_title=payload.get('section_title'),
                chunk_type=payload.get('chunk_type', ChunkType.TEXT.value),
                chunk_metadata=payload.get('chunk_metadata', {}),
                similarity_score=result.get('score', 0.0),
                program_document_id=payload.get('program_document_id', 0),
                program_id=payload.get('program_id', 0),
                university_name=payload.get('university_name'),
                program_name=payload.get('program_name'),
                program_level=payload.get('program_level'),
                field_of_study=payload.get('field_of_study'),
                document_type=payload.get('document_type')
            ))
        
        total_time = (time.time() - start_time) * 1000
        
        # Log query for analytics
        if student_id or chat_session_id:
            query_log = RAGQuery(
                student_id=student_id,
                chat_session_id=chat_session_id,
                query_text=query_request.query,
                query_embedding=query_embedding,
                retrieved_chunks=[{"chunk_id": i, "score": chunk.similarity_score} for i, chunk in enumerate(chunks_response)],
                total_retrieved=len(chunks_response),
                max_similarity_score=chunks_response[0].similarity_score if chunks_response else 0.0,
                embedding_time_ms=embedding_time,
                retrieval_time_ms=retrieval_time,
                total_time_ms=total_time
            )
            db.add(query_log)
            db.commit()
        
        return RAGQueryResponse(
            query=query_request.query,
            chunks=chunks_response,
            total_retrieved=len(chunks_response),
            embedding_time_ms=embedding_time,
            retrieval_time_ms=retrieval_time,
            total_time_ms=total_time,
            search_method="hybrid"
        )
    
    
    def _simple_keyword_search(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform keyword-based search using simple TF-IDF similarity"""
        try:
            # Get all documents from Qdrant for keyword matching
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,  # Adjust based on your dataset size
                with_payload=True
            )
            
            documents = scroll_result[0]
            if not documents:
                return []
            
            # Extract content and keywords for matching
            contents = []
            for doc in documents:
                content = doc.payload.get('content', '')
                keywords = doc.payload.get('keywords', [])
                # Combine content and keywords for matching
                combined_text = content + ' ' + ' '.join(keywords)
                contents.append(combined_text)
            
            # Simple keyword matching using TF-IDF-like scoring
            query_terms = self._extract_search_terms(query)
            if not query_terms:
                return []
            
            # Calculate document frequencies
            doc_freq = {}
            for content in contents:
                content_terms = set(self._extract_search_terms(content))
                for term in query_terms:
                    if term in content_terms:
                        doc_freq[term] = doc_freq.get(term, 0) + 1
            
            # Calculate scores for each document
            scores = []
            for i, content in enumerate(contents):
                content_terms = self._extract_search_terms(content)
                content_term_count = Counter(content_terms)
                
                score = 0
                for term in query_terms:
                    if term in content_term_count:
                        # TF-IDF-like scoring
                        tf = content_term_count[term] / len(content_terms) if content_terms else 0
                        idf = math.log(len(contents) / (doc_freq.get(term, 1)))
                        score += tf * idf
                
                scores.append((i, score))
            
            # Sort by score and return top results
            scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for doc_idx, score in scores[:limit]:
                if score > 0.01:  # Minimum similarity threshold
                    results.append({
                        'payload': documents[doc_idx].payload,
                        'score': min(score, 1.0),  # Cap at 1.0 for consistency
                        'search_type': 'keyword'
                    })
            
            return results
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
    
    def _extract_search_terms(self, text: str) -> List[str]:
        """Extract search terms from text"""
        if not text:
            return []
        
        # Simple tokenization and cleaning
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove stop words and get unique terms
        terms = [word for word in words if word not in self.stop_words and len(word) > 2]
        return terms
    
    def _fuse_search_results(
        self, 
        dense_results: List[Any], 
        sparse_results: List[Dict[str, Any]], 
        final_limit: int
    ) -> List[Dict[str, Any]]:
        """Fuse dense and sparse search results using Reciprocal Rank Fusion"""
        
        # Convert dense results to common format
        dense_formatted = []
        for i, result in enumerate(dense_results):
            dense_formatted.append({
                'payload': result.payload,
                'score': result.score,
                'dense_rank': i + 1,
                'search_type': 'dense'
            })
        
        # Add sparse rank to sparse results
        for i, result in enumerate(sparse_results):
            result['sparse_rank'] = i + 1
        
        # Create combined results dictionary
        combined_results = {}
        
        # Add dense results
        for result in dense_formatted:
            content = result['payload'].get('content', '')
            if content not in combined_results:
                combined_results[content] = result
                combined_results[content]['dense_rank'] = result['dense_rank']
                combined_results[content]['sparse_rank'] = float('inf')
        
        # Add sparse results
        for result in sparse_results:
            content = result['payload'].get('content', '')
            if content in combined_results:
                combined_results[content]['sparse_rank'] = result['sparse_rank']
                # Boost score for items found in both searches
                combined_results[content]['score'] = max(
                    combined_results[content]['score'],
                    result['score']
                ) * 1.2
            else:
                combined_results[content] = result
                combined_results[content]['dense_rank'] = float('inf')
                combined_results[content]['sparse_rank'] = result['sparse_rank']
        
        # Calculate RRF scores
        k = 60  # RRF parameter
        for result in combined_results.values():
            dense_rank = result.get('dense_rank', float('inf'))
            sparse_rank = result.get('sparse_rank', float('inf'))
            
            rrf_score = 0
            if dense_rank != float('inf'):
                rrf_score += 1 / (k + dense_rank)
            if sparse_rank != float('inf'):
                rrf_score += 1 / (k + sparse_rank)
            
            result['rrf_score'] = rrf_score
        
        # Sort by RRF score and return top results
        final_results = sorted(
            combined_results.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        return final_results[:final_limit]
    
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
    
    async def delete_document_embeddings(self, db: Session, rag_document_id: int) -> bool:
        """Delete document embeddings from Qdrant"""
        try:
            # Get program_document_id from RAG document
            rag_doc = db.query(RAGDocument).filter(
                RAGDocument.id == rag_document_id
            ).first()
            
            if not rag_doc:
                return False
            
            return await self._delete_document_embeddings(rag_doc.program_document_id)
            
        except Exception as e:
            print(f"Error deleting embeddings: {e}")
            return False


# Global RAG service instance
try:
    rag_service = RAGService()
except Exception as e:
    rag_service = None
    print(f"Warning: RAG service not initialized - {str(e)}")
