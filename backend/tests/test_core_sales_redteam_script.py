from scripts.run_core_sales_redteam import build_cases


def test_core_sales_redteam_battery_has_required_coverage():
    cases = build_cases()

    assert len(cases) >= 300
    assert any(case.expect_multi_visual for case in cases)
    assert any(case.expect_warning and case.category == "desconto" for case in cases)
    assert any(case.history for case in cases)
    assert any(case.expect_unsupported for case in cases)
