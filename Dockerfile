FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Directorio raíz del proyecto
WORKDIR /app

# Copiar e instalar dependencias primero (cacheo de capas)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiar el resto del proyecto
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Directorio de trabajo = backend (para que ./vectorstore y ./data/pdfs funcionen)
WORKDIR /app/backend

# HuggingFace Spaces usa el puerto 7860
EXPOSE 7860

# Variables de entorno por defecto para HuggingFace
ENV LLM_PROVIDER=groq
ENV GROQ_MODEL=llama-3.1-70b-versatile
ENV PORT=7860

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
