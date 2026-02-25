# 📈 Opos AI — Asistente RAG de Opisicones de Música

Un chatbot RAG (Retrieval-Augmented Generation) que responde preguntas sobre Oposiciones de Musica usando apuntes subidos

## 🏗️ Arquitectura

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Frontend   │───▶│  FastAPI API  │───▶│   Ollama     │
│  HTML/CSS/JS │    │              │    │  Llama 3.1   │
└─────────────┘    │   ┌────────┐ │    └─────────────┘
                   │   │ FAISS  │ │
                   │   │ Vector │ │
                   │   │ Store  │ │
                   │   └────────┘ │
                   └──────────────┘
```

### Flujo RAG:
1. **Pregunta** → El usuario escribe una pregunta
2. **Retrieval** → Búsqueda semántica en FAISS (embeddings HuggingFace)
3. **Augmentation** → Los fragmentos relevantes se inyectan como contexto
4. **Generation** → Llama 3.1 (vía Ollama) genera la respuesta

## 📋 Requisitos

- **Python 3.11+**
- **Ollama** con el modelo `llama3.1` instalado
- ~4GB RAM para embeddings + FAISS
- ~8GB RAM para Llama 3.1 (8B)

## 🚀 Instalación

### 1. Instalar Ollama

```bash
# Windows: descargar de https://ollama.com/download
# Luego descargar el modelo:
ollama pull llama3.1
```

### 2. Configurar el backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración (editar si necesario)
copy .env.example .env
```

### 3. Añadir PDFs

Colocar los archivos PDF del curso en:
```
backend/data/pdfs/
```

### 4. Ejecutar

```bash
cd backend

# Iniciar el servidor
python -m uvicorn app.main:app --reload --port 8000
```

### 5. Indexar documentos

Una vez el servidor esté corriendo y los PDFs estén en `data/pdfs/`:

- **Opción A**: Desde la interfaz web, pulsar "🔄 Indexar documentos"
- **Opción B**: Llamar al API directamente:
  ```bash
  curl -X POST http://localhost:8000/api/ingest
  ```

### 6. Abrir la web

Ir a: **http://localhost:8000**

## 📁 Estructura del Proyecto

```
timeseries-ai/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app principal
│   │   ├── config.py         # Configuración
│   │   ├── api/
│   │   │   └── routes.py     # Endpoints REST
│   │   ├── rag/
│   │   │   ├── embeddings.py # Modelo de embeddings
│   │   │   ├── vectorstore.py# FAISS index
│   │   │   ├── retriever.py  # Búsqueda semántica
│   │   │   └── llm.py        # Integración Llama 3.1
│   │   └── ingestion/
│   │       └── pdf_loader.py # Pipeline de ingesta PDF
│   ├── data/pdfs/            # ← Colocar PDFs aquí
│   ├── vectorstore/          # Índice FAISS (auto-generado)
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── index.html            # Landing page
    ├── chat.html             # Interfaz de chat
    ├── css/styles.css        # Estilos
    └── js/
        ├── main.js           # JS landing
        └── chat.js           # JS chat + streaming
```

## 🔌 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/stats` | Estadísticas del sistema |
| `POST` | `/api/ask` | Pregunta (respuesta completa) |
| `POST` | `/api/ask/stream` | Pregunta (respuesta streaming SSE) |
| `POST` | `/api/ingest` | Indexar PDFs de `data/pdfs/` |
| `POST` | `/api/upload` | Subir un PDF |

## ⚙️ Configuración (.env)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL de Ollama |
| `OLLAMA_MODEL` | `llama3.1` | Modelo LLM |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Modelo embeddings |
| `CHUNK_SIZE` | `500` | Tamaño de chunks |
| `CHUNK_OVERLAP` | `50` | Overlap entre chunks |

## 🎨 Características

- ✅ Landing page con diseño dark mode
- ✅ Gráfico de serie temporal animado en tiempo real
- ✅ Chat con streaming (Server-Sent Events)
- ✅ Renderizado de Markdown y LaTeX (KaTeX)
- ✅ Búsqueda semántica con FAISS
- ✅ Subida de PDFs desde la interfaz
- ✅ Muestra las fuentes consultadas en cada respuesta
- ✅ Preguntas sugeridas y temas en sidebar
- ✅ Responsive design
