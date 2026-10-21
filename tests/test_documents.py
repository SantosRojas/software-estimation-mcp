from __future__ import annotations

from pathlib import Path

import pytest

from estimation_mcp.services.documents import build_action_plan_markdown, build_proposal_markdown, render_markdown_pdf


def test_markdown_builder_and_pdf_output(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTIMATOR_OUTPUT_DIR", str(tmp_path))
    md = "# Documento de prueba\n\n**Cliente:** Ejemplo\n\n## Tabla\n| Campo | Valor |\n|---|---|\n| A | 1 |\n\n- uno\n- dos"
    result = render_markdown_pdf(md, "Documento de prueba")
    pdf = Path(result["file_path"])
    assert pdf.exists()
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert result["size_bytes"] > 500
    assert result["sha256"]


@pytest.mark.parametrize("malicious", ["../../escape", "..\\..\\escape", "/abs/escape", "C:\\Windows\\escape"])
def test_path_traversal_is_neutralized(tmp_path, monkeypatch, malicious):
    """Regresión de seguridad: el nombre de archivo nunca debe salir de ESTIMATOR_OUTPUT_DIR."""
    monkeypatch.setenv("ESTIMATOR_OUTPUT_DIR", str(tmp_path))
    result = render_markdown_pdf("# Doc", "Documento", malicious)
    target = Path(result["file_path"])
    assert target.parent == tmp_path.resolve()
    assert not (tmp_path.parent / f"{target.stem}.pdf").exists()


def test_existing_file_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTIMATOR_OUTPUT_DIR", str(tmp_path))
    first = render_markdown_pdf("# Uno", "Documento unico")
    second = render_markdown_pdf("# Dos", "Documento unico")
    assert Path(first["file_path"]).exists()
    assert Path(second["file_path"]).exists()
    assert first["file_path"] != second["file_path"]


def test_empty_filename_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTIMATOR_OUTPUT_DIR", str(tmp_path))
    for bad in ("..", ".", ".../"):
        with pytest.raises(ValueError):
            render_markdown_pdf("# Doc", "Documento", bad)


def test_action_plan_contains_phases():
    md = build_action_plan_markdown("Cliente", "Proyecto", {"total_days_required": 5, "total_weeks_required": 1, "team_size": 1, "phases_timeline": []})
    assert "Acciones y responsables" in md
    assert "Criterios de éxito" in md


def test_proposal_markdown_includes_buffer_detail_and_clear_missing_data_warning():
    base = {
        "client_name": "Cliente",
        "project_title": "Proyecto",
        "wbs_data": {"recommended_wbs": []},
        "pert_data": {"tasks_calculated": [], "total_expected_hours": 10, "confidence_intervals": {}, "methodology_note": "PERT note"},
        "quotation_data": {"currency": "PEN", "final_price_client": 100, "total_hours": 12},
        "roadmap_data": {"total_days_required": 2, "total_weeks_required": 1, "team_size": 1, "phases_timeline": []},
    }
    with_buffers = build_proposal_markdown(**base, buffer_data={
        "base_hours": 10, "total_buffer_pct": 20, "total_buffered_hours": 12,
        "buffers_applied": {"codebase_buffer_pct": 5, "integrations_buffer_pct": 0, "pm_buffer_pct": 15, "qa_buffer_pct": 0, "extra_contingency_pct": 0},
    })
    assert "Horas con buffers" in with_buffers
    without_buffers = build_proposal_markdown(**base)
    assert "No se recibió el desglose de buffers" in without_buffers
