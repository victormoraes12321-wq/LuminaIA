"""Unit tests for governed evaluation suites, synthetic corpus, baselines, and regressions."""
from __future__ import annotations

import pytest
from contracts.observability_v2 import EvaluationOutcomeV2, EvaluationSuiteKindV2
from services.observability_v2.evaluations import (
    EvaluationBaselineServiceV2,
    EvaluationCorpusServiceV2,
    EvaluationSuiteRegistryV2,
    GovernedEvaluationRunnerV2,
)

pytestmark = pytest.mark.no_database


def test_evaluation_suite_registry_lists_all_26_suites():
    suites = EvaluationSuiteRegistryV2.list_suites()
    assert len(suites) == 26
    kinds = {s.kind for s in suites}
    assert EvaluationSuiteKindV2.SECURITY in kinds
    assert EvaluationSuiteKindV2.TENANT_ISOLATION in kinds
    assert EvaluationSuiteKindV2.REPRODUCIBILITY in kinds


def test_evaluation_corpus_and_runner_execution():
    runner = GovernedEvaluationRunnerV2()

    cases = EvaluationCorpusServiceV2.get_cases_for_suite(EvaluationSuiteKindV2.SECURITY)
    assert len(cases) == 2

    run = runner.run_suite(EvaluationSuiteKindV2.SECURITY)
    assert run.suite == EvaluationSuiteKindV2.SECURITY
    assert run.total_cases == 2
    assert run.passed_cases == 2
    assert run.failed_cases == 0
    assert len(run.regressions) == 0


def test_evaluation_baselines_immutable():
    baselines = EvaluationBaselineServiceV2.list_all_baselines()
    assert len(baselines) == 26
    for b in baselines:
        assert b.version == "1.0"
        assert b.source_commit_reference == "880477a980aeaef840ac0a5c66f8541eb6c7c349"
        assert len(b.checksum) >= 8
