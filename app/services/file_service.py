import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
import shutil

# Configuration
UPLOAD_DIR = Path("uploads")
PROGRAMS_DIR = UPLOAD_DIR / "programs"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["application/pdf"]
ALLOWED_EXTENSIONS = [".pdf"]


class FileService:
    def __init__(self):
        self.ensure_upload_directories()
    
    def ensure_upload_directories(self):
        """Create upload directories if they don't exist"""
        UPLOAD_DIR.mkdir(exist_ok=True)
        PROGRAMS_DIR.mkdir(exist_ok=True)
    
    def validate_pdf_file(self, file: UploadFile) -> None:
        """Validate that the uploaded file is a valid PDF"""
        # Check file extension
        if not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."
            )
        
        # Check file size
        if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
            )
        
        # Reset file pointer to beginning
        file.file.seek(0)
        
        # Read first few bytes to check file signature
        header = file.file.read(4)
        file.file.seek(0)  # Reset again
        
        # PDF file signature check
        if not header.startswith(b'%PDF'):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file. File content does not match PDF format."
            )
    
    def generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename while preserving extension"""
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"
    
    def get_program_directory(self, program_id: int) -> Path:
        """Get or create directory for a specific program"""
        program_dir = PROGRAMS_DIR / str(program_id)
        program_dir.mkdir(exist_ok=True)
        return program_dir
    
    async def save_program_document(self, file: UploadFile, program_id: int) -> Tuple[str, str, int]:
        """
        Save uploaded PDF document for a program
        Returns: (filename, file_path, file_size)
        """
        # Validate file
        self.validate_pdf_file(file)
        
        # Generate unique filename
        filename = self.generate_filename(file.filename)
        
        # Get program directory
        program_dir = self.get_program_directory(program_id)
        file_path = program_dir / filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            return filename, str(file_path), file_size
            
        except Exception as e:
            # Clean up file if it was partially created
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )
    
    def delete_document_file(self, file_path: str) -> bool:
        """Delete a document file from filesystem"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                
                # Try to remove empty directory
                try:
                    path.parent.rmdir()
                except OSError:
                    # Directory not empty, that's fine
                    pass
                
                return True
            return False
        except Exception:
            return False
    
    def get_file_path(self, filename: str, program_id: int) -> Optional[Path]:
        """Get the full path to a file"""
        file_path = self.get_program_directory(program_id) / filename
        return file_path if file_path.exists() else None
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        path = Path(file_path)
        if not path.exists():
            return {}
        
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "exists": True
        }


# Global file service instance
file_service = FileService()
