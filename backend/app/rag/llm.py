"""LLM integration with Ollama (local) and Groq (cloud)."""

import httpx
import json
from app.config import settings

SYSTEM_PROMPT = """Eres un asistente experto en oposiciones de Profesor de Música, creado por Alberto Fernández para ayudar a opositores a preparar su examen. Tu conocimiento está basado en los apuntes y temario oficial de oposiciones.

REGLAS:
1. Responde SIEMPRE en español.
2. Basa tus respuestas ÚNICAMENTE en el contexto proporcionado de los apuntes.
3. Si el contexto no contiene información suficiente para responder, dilo claramente.
4. Usa terminología musical adecuada y precisa.
5. Sé conciso pero completo en tus explicaciones.
6. Si mencionas obras o compositores, contextualízalos históricamente.
7. Puedes usar ejemplos para clarificar conceptos.
8. Mantén un tono académico pero accesible.
"""


def build_prompt(query: str, context_chunks: list[dict]) -> str:
    """Build the prompt with retrieved context."""
    context_text = "\n\n---\n\n".join(
        [
            f"[Fuente: {c['metadata'].get('source', 'desconocido')}, "
            f"Página: {c['metadata'].get('page', '?')}]\n{c['content']}"
            for c in context_chunks
        ]
    )

    return f"""Contexto de los apuntes:
{context_text}

Pregunta del opositor: {query}

Responde basándote en el contexto proporcionado. Si la información no está en el contexto, indícalo."""


# ============================================
# Ollama (local)
# ============================================

async def _generate_ollama(query: str, context_chunks: list[dict]) -> str:
    prompt = build_prompt(query, context_chunks)
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 2048},
            },
        )
        response.raise_for_status()
        return response.json()["response"]


async def _stream_ollama(query: str, context_chunks: list[dict]):
    prompt = build_prompt(query, context_chunks)
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": True,
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 2048},
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                    if data.get("done", False):
                        break


# ============================================
# Groq (cloud - free tier)
# ============================================

def _groq_headers():
    return {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def _groq_body(prompt: str, stream: bool = False):
    return {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": stream,
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": 2048,
    }


async def _generate_groq(query: str, context_chunks: list[dict]) -> str:
    prompt = build_prompt(query, context_chunks)
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=_groq_headers(),
            json=_groq_body(prompt, stream=False),
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def _stream_groq(query: str, context_chunks: list[dict]):
    prompt = build_prompt(query, context_chunks)
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers=_groq_headers(),
            json=_groq_body(prompt, stream=True),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    data = json.loads(payload)
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]


# ============================================
# Public API (routes to active provider)
# ============================================

async def generate_response(query: str, context_chunks: list[dict]) -> str:
    """Generate a response using the configured LLM provider."""
    if settings.LLM_PROVIDER == "groq":
        return await _generate_groq(query, context_chunks)
    return await _generate_ollama(query, context_chunks)


async def generate_response_stream(query: str, context_chunks: list[dict]):
    """Generate a streaming response using the configured LLM provider."""
    if settings.LLM_PROVIDER == "groq":
        async for token in _stream_groq(query, context_chunks):
            yield token
    else:
        async for token in _stream_ollama(query, context_chunks):
            yield token


# ============================================
# Test Question Generation
# ============================================

TEST_SYSTEM_PROMPT = """Eres un generador de tests de oposiciones de Profesor de Música. Debes crear preguntas de tipo test con 4 opciones (A, B, C, D) donde solo una es correcta.

REGLAS ESTRICTAS:
1. Responde SIEMPRE en español.
2. Basa las preguntas ÚNICA Y EXCLUSIVAMENTE en el contexto proporcionado. NO inventes datos.
3. Cada pregunta debe tener exactamente 4 opciones.
4. Incluye una breve explicación de por qué la respuesta correcta es correcta, citando el contexto.
5. Las opciones incorrectas deben ser plausibles pero claramente incorrectas según el contexto.
6. Las preguntas DEBEN estar directamente relacionadas con el tema indicado.
7. NO hagas preguntas sobre temas, compositores, obras o conceptos que NO aparezcan en el contexto.
8. Responde EXCLUSIVAMENTE con un JSON válido, sin texto adicional antes ni después.
"""


def _build_test_prompt(context_chunks: list[dict], topic_name: str, difficulty: str, num_questions: int) -> str:
    context_text = "\n\n---\n\n".join(
        [f"[Página: {c['metadata'].get('page', '?')}]\n{c['content']}"
         for c in context_chunks[:25]]
    )

    diff_desc = "de dificultad MEDIA (conceptos importantes pero accesibles)" if difficulty == "medio" \
        else "de dificultad ALTA (detalles específicos, matices y relaciones complejas)"

    return f"""TEMA: {topic_name}

Contenido COMPLETO del tema (estos son los apuntes reales del tema, úsalos como ÚNICA fuente de información):
{context_text}

IMPORTANTE: Genera exactamente {num_questions} preguntas tipo test {diff_desc} basándote SOLO en el contenido anterior del tema "{topic_name}".
- Cada pregunta DEBE poder responderse con la información del contexto.
- NO inventes datos, fechas, compositores u obras que no aparezcan en el texto.
- Las respuestas correctas DEBEN estar explícitamente en el contexto.

Responde SOLO con un JSON con esta estructura exacta (sin markdown, sin ```json, solo el JSON puro):
{{
  "questions": [
    {{
      "id": 1,
      "question": "Texto de la pregunta",
      "options": {{
        "A": "Primera opción",
        "B": "Segunda opción",
        "C": "Tercera opción",
        "D": "Cuarta opción"
      }},
      "correct": "A",
      "explanation": "Breve explicación de por qué A es correcta, citando el contexto"
    }}
  ]
}}"""


async def generate_test_questions(context_chunks: list[dict], topic_name: str, difficulty: str, num_questions: int = 10) -> dict:
    """Generate test questions using the configured LLM provider."""
    prompt = _build_test_prompt(context_chunks, topic_name, difficulty, num_questions)

    if settings.LLM_PROVIDER == "groq":
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=_groq_headers(),
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": TEST_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
    else:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": TEST_SYSTEM_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.5, "top_p": 0.9, "num_predict": 4096},
                },
            )
            response.raise_for_status()
            raw = response.json()["response"]

    # Parse the JSON from the LLM response
    # Try to extract JSON if wrapped in markdown code blocks
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove markdown code block
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    return json.loads(cleaned)


# ============================================
# Summary Generation
# ============================================

SUMMARY_SYSTEM_PROMPT = """Eres un experto en oposiciones de Profesor de Música. Tu tarea es crear resúmenes completos, bien estructurados y útiles para el estudio.

REGLAS ESTRICTAS:
1. Responde SIEMPRE en español.
2. Basa el resumen ÚNICA Y EXCLUSIVAMENTE en el contexto proporcionado. NO añadas información externa.
3. Estructura el resumen con secciones claras usando encabezados.
4. Incluye SOLO los conceptos clave, definiciones, autores y fechas que aparezcan en el contexto.
5. Usa listas y puntos para facilitar la lectura y el repaso.
6. Mantén un tono académico pero accesible.
7. Al final incluye una sección de "Conceptos clave" con los términos más importantes DEL CONTEXTO.
8. Si el contexto no cubre algún aspecto del tema, NO lo inventes.
9. El resumen debe ser fiel al contenido proporcionado, sin añadir conocimiento externo.
"""


def _build_summary_prompt(context_chunks: list[dict], topic_name: str) -> str:
    # Use ALL chunks — don't truncate, the LLM needs the full content to make a proper summary
    context_text = "\n\n---\n\n".join(
        [f"[Página: {c['metadata'].get('page', '?')}]\n{c['content']}"
         for c in context_chunks]
    )

    total_chars = sum(len(c['content']) for c in context_chunks)
    target_length = total_chars // 2  # Target: half the original content length

    return f"""TEMA: {topic_name}

Contenido COMPLETO del tema ({len(context_chunks)} fragmentos, {total_chars} caracteres):
{context_text}

Genera un resumen EXTENSO Y DETALLADO del tema "{topic_name}" basándote EXCLUSIVAMENTE en el contenido anterior.

LONGITUD OBJETIVO: El resumen debe tener aproximadamente {target_length} caracteres (la mitad del contenido original). NO hagas un resumen corto. Debe ser un resumen LARGO y COMPLETO que cubra TODOS los apartados del tema.

IMPORTANTE:
- Cubre TODOS los apartados y secciones que aparezcan en el contexto, sin omitir ninguno.
- NO añadas información que no esté en el contexto.
- NO inventes compositores, obras, fechas o conceptos que no aparezcan en el texto.
- Si algo no está en el contexto, NO lo incluyas.
- Sé EXHAUSTIVO: incluye todos los datos relevantes (nombres, fechas, obras, definiciones).

El resumen debe:
- Tener como título "{topic_name}"
- Estar dividido en secciones con encabezados claros (usa ## para secciones)
- Incluir TODOS los puntos importantes, no solo los principales
- Desarrollar cada sección con detalle suficiente
- Destacar definiciones, autores, obras y fechas que aparezcan en el contexto
- Terminar con una sección de 'Conceptos clave para el examen'"""


async def generate_summary(context_chunks: list[dict], topic_name: str) -> str:
    """Generate a complete summary using the configured LLM provider."""
    prompt = _build_summary_prompt(context_chunks, topic_name)

    if settings.LLM_PROVIDER == "groq":
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=_groq_headers(),
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 16384,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    else:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": SUMMARY_SYSTEM_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 16384},
                },
            )
            response.raise_for_status()
            return response.json()["response"]
