"""Extraction engine adapters for M-AIDA.

Decouples the extraction pipeline from any single LLM vendor. The rest of the
codebase depends only on :class:`ExtractionEngine`; vendor SDKs are imported
lazily inside their adapter so a deployment ships only the client it actually
uses (BYOK - bring your own key).

Adding a provider = subclassing ExtractionEngine and registering it in
``make_engine``. Nothing else in M-AIDA changes.
"""
from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class EngineError(RuntimeError):
    """Raised when the underlying provider call fails."""


@runtime_checkable
class ExtractionEngine(Protocol):
    """Minimal contract the extraction pipeline needs from an LLM provider."""

    #: human-readable provider id, e.g. "anthropic"
    provider: str
    #: model identifier as reported to the audit trail
    model: str

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Return the raw text of a single completion for (system, user)."""
        ...


class AnthropicEngine:
    """Adapter for an Anthropic-compatible Messages API endpoint."""

    provider = "anthropic"
    DEFAULT_MODEL = "provider-default-model"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        import anthropic  # lazy: only this adapter needs the SDK

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except self._anthropic.APIError as exc:  # pragma: no cover - network
            logger.error("Provider API call failed: %s", exc)
            raise EngineError(str(exc)) from exc
        return next(
            (block.text for block in message.content if block.type == "text"), ""
        ).strip()


def make_engine(
    provider: str, api_key: str, model: str | None = None
) -> ExtractionEngine:
    """Factory: build the configured engine.

    Args:
        provider: provider id from settings (``llm_provider``).
        api_key: provider credential supplied by the deployment (BYOK).
        model: model id supplied by the researcher/deployment.
    """
    provider = (provider or "anthropic").lower()
    if provider == "anthropic":
        return AnthropicEngine(api_key=api_key, model=model)
    raise EngineError(f"Unknown llm_provider: {provider!r}")
