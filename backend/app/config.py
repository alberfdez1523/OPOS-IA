from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM Provider: "ollama" or "groq"
    LLM_PROVIDER: str = "ollama"

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.3"

    # Groq (cloud - free tier)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Paths
    VECTORSTORE_PATH: str = "./vectorstore"
    PDF_PATH: str = "./data/pdfs"

    # Chunking
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
