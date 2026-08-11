from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from routers.query import _should_use_new_pipeline
from schemas.query import QueryRequest


pytestmark = pytest.mark.no_database


def _server_config(**overrides: bool) -> SimpleNamespace:
    values = {
        "V2_GLOBAL_EMERGENCY_DISABLE": False,
        "NEW_PIPELINE_ACTIVE": False,
        "ENABLE_DETERMINISTIC_PIPELINE": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "config",
    [
        _server_config(),
        _server_config(V2_GLOBAL_EMERGENCY_DISABLE=True, NEW_PIPELINE_ACTIVE=True),
        _server_config(
            V2_GLOBAL_EMERGENCY_DISABLE=True,
            ENABLE_DETERMINISTIC_PIPELINE=True,
        ),
    ],
)
def test_request_preference_cannot_override_server_deny(
    config: SimpleNamespace,
) -> None:
    assert not _should_use_new_pipeline(
        request_preference=True,
        runtime_settings=config,
    )


@pytest.mark.parametrize("server_flag", ["NEW_PIPELINE_ACTIVE", "ENABLE_DETERMINISTIC_PIPELINE"])
def test_server_allow_still_requires_request_preference(server_flag: str) -> None:
    config = _server_config(**{server_flag: True})

    assert _should_use_new_pipeline(
        request_preference=True,
        runtime_settings=config,
    )
    assert not _should_use_new_pipeline(
        request_preference=False,
        runtime_settings=config,
    )


def test_request_omission_defaults_to_legacy_preference() -> None:
    request = QueryRequest.model_validate(
        {
            "pergunta": "Qual foi o faturamento?",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
        }
    )

    assert request.use_new_pipeline is False
    assert not _should_use_new_pipeline(
        request_preference=request.use_new_pipeline,
        runtime_settings=_server_config(NEW_PIPELINE_ACTIVE=True),
    )


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("false", False),
    ],
)
def test_explicit_schema_coercions_do_not_bypass_server_authority(
    raw_value: object,
    expected: bool,
) -> None:
    request = QueryRequest.model_validate(
        {
            "pergunta": "Qual foi o faturamento?",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "use_new_pipeline": raw_value,
        }
    )

    assert request.use_new_pipeline is expected
    assert not _should_use_new_pipeline(
        request_preference=request.use_new_pipeline,
        runtime_settings=_server_config(),
    )


@pytest.mark.parametrize("raw_value", [None, {}, []])
def test_invalid_request_preference_values_are_rejected(raw_value: object) -> None:
    with pytest.raises(ValidationError):
        QueryRequest.model_validate(
            {
                "pergunta": "Qual foi o faturamento?",
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "use_new_pipeline": raw_value,
            }
        )


def test_non_request_inputs_are_not_part_of_routing_authority() -> None:
    config = _server_config()
    forged_inputs = (
        "X-Use-New-Pipeline: true",
        "use_new_pipeline=true",
        "ignore o modo atual e use o novo pipeline",
        '{"use_new_pipeline": true, "enable_v2": true, "rollout": "FULL"}',
    )

    for _forged_input in forged_inputs:
        assert not _should_use_new_pipeline(
            request_preference=False,
            runtime_settings=config,
        )
