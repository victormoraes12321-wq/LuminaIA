from services.enterprise_audit_engine import EnterpriseAuditEngine


def test_enterprise_audit_generates_exact_question_and_scenario_matrix():
    engine = EnterpriseAuditEngine()
    questions = engine.generate_questions()
    scenarios = [scenario for question in questions for scenario in engine.generate_scenarios(question)]

    assert len(questions) == 100
    assert len(scenarios) == 300
    assert {scenario.mutation_kind for scenario in scenarios} == {
        "semantic_noise",
        "data_scale",
        "concurrency",
    }
    assert all(scenario.concurrency == 50 for scenario in scenarios if scenario.mutation_kind == "concurrency")


def test_enterprise_audit_report_contains_required_prove_it_evidence():
    engine = EnterpriseAuditEngine()
    report = engine.run()

    assert report.executive_summary["questions_generated"] == 100
    assert report.executive_summary["scenarios_generated"] == 300
    assert report.executive_summary["evidence_objects"] == 900
    assert report.executive_summary["proof_completeness_percent"] == 100.0
    assert report.coverage_matrix["critical_path_coverage_percent"] >= 98.5
    assert report.score_panel["Score Geral da Plataforma LuminaAI"] >= 98.5
    assert report.repeatability["data_consistency_variance"] == 0

    evidence = report.evidence_log[0]
    assert evidence["snapshot_pre"]
    assert evidence["payload_trace"]["payload"]["headers"]["X-Lumina-Audit-ID"]
    assert evidence["assertion_output_vs_oracle"]["binary_output"] == 1
    assert evidence["snapshot_post"]


def test_enterprise_audit_static_architecture_checks_are_clean():
    engine = EnterpriseAuditEngine()
    engine.run()

    severities = {finding.severity for finding in engine._findings}
    assert "CRITICAL" not in severities
    assert not engine._check_aicm_access_governed_by_aim()["details"]["unexpected"]
