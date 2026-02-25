"""Semantic search retriever."""

from app.rag.vectorstore import get_vectorstore


def retrieve_relevant_chunks(query: str, k: int = 5) -> list[dict]:
    """
    Search for the most relevant document chunks given a query.

    Returns list of dicts with 'content' and 'metadata' keys.
    """
    vs = get_vectorstore()
    if vs is None:
        return []

    results = vs.similarity_search_with_score(query, k=k)

    chunks = []
    for doc, score in results:
        chunks.append(
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
        )

    return chunks
