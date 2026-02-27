# 🎵 MúsicaOpos AI — Asistente RAG para Oposiciones de Música

Chatbot inteligente con **Retrieval-Augmented Generation (RAG)** para preparar las oposiciones de Profesor de Música. Sube tus temarios en PDF, hazle preguntas a la IA, genera tests de autoevaluación y resúmenes descargables — todo desde una interfaz moderna y 100 % local.

> **Creado por Alberto Fernández**

---

## 🏗️ Arquitectura

```
┌──────────────────┐     ┌──────────────────────┐     ┌──────────────┐
│     Frontend      │────▶│     FastAPI Backend    │────▶│    Ollama     │
│  HTML / CSS / JS  │     │                      │     │  Llama 3.1   │
│                  │     │  ┌────────────────┐  │     └──────────────┘
│  · Chat          │     │  │  FAISS Vector  │  │            │
│  · Tests         │     │  │    Store       │  │     ┌──────────────┐
│  · Resúmenes     │     │  └────────────────┘  │     │    Groq ☁️    │
│  · Login         │     │                      │     │  (fallback)  │
└──────────────────┘     └──────────────────────┘     └──────────────┘
```

### Flujo RAG

1. **Pregunta** → El usuario escribe una pregunta en el chat
2. **Retrieval** → Búsqueda semántica en FAISS con embeddings `all-MiniLM-L6-v2`
3. **Augmentation** → Los fragmentos más relevantes se inyectan como contexto al prompt
4. **Generation** → Llama 3.1 (local vía Ollama) o Llama 3.3 70B (cloud vía Groq) genera la respuesta

---

## 📋 Requisitos

| Componente | Mínimo |
|------------|--------|
| Python | 3.11+ |
| RAM | ~8 GB (embeddings + FAISS + Llama 3.1 8B) |
| Ollama | Instalado con `llama3.1` descargado |
| Disco | ~6 GB (modelo + vectorstore) |

> **Nota:** Si prefieres usar Groq (cloud), solo necesitas una API key gratuita y no necesitas Ollama ni RAM extra.

---

## 🚀 Instalación

### 1. Instalar Ollama

```bash
# Windows: descargar desde https://ollama.com/download
# Después, descargar el modelo:
ollama pull llama3.1
```

### 2. Configurar el backend

```bash
cd backend

# (Opcional) Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/Mac
```

Editar `.env` según tu configuración (ver sección [Configuración](#-configuración-env)).

### 3. Añadir los PDFs del temario

```
backend/data/pdfs/
├── TEMA 1 .pdf
├── TEMA 2 .pdf
├── ...
```

### 4. Ejecutar

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Al arrancar, el servidor **pre-carga** automáticamente el modelo de embeddings y el vectorstore para que la primera consulta sea instantánea.

### 5. Indexar documentos

Una vez el servidor esté corriendo y los PDFs estén en `data/pdfs/`:

- **Opción A:** Desde la interfaz web → botón **"🔄 Indexar documentos"**
- **Opción B:** Por API:
  ```bash
  curl -X POST http://localhost:8000/api/ingest
  ```

### 6. Abrir la web

```
http://localhost:8000
```

Contraseña de acceso: `musica2026`

---

## 📁 Estructura del Proyecto

```
OPOS-IA/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + startup preload
│   │   ├── config.py            # Settings (Pydantic)
│   │   ├── api/
│   │   │   └── routes.py        # 9 endpoints REST
│   │   ├── rag/
│   │   │   ├── embeddings.py    # HuggingFace embeddings (singleton)
│   │   │   ├── vectorstore.py   # FAISS load/create/merge
│   │   │   ├── retriever.py     # Búsqueda semántica
│   │   │   └── llm.py           # Ollama/Groq + test + summary
│   │   └── ingestion/
│   │       └── pdf_loader.py    # Carga y chunking de PDFs
│   ├── data/pdfs/               # ← Temarios PDF aquí
│   ├── vectorstore/             # Índice FAISS (auto-generado)
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── login.html               # Pantalla de login
│   ├── index.html               # Landing page
│   ├── chat.html                # Chat con IA (streaming)
│   ├── test.html                # Generador de tests
│   ├── summary.html             # Generador de resúmenes + PDF
│   ├── css/
│   │   └── styles.css           # Estilos dark mode
│   └── js/
│       ├── main.js              # JS landing
│       ├── chat.js              # Chat + SSE streaming
│       ├── test.js              # Lógica de tests
│       └── summary.js           # Resúmenes + descarga PDF
├── render.yaml                  # Deploy en Render (Groq)
├── Procfile                     # Heroku/Render start command
└── README.md
```

---

## 🔌 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/stats` | Estadísticas (chunks, modelo, estado) |
| `POST` | `/api/ask` | Pregunta con respuesta completa |
| `POST` | `/api/ask/stream` | Pregunta con streaming SSE |
| `POST` | `/api/ingest` | Indexar todos los PDFs de `data/pdfs/` |
| `POST` | `/api/upload` | Subir un PDF nuevo |
| `GET` | `/api/pdfs` | Listar PDFs disponibles |
| `POST` | `/api/generate-test` | Generar test de N preguntas desde un tema |
| `POST` | `/api/generate-summary` | Generar resumen completo de un tema |
| `GET` | `/health` | Health check |

---

## ⚙️ Configuración (.env)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Proveedor LLM: `ollama` (local) o `groq` (cloud) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL del servidor Ollama |
| `OLLAMA_MODEL` | `llama3.1` | Modelo local (8B, 4.6 GB) |
| `GROQ_API_KEY` | — | API key de Groq (solo si `LLM_PROVIDER=groq`) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Modelo cloud en Groq |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Modelo de embeddings |
| `CHUNK_SIZE` | `500` | Tamaño de los fragmentos de texto |
| `CHUNK_OVERLAP` | `50` | Solapamiento entre chunks |

---

## 🎨 Funcionalidades

### 💬 Chat con IA
- Respuestas en streaming (Server-Sent Events)
- Renderizado de **Markdown** y **LaTeX** (KaTeX)
- Fuentes consultadas en panel **desplegable** (colapsado por defecto)
- Búsqueda semántica con FAISS sobre los temarios

### 📝 Generador de Tests
- Selecciona un tema y la dificultad (medio / difícil)
- Genera tests de 3 a 20 preguntas tipo test con 4 opciones
- Corrección automática con puntuación y feedback

### 📄 Generador de Resúmenes
- Resumen completo y estructurado de cada tema
- Renderizado en Markdown con secciones, listas y negrita
- **Descarga instantánea en PDF** con diseño profesional (impresión nativa del navegador)

### 🔐 Login
- Pantalla de acceso con contraseña
- Sesión guardada en `sessionStorage`

### ⚡ Rendimiento
- Pre-carga de embeddings y vectorstore al arrancar el servidor
- La primera consulta tras login es instantánea
- Cache-busting automático en assets estáticos

### 🎨 Diseño
- Dark mode completo con gradientes púrpura
- Tipografía Inter + JetBrains Mono
- Navegación lateral entre Chat, Tests y Resúmenes
- Responsive design
- Subida de PDFs desde la interfaz

---

## ☁️ Deploy en Render

El proyecto incluye `render.yaml` para despliegue automático en [Render](https://render.com) usando Groq como proveedor LLM (cloud):

1. Conectar el repositorio a Render
2. Configurar `GROQ_API_KEY` en el dashboard
3. El servicio arrancará automáticamente con Llama 3.3 70B vía Groq

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI · Uvicorn · LangChain |
| LLM | Ollama (local) · Groq (cloud) |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector Store | FAISS |
| PDF Parsing | PyPDF |
| Frontend | HTML5 · CSS3 · Vanilla JS |
| Markdown | marked.js |
| Matemáticas | KaTeX |
| PDF Export | Impresión nativa del navegador |
