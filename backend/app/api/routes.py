"""API routes for the RAG chatbot."""

import os
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.rag.retriever import retrieve_relevant_chunks
from app.rag.llm import generate_response, generate_response_stream, generate_test_questions, generate_summary
from app.rag.vectorstore import get_chunk_count, get_vectorstore
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
    model_name = settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OLLAMA_MODEL
    return StatsResponse(
        chunks=chunk_count,
        model=model_name,
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


# --- Test Generation ---

class TestRequest(BaseModel):
    pdf_name: str
    difficulty: str  # "medio" or "dificil"
    num_questions: int = 10


@router.get("/pdfs")
async def list_pdfs():
    """List available PDF files."""
    pdf_dir = Path(settings.PDF_PATH)
    if not pdf_dir.exists():
        return {"pdfs": []}
    pdf_files = [f.name for f in pdf_dir.glob("*.pdf")]
    return {"pdfs": sorted(pdf_files)}


@router.post("/generate-test")
async def generate_test(request: TestRequest):
    """Generate a test with questions from a specific PDF using the LLM."""
    if request.difficulty not in ("medio", "dificil"):
        raise HTTPException(status_code=400, detail="Dificultad debe ser 'medio' o 'dificil'")

    # Get chunks that come from the selected PDF
    vs = get_vectorstore()
    if vs is None:
        raise HTTPException(status_code=404, detail="No hay vector store. Indexa los documentos primero.")

    # Retrieve all chunks and filter by PDF source
    all_docs = vs.similarity_search(request.pdf_name.replace(".pdf", ""), k=40)
    pdf_chunks = []
    for doc in all_docs:
        source = doc.metadata.get("source", "")
        if request.pdf_name in source or request.pdf_name.replace(".pdf", "") in source:
            pdf_chunks.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
            })

    # If not enough specific chunks, use all retrieved
    if len(pdf_chunks) < 5:
        pdf_chunks = [{"content": doc.page_content, "metadata": doc.metadata} for doc in all_docs]

    try:
        result = await generate_test_questions(
            pdf_chunks,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
        )
        return {"status": "ok", "test": result}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error generando test: {str(e)}")


# --- Summary Generation ---

class SummaryRequest(BaseModel):
    pdf_name: str


@router.post("/generate-summary")
async def generate_summary_endpoint(request: SummaryRequest):
    """Generate a summary from a specific PDF using the LLM."""
    vs = get_vectorstore()
    if vs is None:
        raise HTTPException(status_code=404, detail="No hay vector store. Indexa los documentos primero.")

    # Retrieve chunks from the selected PDF
    all_docs = vs.similarity_search(request.pdf_name.replace(".pdf", ""), k=40)
    pdf_chunks = []
    for doc in all_docs:
        source = doc.metadata.get("source", "")
        if request.pdf_name in source or request.pdf_name.replace(".pdf", "") in source:
            pdf_chunks.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
            })

    # If not enough specific chunks, use all retrieved
    if len(pdf_chunks) < 5:
        pdf_chunks = [{"content": doc.page_content, "metadata": doc.metadata} for doc in all_docs]

    try:
        summary_text = await generate_summary(pdf_chunks)
        return {"status": "ok", "summary": summary_text, "pdf_name": request.pdf_name}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error generando resumen: {str(e)}")
