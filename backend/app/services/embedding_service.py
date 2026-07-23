from openai import AsyncOpenAI

from app.core.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions — matches document_chunks.embedding


class EmbeddingService:
    """RAG retrieval (Blueprint §14.2) needs embeddings; Anthropic has no embeddings
    endpoint, so this uses OpenAI's — consistent with the Blueprint's own multi-model
    stack (Claude / OpenAI / Gemini), not a deviation from it. Genuinely optional: with
    no `OPENAI_API_KEY`, `embed()` returns `None` and callers fall back to keyword-only
    search (Roadmap Phase 1's actual Knowledge scope) rather than raising or faking a
    vector."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def embed(self, text: str) -> list[float] | None:
        if self._client is None:
            return None
        response = await self._client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding
