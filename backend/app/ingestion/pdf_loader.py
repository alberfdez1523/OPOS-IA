"""PDF ingestion pipeline: load, chunk, and index PDFs."""

import os
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from app.config import settings
from app.rag.vectorstore import create_vectorstore, add_to_vectorstore, get_chunk_count


def load_pdfs(pdf_dir: str | None = None) -> list:
    """Load all PDFs from the specified directory."""
    pdf_path = Path(pdf_dir or settings.PDF_PATH)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_path}")

    all_documents = []
    pdf_files = list(pdf_path.glob("*.pdf"))

    if not pdf_files:
        return []

    for pdf_file in pdf_files:
        print(f"📄 Loading: {pdf_file.name}")
        loader = PyPDFLoader(str(pdf_file))
        documents = loader.load()
        all_documents.extend(documents)
        print(f"   → {len(documents)} pages loaded")

    return all_documents


def chunk_documents(documents: list) -> list:
    """Split documents into chunks for embedding."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(documents)
    print(f"📦 Created {len(chunks)} chunks from {len(documents)} pages")
    return chunks


def ingest_pdfs(pdf_dir: str | None = None) -> dict:
    """
    Full ingestion pipeline:
    1. Load PDFs
    2. Chunk them
    3. Create/update vector store

    Returns stats about the ingestion.
    """
    print("🚀 Starting PDF ingestion...")

    # Load
    documents = load_pdfs(pdf_dir)
    if not documents:
        return {
            "status": "no_pdfs",
            "message": "No PDF files found in the directory",
            "chunks": 0,
        }

    # Chunk
    chunks = chunk_documents(documents)

    # Index
    print("🔍 Creating embeddings and indexing...")
    create_vectorstore(chunks)

    total_chunks = get_chunk_count()
    print(f"✅ Ingestion complete! Total chunks in index: {total_chunks}")

    return {
        "status": "success",
        "message": f"Ingested {len(documents)} pages into {len(chunks)} chunks",
        "pages": len(documents),
        "chunks": len(chunks),
        "total_chunks_in_index": total_chunks,
    }
