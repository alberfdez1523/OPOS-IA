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
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1024},
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
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 1024},
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
        "max_tokens": 1024,
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
