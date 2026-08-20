from __future__ import annotations

import json
from pathlib import Path

import pytest


CORPUS = json.loads((Path(__file__).parent / "fixtures" / "rc1" / "language_safety.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CORPUS["typo"], ids=lambda case: case["case_id"])
def test_typo_corpus(case: dict[str, object]) -> None:
    assert case["classification"] in {"RESOLVE", "CLARIFY", "REJECT"}
    if case["classification"] == "RESOLVE":
        assert case["canonical"] and len(str(case["canonical"])) >= 3
    else:
        assert case["canonical"] is None


@pytest.mark.parametrize("case", CORPUS["impossible"], ids=lambda case: case["case_id"])
def test_impossible_corpus(case: dict[str, object]) -> None:
    assert case["classification"] in {"UNSUPPORTED", "REJECT"}
    assert str(case["expected_behavior"]).startswith(("STATE_", "REFUSE_"))
    assert case["fabricated_answer"] is False
    assert case["fabricated_metric"] is False
    assert case["fabricated_data_source"] is False


@pytest.mark.parametrize("case", CORPUS["causality"], ids=lambda case: case["case_id"])
def test_causality_corpus(case: dict[str, object]) -> None:
    assert case["evidence_available"]
    assert case["expected_behavior"]
    assert case["causal_claim_allowed"] is False


def test_language_safety_counts_and_order() -> None:
    minimums = {"typo": 25, "impossible": 15, "causality": 10}
    for name, minimum in minimums.items():
        cases = CORPUS[name]
        assert len(cases) >= minimum
        ids = [case["case_id"] for case in cases]
        assert ids == sorted(ids) and len(ids) == len(set(ids))
