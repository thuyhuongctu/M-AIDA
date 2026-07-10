"""Smoke tests for the ExtractionEngine adapter layer (engines.py).

Verifies that (1) a fake engine can be injected without any vendor SDK,
(2) the extraction pipeline converts a t-statistic exactly per Cohen (1988),
and (3) the legacy ``StatisticalExtractor(api_key=...)`` constructor still
builds the default Anthropic engine.
"""

from __future__ import annotations

import json

import pytest

from engines import EngineError, ExtractionEngine, make_engine
from extractor import StatisticalExtractor


class FakeEngine:
    """Deterministic engine: returns a canned extraction JSON payload."""

    provider = "fake"
    model = "fake-model-1"

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        self.calls.append((system, user))
        return json.dumps(self._payload)


class TestEngineInjection:
    def test_fake_engine_satisfies_protocol(self):
        assert isinstance(FakeEngine({}), ExtractionEngine)

    def test_extraction_with_injected_engine_t_to_r(self):
        # t = 2.5, df = 100 -> r = 2.5 / sqrt(2.5^2 + 100) = 0.2425 (Cohen, 1988)
        engine = FakeEngine(
            {
                "sample_n": 102,
                "effect_t": 2.5,
                "effect_df": 100,
                "doi_measure": "FSTS",
                "performance_measure": "ACC",
            }
        )
        extractor = StatisticalExtractor(engine=engine)
        effect = extractor.extract_from_text("dummy pdf text", {"title": "T", "year": 2020})
        assert effect.effect_r == pytest.approx(0.2425, abs=1e-4)
        assert effect.extraction_confidence == pytest.approx(0.8)
        assert effect.requires_verification is False
        assert engine.calls, "engine.complete was never invoked"

    def test_constructor_requires_key_or_engine(self):
        with pytest.raises(ValueError):
            StatisticalExtractor()

    def test_legacy_api_key_path_builds_anthropic_engine(self):
        pytest.importorskip("anthropic")
        extractor = StatisticalExtractor(api_key="sk-test-not-real")
        assert extractor._engine.provider == "anthropic"

    def test_make_engine_rejects_unknown_provider(self):
        with pytest.raises(EngineError):
            make_engine("unknown-vendor", api_key="x")
