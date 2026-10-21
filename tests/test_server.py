from __future__ import annotations

import pytest

from estimation_mcp.server import compare_scenarios


def _scenario(**overrides):
    base = {
        "name": "Base",
        "total_hours": 100,
        "hourly_rate_cost": 20,
        "overhead_percentage": 15,
        "target_profit_margin_pct": 30,
        "tax_rate_pct": 18,
        "currency": "PEN",
        "team_size": 2,
        "daily_effective_hours_per_dev": 6,
        "team_availability_pct": 100,
    }
    base.update(overrides)
    return base


def test_compare_scenarios_returns_matching_calculations():
    result = compare_scenarios([_scenario(), _scenario(name="Con buffers", total_hours=185)])
    assert len(result["scenarios"]) == 2
    first, second = result["scenarios"]
    assert first["quotation"]["total_hours"] == 100
    assert second["quotation"]["total_hours"] == 185
    assert second["quotation"]["final_price_client"] > first["quotation"]["final_price_client"]
    assert "comparison_note" in result


def test_compare_scenarios_requires_at_least_one():
    with pytest.raises(ValueError):
        compare_scenarios([])


def test_compare_scenarios_limits_to_ten():
    with pytest.raises(ValueError):
        compare_scenarios([_scenario(name=f"S{i}") for i in range(11)])


def test_compare_scenarios_rejects_invalid_quotation_input():
    with pytest.raises(ValueError):
        compare_scenarios([_scenario(hourly_rate_cost="no-numerico")])
