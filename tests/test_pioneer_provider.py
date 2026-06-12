import asyncio
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from backend.providers.base import IRGenerationError
from backend.providers.factory import create_provider
from backend.providers.fallback import DeterministicProvider
from backend.providers.pioneer_provider import PioneerProvider
from backend.config import Settings
from shared.ir import EngineeringIR


@dataclass
class FakeResponse:
    output_parsed: object


class FakeResponses:
    def __init__(self, valid_ir: EngineeringIR) -> None:
        self.calls = 0
        self.valid_ir = valid_ir

    async def parse(self, **_kwargs) -> FakeResponse:
        self.calls += 1
        return FakeResponse(output_parsed=self.valid_ir)


class FakeClient:
    def __init__(self, valid_ir: EngineeringIR) -> None:
        self.responses = FakeResponses(valid_ir)


def test_pioneer_provider_generates_valid_ir() -> None:
    baseline = asyncio.run(DeterministicProvider().generate("make a house", None))
    client = FakeClient(baseline)
    provider = PioneerProvider(client=client, api_key="test-key", model="test-model")

    generated = asyncio.run(provider.generate("make a new house", None))

    assert provider.name == "pioneer"
    assert generated.intent == "make a new house"
    assert len(generated.scene.objects) == 5


def test_pioneer_provider_requires_api_key_without_client() -> None:
    with pytest.raises(IRGenerationError, match="PIONEER_API_KEY"):
        PioneerProvider()


def test_pioneer_provider_uses_pioneer_base_url(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("PIONEER_API_KEY", "test-key")
    monkeypatch.setattr("backend.providers.openai_provider.AsyncOpenAI", FakeAsyncOpenAI)

    PioneerProvider(model="job_test_model")

    assert captured["api_key"] == "test-key"
    assert captured["base_url"] == "https://api.pioneer.ai/v1"


def test_pioneer_resilient_provider_falls_back_on_failure() -> None:
    class FailingPioneer:
        name = "pioneer"

        async def generate(self, _prompt, _current_ir):
            raise IRGenerationError("pioneer unavailable")

    from backend.providers.factory import NamedResilientProvider

    provider = NamedResilientProvider(
        "pioneer+deterministic",
        FailingPioneer(),
        DeterministicProvider(),
    )
    generated = asyncio.run(provider.generate("make a house", None))
    assert len(generated.scene.objects) == 5


def test_factory_selects_pioneer_with_fallback(monkeypatch) -> None:
    monkeypatch.setenv("PIONEER_API_KEY", "test-key")
    monkeypatch.setenv("CAD_AGENT_PROVIDER", "pioneer")
    settings = Settings.from_env()
    provider = create_provider(settings)
    assert provider.name == "pioneer+deterministic"

    first = asyncio.run(provider.generate("make a house", None))
    assert len(first.scene.objects) == 5


def test_factory_falls_back_without_pioneer_key(monkeypatch) -> None:
    monkeypatch.delenv("PIONEER_API_KEY", raising=False)
    monkeypatch.setenv("CAD_AGENT_PROVIDER", "pioneer")
    settings = Settings.from_env()
    provider = create_provider(settings)
    assert provider.name == "deterministic"
