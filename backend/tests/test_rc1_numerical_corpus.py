from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest


CORPUS = json.loads((Path(__file__).parent / "fixtures" / "rc1" / "numerical_truth.json").read_text(encoding="utf-8"))
ROWS = (
    ("A", "2026-06-05", "1", "1", "100", "A", "A-JUN-1", 10000, 2, 2000),
    ("A", "2026-06-10", "2", "2", "200", "B", "A-JUN-2", 20000, 2, 2000),
    ("A", "2026-07-05", "1", "1", "100", "A", "A-JUL-1", 15000, 1, 1000),
    ("A", "2026-07-10", "2", "2", "200", "B", "A-JUL-2", 25000, 2, 2000),
    ("A", "2025-06-05", "1", "1", "100", "A", "A-2025-1", 7500, 1, 0),
    ("B", "2026-06-05", "1", "1", "100", "X", "B-JUN-1", 90000, 3, 3000),
    ("B", "2026-07-05", "1", "1", "100", "X", "B-JUL-1", 120000, 4, 4000),
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE sales (tenant TEXT, day TEXT, seller TEXT, branch TEXT, product TEXT, "
        "category TEXT, order_id TEXT, revenue_cents INTEGER, quantity INTEGER, discount_cents INTEGER)"
    )
    connection.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ROWS)
    return connection


def _where(case: dict[str, object]) -> tuple[str, list[object]]:
    filters = case["expected_filters"]
    clauses, binds = ["tenant = ?"], [filters["tenant"]]
    period = str(case["expected_period"])
    if "|" not in period and period != "all":
        clauses.append("substr(day, 1, ?) = ?")
        binds.extend([len(period), period])
    for key in ("seller", "branch", "product", "category"):
        if key in filters:
            clauses.append(f"{key} = ?")
            binds.append(filters[key])
    return " AND ".join(clauses), binds


def _money(cents: int | None) -> str | None:
    return None if cents is None else str((Decimal(cents) / Decimal(100)).quantize(Decimal("0.01")))


def _scalar(connection: sqlite3.Connection, case: dict[str, object], metric: str) -> str | None:
    where, binds = _where(case)
    if metric in {"target_revenue", "target_attainment"}:
        return None
    column = {"revenue": "revenue_cents", "quantity": "quantity", "discount": "discount_cents"}[metric]
    value = connection.execute(f"SELECT SUM({column}) FROM sales WHERE {where}", binds).fetchone()[0]
    if metric == "quantity":
        return None if value is None else str(value)
    return _money(value)


def _ticket(connection: sqlite3.Connection, case: dict[str, object]) -> str | None:
    where, binds = _where(case)
    total, orders = connection.execute(
        f"SELECT SUM(revenue_cents), COUNT(DISTINCT order_id) FROM sales WHERE {where}", binds
    ).fetchone()
    if not orders:
        return None
    return str((Decimal(total) / Decimal(orders) / Decimal(100)).quantize(Decimal("0.01")))


def _grouped(connection: sqlite3.Connection, case: dict[str, object], dimension: str, descending: bool = False, limit: int | None = None) -> list[list[str]]:
    where, binds = _where(case)
    direction = "DESC" if descending else "ASC"
    order = f"total {direction}, {dimension} ASC" if case["expected_intent"] in {"ranking", "top", "bottom"} else f"{dimension} ASC"
    sql = f"SELECT {dimension}, SUM(revenue_cents) AS total FROM sales WHERE {where} GROUP BY {dimension} ORDER BY {order}"
    if limit:
        sql += " LIMIT ?"
        binds.append(limit)
    return [[str(key), _money(total)] for key, total in connection.execute(sql, binds).fetchall()]


def _periods(connection: sqlite3.Connection, case: dict[str, object]) -> list[list[str]]:
    periods = str(case["expected_period"]).split("|")
    tenant = case["expected_filters"]["tenant"]
    result = []
    for period in periods:
        cents = connection.execute(
            "SELECT SUM(revenue_cents) FROM sales WHERE tenant = ? AND substr(day, 1, ?) = ?",
            (tenant, len(period), period),
        ).fetchone()[0]
        result.append([period, _money(cents)])
    return result


def independent_oracle(case: dict[str, object]) -> dict[str, object]:
    with _connection() as connection:
        expected = case["expected_behavior"]
        metric = str(case["expected_metric"])
        if metric == "revenue|quantity|average_ticket|discount":
            return {"values": {name: (_ticket(connection, case) if name == "average_ticket" else _scalar(connection, case, name)) for name in ("revenue", "quantity", "average_ticket", "discount")}}
        if case["expected_dimensions"] == ["period"]:
            rows = _periods(connection, case)
            result: dict[str, object] = {"rows": rows}
            if "delta" in expected:
                result["delta"] = _money(int(Decimal(rows[1][1]) * 100) - int(Decimal(rows[0][1]) * 100))
            return result
        if case["expected_intent"] in {"ranking", "top", "bottom", "grouped_aggregate"} and case["expected_dimensions"]:
            dimension = case["expected_dimensions"][0]
            descending = case["expected_intent"] in {"ranking", "top"}
            limit = 1 if case["expected_intent"] in {"top", "bottom"} else None
            result = {"rows": _grouped(connection, case, dimension, descending, limit)}
            if "total" in expected:
                result["total"] = _scalar(connection, case, "revenue")
            return result
        value = _ticket(connection, case) if metric == "average_ticket" else _scalar(connection, case, metric)
        return {"value": value}


@pytest.mark.parametrize("case", CORPUS, ids=lambda case: case["case_id"])
def test_numerical_truth_against_independent_sql_oracle(case: dict[str, object]) -> None:
    expected = {key: value for key, value in case["expected_behavior"].items() if key != "status"}
    assert independent_oracle(case) == expected


def test_numerical_corpus_contract_and_order() -> None:
    assert len(CORPUS) >= 60
    ids = [case["case_id"] for case in CORPUS]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    required = {"question", "expected_intent", "expected_metric", "expected_period", "expected_dimensions", "expected_filters", "expected_order", "expected_result_reference", "expected_behavior", "expected_resolution_path", "view_class"}
    assert all(required <= case.keys() for case in CORPUS)
    assert {case["expected_resolution_path"] for case in CORPUS} == {"DETERMINISTIC"}
