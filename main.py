from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import shutil

# Import routers
from app.api.auth import router as auth_router
from app.api.eligibility import router as eligibility_router
from app.api.chat import router as chat_router
from app.api.rag import router as rag_router
from app.api.universities import router as universities_router
from app.api.applications import router as applications_router
from app.api.documents import router as documents_router
from app.api.admin.auth import router as admin_auth_router
from app.api.admin.programs import router as admin_programs_router
from app.api.admin.documents import router as admin_documents_router
from app.api.admin.applications import router as admin_applications_router
from app.api.admin.document_types import router as admin_document_types_router

# Load environment variables
load_dotenv()

# Create FastAPI instance
app = FastAPI(
    title="StudyCopilot API",
    description="Backend API for StudyCopilot - Your AI-Powered Path to UK Universities",
    version="1.0.0"
)
# Startup hook to ensure local models are in repo folder when using local backend
@app.on_event("startup")
async def ensure_local_models():
    backend = os.getenv("LLM_BACKEND", "openai").strip().lower()
    if backend != "local":
        return
    project_root = os.path.abspath(os.path.dirname(__file__))
    models_root = os.path.join(project_root, "models")
    # If user requests a fresh download, remove existing models
    if os.getenv("REFRESH_LOCAL_MODELS", "false").lower() in {"1", "true", "yes"}:
        if os.path.isdir(models_root):
            try:
                shutil.rmtree(models_root)
            except Exception:
                pass
    # Initialize providers once to trigger downloads into product-be/models
    try:
        from app.services.llm_providers.factory import create_chat_and_embeddings
        chat, emb = create_chat_and_embeddings()
        # Warm small calls to finalize files
        _ = emb.embed(["init"])
        _ = chat.generate([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "ok"}
        ], max_tokens=4, temperature=0.1)
    except Exception as e:
        # Defer failure to actual endpoints; we don't hard fail startup
        print(f"[startup] Local model init warning: {e}")

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(eligibility_router)
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(universities_router)
app.include_router(applications_router)
app.include_router(documents_router)

# Include admin routers
app.include_router(admin_auth_router)
app.include_router(admin_programs_router)
app.include_router(admin_documents_router)
app.include_router(admin_applications_router)
app.include_router(admin_document_types_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "StudyCopilot API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "studycopilot-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
