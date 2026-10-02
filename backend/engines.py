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
    # Mô hình dùng khi LLM_MODEL để trống. Trước đây là chuỗi giữ chỗ
    # "provider-default-model" — không phải mã mô hình thật, nên ai chỉ điền
    # LLM_API_KEY mà quên LLM_MODEL thì mọi lượt trích xuất đều hỏng với lỗi
    # "model not found" từ API. Sonnet: đủ chính xác cho việc đọc bảng số liệu
    # và rẻ hơn Opus; muốn đổi thì đặt LLM_MODEL trong backend/.env.
    DEFAULT_MODEL = "claude-sonnet-5"

    def __init__(self, api_key: str, model: str | None = None, temperature: float | None = None) -> None:
        import anthropic  # lazy: only this adapter needs the SDK

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        # None = do not send the parameter (the provider's default applies,
        # which is the behaviour of every release up to 8.0). A validation
        # run freezes an explicit value (LLM_TEMPERATURE) and records it.
        self.temperature = temperature
        # 8.0: token counts and latency of the last call, read by the job
        # pipeline to write llm_calls (cost accounting per user). Engines
        # that do not report usage simply leave these at None/0.
        self.last_usage: dict[str, int] | None = None
        self.last_latency_ms: int = 0

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        import time

        started = time.perf_counter()
        self.last_usage = None
        try:
            extra = {} if self.temperature is None else {"temperature": self.temperature}
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                **extra,
            )
        except self._anthropic.APIError as exc:  # pragma: no cover - network
            self.last_latency_ms = int((time.perf_counter() - started) * 1000)
            logger.error("Provider API call failed: %s", exc)
            raise EngineError(str(exc)) from exc
        self.last_latency_ms = int((time.perf_counter() - started) * 1000)
        usage = getattr(message, "usage", None)
        if usage is not None:
            self.last_usage = {
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            }
        return next(
            (block.text for block in message.content if block.type == "text"), ""
        ).strip()


def make_engine(
    provider: str, api_key: str, model: str | None = None, temperature: float | None = None
) -> ExtractionEngine:
    """Factory: build the configured engine.

    Args:
        provider: provider id from settings (``llm_provider``).
        api_key: provider credential supplied by the deployment (BYOK).
        model: model id supplied by the researcher/deployment.
    """
    provider = (provider or "anthropic").lower()
    if provider == "anthropic":
        return AnthropicEngine(api_key=api_key, model=model, temperature=temperature)
    raise EngineError(f"Unknown llm_provider: {provider!r}")
