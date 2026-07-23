from anthropic import AsyncAnthropic

from app.core.config import get_settings

SUMMARY_MODEL = "claude-sonnet-5"

_FALLBACK_MAX_CHARS = 500


def _extractive_fallback(text: str) -> str:
    """No live model call — a simple leading excerpt, clearly not claiming to be an AI
    summary. Blueprint §1.9 warns against adding LLM-cost-bearing features before unit
    economics have been checked against real usage; this is the honest degrade path
    when no ANTHROPIC_API_KEY is configured, not a disguised fake summary."""
    excerpt = text.strip()[:_FALLBACK_MAX_CHARS]
    if len(text.strip()) > _FALLBACK_MAX_CHARS:
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return excerpt


class SummarizationService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def summarize(self, *, title: str, text: str) -> str:
        if not text.strip():
            return ""
        if self._client is None:
            return _extractive_fallback(text)

        response = await self._client.messages.create(
            model=SUMMARY_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Summarize this document in 2-3 sentences for a busy business "
                        f"owner. Title: {title}\n\nContent:\n{text[:8000]}"
                    ),
                }
            ],
        )
        return "".join(block.text for block in response.content if block.type == "text")
