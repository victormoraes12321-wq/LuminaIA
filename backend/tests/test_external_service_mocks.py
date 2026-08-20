from __future__ import annotations

import pytest

from testing.ai_mock import DeterministicAIMockError


pytestmark = [
    pytest.mark.unit,
    pytest.mark.no_database,
]


@pytest.mark.ai_mock
@pytest.mark.asyncio
async def test_openai_mock_is_deterministic_and_records_calls(
    fake_openai_provider,
) -> None:
    fake_openai_provider.queue_text("resultado fixo")
    response = await fake_openai_provider.client.chat.completions.create(
        model="gpt-test",
        purpose="intent_detection",
        messages=[],
    )
    assert response.choices[0].message.content == "resultado fixo"
    assert len(fake_openai_provider.calls) == 1
    assert fake_openai_provider.calls[0].purpose == "intent_detection"


@pytest.mark.ai_mock
@pytest.mark.asyncio
async def test_openai_mock_supports_failure_and_timeout(fake_openai_provider) -> None:
    fake_openai_provider.fail_with(DeterministicAIMockError("falha controlada"))
    with pytest.raises(DeterministicAIMockError, match="falha controlada"):
        await fake_openai_provider.client.chat.completions.create(messages=[])

    fake_openai_provider.timeout_next()
    with pytest.raises(TimeoutError, match="Timeout simulado"):
        await fake_openai_provider.client.chat.completions.create(messages=[])


@pytest.mark.oracle_mock
def test_oracle_mock_mode_is_forced_by_test_settings() -> None:
    from config import settings

    assert settings.is_testing is True
    assert settings.MOCK_ORACLE is True
    assert settings.LUMINA_DISABLE_EXTERNAL_NETWORK is True
