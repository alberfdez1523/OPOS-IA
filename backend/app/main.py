"""FastAPI main application for MúsicaOpos AI RAG system."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.routes import router

app = FastAPI(
    title="MúsicaOpos AI - RAG Chatbot",
    description="Asistente para Oposiciones de Profesor de Música basado en RAG con Llama 3.1 · Creado por Alberto Fernández",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_preload():
    """Pre-load embeddings and vectorstore on startup so the app is ready instantly."""
    import asyncio
    from app.rag.embeddings import get_embeddings
    from app.rag.vectorstore import get_vectorstore
    print("🚀 Pre-loading embeddings model...")
    get_embeddings()
    print("🚀 Pre-loading FAISS vectorstore...")
    vs = get_vectorstore()
    if vs:
        print(f"✅ Vectorstore loaded: {vs.index.ntotal} chunks ready")
    else:
        print("⚠️ No vectorstore found. Run /api/ingest first.")

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

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve frontend
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
