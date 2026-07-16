import uuid

import pytest

from services.ai_credential_manager import AUTHORIZED_OPENAI_MODEL, ai_credential_manager


def test_aicm_rejects_invalid_and_masked_keys():
    assert ai_credential_manager.is_probably_invalid_key(None) is True
    assert ai_credential_manager.is_probably_invalid_key("SUBSTITUA_OPENAI_API_KEY") is True
    assert ai_credential_manager.is_probably_invalid_key("********abcd") is True
    assert ai_credential_manager.mask_credential("sk-test-secret-1234567890") == "****7890"


def test_aicm_redirects_to_authorized_model():
    assert ai_credential_manager.validate_authorized_model("gpt-4o") == AUTHORIZED_OPENAI_MODEL
    assert ai_credential_manager.validate_authorized_model(AUTHORIZED_OPENAI_MODEL) == AUTHORIZED_OPENAI_MODEL


@pytest.mark.asyncio
async def test_aicm_resolves_tenant_candidate_without_exposing_secret():
    api_key = "sk-" + "a" * 48
    tenant_id = uuid.uuid4()

    candidates = await ai_credential_manager.resolve_candidates(
        tenant_id=tenant_id,
        tenant_config={"api_key": api_key, "model": "gpt-4o-mini"},
        allow_global_fallback=False,
    )

    assert len(candidates) == 1
    assert candidates[0].source == "tenant"
    assert candidates[0].model == AUTHORIZED_OPENAI_MODEL

    status = ai_credential_manager.get_status(tenant_id)
    assert api_key not in str(status)
