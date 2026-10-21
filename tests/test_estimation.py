from __future__ import annotations

import pytest

from estimation_mcp.domain.estimation import (
    apply_buffers,
    calculate_pert,
    calculate_quotation,
    generate_roadmap,
    wbs_breakdown,
)
from estimation_mcp.domain.scope import analyze_scope_gaps, build_risk_register


def test_pert_expected_and_standard_deviation():
    result = calculate_pert([{
        "task_id": "T1", "name": "API", "optimistic_hours": 2,
        "most_likely_hours": 4, "pessimistic_hours": 8,
    }])
    assert result["tasks_calculated"][0]["expected_hours"] == 4.33
    assert result["tasks_calculated"][0]["standard_deviation"] == 1.0
    assert result["confidence_intervals"]["95_percent_confidence"] == 6.33


def test_pert_rejects_invalid_order_and_duplicate_ids():
    with pytest.raises(ValueError, match="optimista"):
        calculate_pert([{"task_id": "T", "name": "x", "optimistic_hours": 4, "most_likely_hours": 2, "pessimistic_hours": 3}])
    task = {"task_id": "T", "name": "x", "optimistic_hours": 1, "most_likely_hours": 2, "pessimistic_hours": 3}
    with pytest.raises(ValueError, match="duplicado"):
        calculate_pert([task, task])


def test_buffers_use_additive_percentages_from_spec():
    result = apply_buffers(100, "legacy", True, "rigorous")
    assert result["total_buffer_pct"] == 85
    assert result["total_buffered_hours"] == 185


def test_quote_margin_on_sale_price_and_tax():
    result = calculate_quotation(100, 10, 15, 30, 18, "PEN")
    assert result["direct_cost"] == 1000
    assert result["overhead_cost"] == 150
    assert result["sale_price_before_tax"] == 1642.86
    assert result["tax_amount"] == 295.71
    assert result["final_price_client"] == 1938.57
    assert result["effective_margin_pct"] == 30


def test_quote_rejects_margin_above_limit_and_nan():
    with pytest.raises(ValueError):
        calculate_quotation(1, 1, target_profit_margin_pct=100)
    with pytest.raises(ValueError):
        calculate_quotation(float("nan"), 1)


def test_roadmap_days_reconcile_and_skip_weekends():
    result = generate_roadmap(12, 1, 6, "2026-10-23")
    assert result["total_days_required"] == 2
    assert sum(p["estimated_days"] for p in result["phases_timeline"]) == 2
    dated = [p for p in result["phases_timeline"] if p.get("start_date")]
    assert dated[0]["start_date"] == "2026-10-23"
    for phase in dated:
        assert __import__('datetime').date.fromisoformat(phase["start_date"]).weekday() < 5


def test_roadmap_small_estimate_does_not_overallocate():
    result = generate_roadmap(2, 1, 6)
    assert result["total_days_required"] == 1
    assert sum(p["estimated_days"] for p in result["phases_timeline"]) == 1


def test_wbs_type_is_validated():
    result = wbs_breakdown("Exportar reporte de venta", "feature")
    assert len(result["recommended_wbs"]) >= 4
    with pytest.raises(ValueError):
        wbs_breakdown("x", "unknown")


def test_scope_gap_does_not_claim_implicit_confirmation():
    result = analyze_scope_gaps("Integrar pedidos con el ERP", confirmed_categories=["integraciones"])
    assert result["pending_categories_count"] == 7
    integration = next(c for c in result["coverage_categories"] if c["category"] == "integraciones")
    assert integration["status"] == "confirmado_por_usuario"


def test_risk_register_orders_highest_risk_first():
    result = build_risk_register("legacy", True, True, True, "mission_critical")
    assert result["risk_count"] >= 5
    assert result["risk_register"][0]["score"] >= result["risk_register"][-1]["score"]
    assert result["high_risk_count"] >= 1
