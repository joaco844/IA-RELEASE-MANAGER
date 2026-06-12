"""LLM provider factory.

The whole AI layer talks to `BaseChatModel` / `Embeddings` interfaces, so the
provider (OpenAI or Google Gemini) is swappable purely through configuration
(`AI_PROVIDER`) or per-request overrides.
"""

from typing import TYPE_CHECKING, Literal

from app.core.config import get_settings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models.chat_models import BaseChatModel

Provider = Literal["openai", "gemini"]


def resolve_provider(provider: str | None = None) -> Provider:
    settings = get_settings()
    value = provider or settings.ai_provider
    if value not in ("openai", "gemini"):
        raise ValueError(f"Unsupported AI provider: {value}")
    return value  # type: ignore[return-value]


def get_model_name(provider: str | None = None) -> str:
    settings = get_settings()
    return (
        settings.openai_model
        if resolve_provider(provider) == "openai"
        else settings.gemini_model
    )


def get_chat_model(
    provider: str | None = None, temperature: float | None = None
) -> "BaseChatModel":
    settings = get_settings()
    resolved = resolve_provider(provider)
    temp = settings.ai_temperature if temperature is None else temperature

    if resolved == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temp,
            api_key=settings.openai_api_key,
            timeout=120,
            max_retries=2,
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temp,
        google_api_key=settings.gemini_api_key,
        timeout=120,
        max_retries=2,
    )


def get_embeddings(provider: str | None = None) -> "Embeddings":
    settings = get_settings()
    if resolve_provider(provider) == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.openai_embedding_model, api_key=settings.openai_api_key
        )

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model, google_api_key=settings.gemini_api_key
    )
