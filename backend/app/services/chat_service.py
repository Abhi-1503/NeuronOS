import re
import uuid
from datetime import datetime, timezone

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, Conversation
from app.repositories.chat_repository import ChatRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.document_repository import DocumentRepository
from app.core.config import get_settings

CHAT_MODEL = "claude-sonnet-5"
MAX_RETRIEVED_DOCUMENTS = 3
MAX_RETRIEVED_CUSTOMERS = 3
_TITLE_MAX_CHARS = 60

# A natural-language question ILIKE'd as one literal string almost never matches a
# document (e.g. "Tell me about the XYZ renewal" won't match a doc whose text is
# "XYZ Solutions renewal is due next month"). Retrieval instead searches per keyword —
# still the same real Postgres ILIKE under the hood, just tokenized first — and merges
# results, rather than switching to actual NLP/embeddings (out of Phase 1 scope,
# Blueprint §14's "rule-based, not ML" MVP philosophy).
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "when", "where", "who",
    "how", "why", "tell", "me", "about", "with", "for", "and", "or", "to", "of",
    "in", "on", "at", "my", "our", "this", "that", "please", "can", "you", "do",
    "does", "did", "it", "be", "have", "has", "had",
}


def _extract_keywords(message: str, *, limit: int = 5) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", message)
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        lowered = word.lower()
        if len(word) < 3 or lowered in _STOPWORDS or lowered in seen:
            continue
        seen.add(lowered)
        keywords.append(word)
        if len(keywords) >= limit:
            break
    return keywords


class ConversationNotFoundError(Exception):
    pass


class ConversationAccessDeniedError(Exception):
    pass


def _title_from_message(message: str) -> str:
    stripped = message.strip()
    if len(stripped) <= _TITLE_MAX_CHARS:
        return stripped
    return stripped[:_TITLE_MAX_CHARS].rsplit(" ", 1)[0] + "…"


class ChatService:
    """API Spec §6 (AI Workspace). RAG retrieval combines the Knowledge Engine (keyword
    search over documents, respecting `visibility` — Blueprint §5.3's hard requirement
    that AI-surfaced content never leak outside the requester's own visibility scope)
    and the Context Engine (a rule-based customer-name mention match, the same
    "rule-based, not ML" approach already used for document linking, Blueprint §14).
    Generation uses Anthropic when configured; with no `ANTHROPIC_API_KEY` it degrades
    to an honest, clearly-labeled presentation of the raw retrieved context rather than
    fabricating a response."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chats = ChatRepository(session)
        self._documents = DocumentRepository(session)
        self._customers = CustomerRepository(session)
        settings = get_settings()
        self._client = (
            AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        )

    async def _retrieve(
        self, message: str, *, include_admin_only: bool
    ) -> tuple[list[dict], list[str]]:
        citations: list[dict] = []
        context_blocks: list[str] = []

        seen_document_ids: set[uuid.UUID] = set()
        for keyword in _extract_keywords(message):
            if len(seen_document_ids) >= MAX_RETRIEVED_DOCUMENTS:
                break
            matches = await self._documents.keyword_search(
                keyword, limit=MAX_RETRIEVED_DOCUMENTS, include_admin_only=include_admin_only
            )
            for doc, excerpt in matches:
                if doc.id in seen_document_ids or len(seen_document_ids) >= MAX_RETRIEVED_DOCUMENTS:
                    continue
                seen_document_ids.add(doc.id)
                citations.append({"type": "document", "id": str(doc.id), "excerpt": excerpt[:300]})
                context_blocks.append(f"Document '{doc.title}': {excerpt[:500]}")

        haystack = message.lower()
        customers = await self._customers.list_all_active()
        matched_customers = 0
        for customer in customers:
            if matched_customers >= MAX_RETRIEVED_CUSTOMERS:
                break
            if customer.name.lower() in haystack:
                excerpt = (
                    f"{customer.name} — status {customer.status}, "
                    f"relationship score {customer.relationship_score}"
                )
                citations.append({"type": "customer", "id": str(customer.id), "excerpt": excerpt})
                context_blocks.append(f"Customer '{customer.name}': {excerpt}")
                matched_customers += 1

        return citations, context_blocks

    async def _generate(self, message: str, context_blocks: list[str]) -> str:
        if self._client is None:
            if not context_blocks:
                return (
                    "AI-generated answers aren't available (no ANTHROPIC_API_KEY configured), "
                    "and nothing in your documents or customers directly matched this question."
                )
            joined = "\n".join(f"- {block}" for block in context_blocks)
            return (
                "AI-generated answers aren't available yet (no ANTHROPIC_API_KEY configured) — "
                f"here's what matched your question directly:\n{joined}"
            )

        context_text = (
            "\n".join(context_blocks)
            if context_blocks
            else "No matching documents or customers were found in this organization's workspace."
        )
        response = await self._client.messages.create(
            model=CHAT_MODEL,
            max_tokens=600,
            system=(
                "You are the NeuronOS AI Workspace assistant. Answer using only the context "
                "provided below; if it doesn't contain the answer, say so plainly rather than "
                "guessing.\n\nContext:\n" + context_text
            ),
            messages=[{"role": "user", "content": message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    async def send_message(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        include_admin_only: bool,
        conversation_id: uuid.UUID | None,
        message: str,
    ) -> tuple[Conversation, ChatMessage]:
        if conversation_id is not None:
            conversation = await self._chats.get_conversation(conversation_id)
            if conversation is None:
                raise ConversationNotFoundError()
            if conversation.user_id != user_id:
                raise ConversationAccessDeniedError()
        else:
            conversation = Conversation(
                organization_id=organization_id,
                user_id=user_id,
                title=_title_from_message(message),
            )
            self._chats.add_conversation(conversation)
            await self._session.flush()

        now = datetime.now(timezone.utc)
        self._chats.add_message(
            ChatMessage(
                conversation_id=conversation.id, role="user", content=message, created_at=now
            )
        )

        citations, context_blocks = await self._retrieve(
            message, include_admin_only=include_admin_only
        )
        answer = await self._generate(message, context_blocks)

        assistant_message = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            citations=citations or None,
            created_at=datetime.now(timezone.utc),
        )
        self._chats.add_message(assistant_message)
        conversation.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return conversation, assistant_message

    async def list_conversations(self, user_id: uuid.UUID, *, limit: int = 25) -> list[Conversation]:
        return await self._chats.list_for_user(user_id, limit=limit)

    async def get_conversation_detail(
        self, conversation_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> tuple[Conversation, list[ChatMessage]]:
        conversation = await self._chats.get_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError()
        if conversation.user_id != user_id:
            raise ConversationAccessDeniedError()
        messages = await self._chats.get_messages(conversation_id)
        return conversation, messages
