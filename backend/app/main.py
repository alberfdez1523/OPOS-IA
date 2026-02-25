"""FastAPI main application for MúsicaOpos AI RAG system."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-ingest PDFs on startup if vectorstore doesn't exist."""
    from app.rag.vectorstore import get_vectorstore
    from app.ingestion.pdf_loader import ingest_pdfs

    if get_vectorstore() is None:
        print("⚡ Vectorstore not found — auto-ingesting PDFs...")
        try:
            result = ingest_pdfs()
            print(f"✅ Auto-ingest: {result['message']}")
        except Exception as e:
            print(f"⚠️ Auto-ingest failed: {e}")
    else:
        print("✅ Vectorstore loaded from disk.")
    yield


app = FastAPI(
    title="MúsicaOpos AI - RAG Chatbot",
    description="Asistente para Oposiciones de Profesor de Música basado en RAG con Llama 3.1 · Creado por Alberto Fernández",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Serve frontend
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
