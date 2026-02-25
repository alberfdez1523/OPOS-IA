"""API routes for the RAG chatbot."""

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.llm import generate_response, generate_response_stream
from app.rag.vectorstore import get_chunk_count
from app.ingestion.pdf_loader import ingest_pdfs

router = APIRouter()


# --- Models ---

class QuestionRequest(BaseModel):
    question: str
    k: int = 5


class QuestionResponse(BaseModel):
    answer: str
    sources: list[dict]


class StatsResponse(BaseModel):
    chunks: int
    model: str
    status: str


class IngestResponse(BaseModel):
    status: str
    message: str
    chunks: int


# --- Routes ---

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    chunk_count = get_chunk_count()
    return StatsResponse(
        chunks=chunk_count,
        model=settings.OLLAMA_MODEL,
        status="active" if chunk_count > 0 else "no_data",
    )


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question - retrieves context and generates answer."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    # Retrieve relevant chunks
    chunks = retrieve_relevant_chunks(request.question, k=request.k)

    if not chunks:
        return QuestionResponse(
            answer="No tengo información sobre ese tema en mis apuntes. "
                   "Asegúrate de que los PDFs han sido cargados correctamente.",
            sources=[],
        )

    # Generate response
    try:
        answer = await generate_response(request.question, chunks)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al generar respuesta. ¿Está Ollama ejecutándose? Error: {str(e)}",
        )

    sources = [
        {
            "source": c["metadata"].get("source", "desconocido"),
            "page": c["metadata"].get("page", "?"),
            "score": round(c["score"], 4),
            "preview": c["content"][:150] + "...",
        }
        for c in chunks
    ]

    return QuestionResponse(answer=answer, sources=sources)


@router.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """Ask a question with streaming response."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    chunks = retrieve_relevant_chunks(request.question, k=request.k)

    if not chunks:
        async def empty_response():
            yield "data: No tengo información sobre ese tema en mis apuntes.\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(empty_response(), media_type="text/event-stream")

    async def stream_generator():
        try:
            async for token in generate_response_stream(request.question, chunks):
                yield f"data: {token}\n\n"
            # Send sources at the end
            import json
            sources = [
                {
                    "source": c["metadata"].get("source", "desconocido"),
                    "page": c["metadata"].get("page", "?"),
                    "score": round(c["score"], 4),
                    "preview": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                }
                for c in chunks
            ]
            yield f"data: [SOURCES]{json.dumps(sources)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents():
    """Trigger PDF ingestion from the data/pdfs directory."""
    try:
        result = ingest_pdfs()
        return IngestResponse(
            status=result["status"],
            message=result["message"],
            chunks=result.get("chunks", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for ingestion."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    pdf_dir = Path(settings.PDF_PATH)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    file_path = pdf_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "uploaded", "filename": file.filename, "path": str(file_path)}
