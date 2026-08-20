from __future__ import annotations

import json
from pathlib import Path

import pytest


CASES = json.loads((Path(__file__).parent / "fixtures" / "rc1" / "numerical_truth.json").read_text(encoding="utf-8"))
MULTIVIEW = [case for case in CASES if case["view_class"] != "single-view"]


@pytest.mark.parametrize("case", MULTIVIEW, ids=lambda case: case["case_id"])
def test_multiview_cases_are_explicit_and_numerically_anchored(case: dict[str, object]) -> None:
    assert case["view_class"] in {"two-view", "three-view", "four-plus-view"}
    behavior = case["expected_behavior"]
    assert behavior["status"] in {"ANSWER", "MISSING_DATA"}
    assert any(key in behavior for key in ("value", "values", "rows"))


def test_all_supported_view_classes_are_represented() -> None:
    counts = {name: sum(case["view_class"] == name for case in CASES) for name in ("single-view", "two-view", "three-view", "four-plus-view")}
    assert all(counts.values()), counts
