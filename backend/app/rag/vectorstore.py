"""FAISS vector store management."""

import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from app.config import settings
from app.rag.embeddings import get_embeddings

_vectorstore = None


def get_vectorstore() -> FAISS | None:
    """Load existing FAISS index from disk."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    index_path = Path(settings.VECTORSTORE_PATH)
    if (index_path / "index.faiss").exists():
        _vectorstore = FAISS.load_local(
            str(index_path),
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
    return _vectorstore


def create_vectorstore(documents: list) -> FAISS:
    """Create a new FAISS index from documents and save to disk."""
    global _vectorstore
    embeddings = get_embeddings()

    _vectorstore = FAISS.from_documents(documents, embeddings)

    index_path = Path(settings.VECTORSTORE_PATH)
    index_path.mkdir(parents=True, exist_ok=True)
    _vectorstore.save_local(str(index_path))

    return _vectorstore


def add_to_vectorstore(documents: list) -> FAISS:
    """Add documents to existing vector store or create new one."""
    global _vectorstore

    existing = get_vectorstore()
    if existing is None:
        return create_vectorstore(documents)

    embeddings = get_embeddings()
    new_store = FAISS.from_documents(documents, embeddings)
    existing.merge_from(new_store)

    index_path = Path(settings.VECTORSTORE_PATH)
    existing.save_local(str(index_path))
    _vectorstore = existing

    return _vectorstore


def get_chunks_by_source(pdf_name: str) -> list[dict]:
    """Get ALL chunks from a specific PDF by filtering the docstore metadata.
    
    This is the correct way to retrieve topic-specific content — NOT similarity search.
    Returns chunks sorted by page number for coherent context.
    """
    vs = get_vectorstore()
    if vs is None:
        return []

    chunks = []
    for doc_id, doc in vs.docstore._dict.items():
        source = doc.metadata.get("source", "")
        # Match by filename (handle both / and \ path separators)
        source_filename = source.replace("\\", "/").split("/")[-1]
        if source_filename == pdf_name or pdf_name in source:
            chunks.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
            })

    # Sort by page number for coherent ordering
    chunks.sort(key=lambda c: c["metadata"].get("page", 0))
    return chunks


def get_chunk_count() -> int:
    """Return the number of chunks in the vector store."""
    vs = get_vectorstore()
    if vs is None:
        return 0
    return vs.index.ntotal
