from __future__ import annotations

import json
from pathlib import Path

import pytest


CONVERSATIONS = json.loads((Path(__file__).parent / "fixtures" / "rc1" / "continuity.json").read_text(encoding="utf-8"))
TURNS = [(conversation["conversation_id"], turn) for conversation in CONVERSATIONS for turn in conversation["turns"]]


@pytest.mark.parametrize(("conversation_id", "turn"), TURNS, ids=[turn["case_id"] for _, turn in TURNS])
def test_continuity_turn_contract(conversation_id: str, turn: dict[str, object]) -> None:
    assert conversation_id.startswith("CONV-")
    assert turn["input"].strip()
    assert isinstance(turn["expected_inherited_context"], dict)
    assert isinstance(turn["expected_removed_context"], list)
    assert isinstance(turn["expected_corrections"], dict)
    assert turn["expected_result_behavior"].strip()
    inherited = json.dumps(turn["expected_inherited_context"], ensure_ascii=False)
    for removed in turn["expected_removed_context"]:
        if removed != "all":
            field, _, value = removed.partition(":")
            correction = turn["expected_corrections"].get(field)
            assert correction != value
            assert f'"{field}": "{value}"' not in inherited or field in turn["expected_corrections"]


def test_continuity_minimum_and_order() -> None:
    assert len(CONVERSATIONS) >= 5
    assert all(len(conversation["turns"]) >= 10 for conversation in CONVERSATIONS)
    assert len(TURNS) >= 50
    ids = [turn["case_id"] for _, turn in TURNS]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    inputs = {turn["input"].casefold() for _, turn in TURNS}
    for required in ("e julho?", "agora só fortaleza", "tira fortaleza", "o anterior", "só os três primeiros", "agora compara com ano passado"):
        assert required in inputs
