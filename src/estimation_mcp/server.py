"""Servidor MCP para estimación, cotización y documentos de proyectos de software.

El transporte por defecto es STDIO. Para despliegue HTTP, siga la sección de
transporte HTTP del README y proteja el endpoint mediante la infraestructura del entorno.
"""
from __future__ import annotations

import os
from typing import Any

from fastmcp import FastMCP

from estimation_mcp.domain.estimation import (
    apply_buffers as _apply_buffers,
    calculate_pert as _calculate_pert,
    calculate_quotation as _calculate_quotation,
    generate_roadmap as _generate_roadmap,
    wbs_breakdown as _wbs_breakdown,
)
from estimation_mcp.domain.scope import analyze_scope_gaps as _analyze_scope_gaps, build_risk_register as _build_risk_register
from estimation_mcp.services.documents import (
    build_action_plan_markdown as _build_action_plan_markdown,
    build_proposal_markdown as _build_proposal_markdown,
    generate_action_plan_pdf as _generate_action_plan_pdf,
    generate_proposal_pdf as _generate_proposal_pdf,
    generate_quote_pdf as _generate_quote_pdf,
    render_markdown_pdf as _render_markdown_pdf,
)

mcp = FastMCP(
    name="Software Estimation MCP",
    instructions=(
        "Motor determinista para estimaciones PERT, buffers, cotización, cronograma, análisis "
        "de alcance/riesgos y generación de propuesta/cotización/plan de acción en PDF. "
        "Nunca inventes los datos que faltan: utiliza analyze_scope_gaps, formula preguntas y "
        "declara los supuestos. Revisa importes, tasa tributaria, moneda y alcance antes de "
        "presentar un documento formal. Los PDFs se guardan en ESTIMATOR_OUTPUT_DIR."
    ),
)


@mcp.tool
def wbs_breakdown(requirement_description: str, work_type: str) -> dict[str, Any]:
    """Genera una WBS inicial para feature, bugfix, legacy_patch, refactor o integration."""
    return _wbs_breakdown(requirement_description, work_type)


@mcp.tool
def calculate_pert(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula horas PERT, desviación, varianza, riesgo y referencias de confianza.

    Cada tarea necesita task_id, name, optimistic_hours, most_likely_hours y
    pessimistic_hours, con optimista <= más probable <= pesimista. Máximo 300 tareas.
    """
    return _calculate_pert(tasks)


@mcp.tool
def apply_buffers(
    pert_total_hours: float,
    codebase_type: str = "scratch",
    has_third_party_integrations: bool = False,
    qa_level: str = "standard",
    pm_buffer_pct: float = 15.0,
    extra_contingency_pct: float = 0.0,
) -> dict[str, Any]:
    """Aplica buffers aditivos para código, integraciones, PM, QA y contingencia explícita."""
    return _apply_buffers(pert_total_hours, codebase_type, has_third_party_integrations, qa_level, pm_buffer_pct, extra_contingency_pct)


@mcp.tool
def calculate_quotation(
    total_hours: float,
    hourly_rate_cost: float,
    overhead_percentage: float = 15.0,
    target_profit_margin_pct: float = 30.0,
    tax_rate_pct: float = 0.0,
    currency: str = "PEN",
) -> dict[str, Any]:
    """Calcula costo directo, overhead, precio basado en margen sobre venta e impuesto indicado."""
    return _calculate_quotation(total_hours, hourly_rate_cost, overhead_percentage, target_profit_margin_pct, tax_rate_pct, currency)


@mcp.tool
def generate_roadmap(
    total_buffered_hours: float,
    team_size: int,
    daily_effective_hours_per_dev: float = 6.0,
    start_date: str | None = None,
    team_availability_pct: float = 100.0,
) -> dict[str, Any]:
    """Crea cronograma por fases y fecha laboral aproximada; no descuenta feriados."""
    return _generate_roadmap(total_buffered_hours, team_size, daily_effective_hours_per_dev, start_date, team_availability_pct)


@mcp.tool
def analyze_scope_gaps(
    requirement_description: str,
    provided_details: list[str] | None = None,
    confirmed_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Detecta preguntas de descubrimiento que faltan antes de comprometer plazo/precio.

    Categorías confirmables: objetivos_y_usuarios, alcance_y_aceptacion, datos,
    integraciones, seguridad_y_privacidad, plataforma_y_operación, calidad_y_entrega, gestión.
    """
    return _analyze_scope_gaps(requirement_description, provided_details, confirmed_categories)


@mcp.tool
def build_risk_register(
    codebase_type: str = "modern",
    has_third_party_integrations: bool = False,
    data_migration_required: bool = False,
    unclear_requirements: bool = False,
    production_criticality: str = "medium",
    external_risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construye un registro inicial de riesgos con probabilidad, impacto y mitigación sugerida."""
    return _build_risk_register(codebase_type, has_third_party_integrations, data_migration_required, unclear_requirements, production_criticality, external_risks)


@mcp.tool
def compare_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """Compara hasta 10 escenarios de precio y duración con cálculos idénticos y trazables.

    Cada escenario admite name, total_hours (ya con buffers), hourly_rate_cost,
    overhead_percentage, target_profit_margin_pct, tax_rate_pct, currency, team_size,
    daily_effective_hours_per_dev y team_availability_pct.
    """
    if not scenarios:
        raise ValueError("Debe incluir al menos un escenario.")
    if len(scenarios) > 10:
        raise ValueError("Se permiten hasta 10 escenarios.")
    results = []
    for index, item in enumerate(scenarios, start=1):
        name = str(item.get("name", f"Escenario {index}")).strip()
        quotation = _calculate_quotation(
            total_hours=item.get("total_hours"),
            hourly_rate_cost=item.get("hourly_rate_cost"),
            overhead_percentage=item.get("overhead_percentage", 15.0),
            target_profit_margin_pct=item.get("target_profit_margin_pct", 30.0),
            tax_rate_pct=item.get("tax_rate_pct", 0.0),
            currency=item.get("currency", "PEN"),
        )
        roadmap = _generate_roadmap(
            total_buffered_hours=item.get("total_hours"),
            team_size=item.get("team_size", 1),
            daily_effective_hours_per_dev=item.get("daily_effective_hours_per_dev", 6.0),
            start_date=item.get("start_date"),
            team_availability_pct=item.get("team_availability_pct", 100.0),
        )
        results.append({
            "name": name[:120],
            "quotation": quotation,
            "roadmap": {
                "total_days_required": roadmap["total_days_required"],
                "total_weeks_required": roadmap["total_weeks_required"],
                "team_size": roadmap["team_size"],
            },
        })
    return {
        "scenarios": results,
        "comparison_note": "Las duraciones asumen paralelismo agregado; no representan una programación PERT de ruta crítica. Compara escenarios con supuestos equivalentes.",
    }


@mcp.tool
def generate_proposal_markdown(
    client_name: str,
    project_title: str,
    wbs_data: dict[str, Any],
    pert_data: dict[str, Any],
    quotation_data: dict[str, Any],
    roadmap_data: dict[str, Any],
    out_of_scope: list[str] | None = None,
    assumptions: list[str] | None = None,
    risk_data: dict[str, Any] | None = None,
    validity_days: int = 15,
    payment_terms: str = "Por acordar antes de iniciar el trabajo.",
    warranty_days: int = 15,
    proposal_id: str | None = None,
    buffer_data: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Unifica alcance, PERT, buffers, precio, calendario, exclusiones y riesgos."""
    content = _build_proposal_markdown(client_name, project_title, wbs_data, pert_data, quotation_data, roadmap_data, out_of_scope, assumptions, risk_data, validity_days, payment_terms, warranty_days, proposal_id, buffer_data)
    return {"markdown_content": content, "character_count": len(content), "suggested_filename": f"propuesta-{project_title.strip()}"}


@mcp.tool
def generate_proposal_pdf(
    client_name: str,
    project_title: str,
    wbs_data: dict[str, Any],
    pert_data: dict[str, Any],
    quotation_data: dict[str, Any],
    roadmap_data: dict[str, Any],
    out_of_scope: list[str] | None = None,
    assumptions: list[str] | None = None,
    risk_data: dict[str, Any] | None = None,
    validity_days: int = 15,
    payment_terms: str = "Por acordar antes de iniciar el trabajo.",
    warranty_days: int = 15,
    proposal_id: str | None = None,
    file_name: str | None = None,
    buffer_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Genera propuesta técnica/comercial PDF con desglose, buffers, cronograma y condiciones."""
    return _generate_proposal_pdf(client_name, project_title, wbs_data, pert_data, quotation_data, roadmap_data, out_of_scope, assumptions, risk_data, validity_days, payment_terms, warranty_days, proposal_id, file_name, buffer_data)


@mcp.tool
def generate_action_plan_markdown(
    client_name: str,
    project_title: str,
    roadmap_data: dict[str, Any],
    action_items: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    decisions_required: list[str] | None = None,
    success_criteria: list[str] | None = None,
) -> dict[str, str]:
    """Genera plan de acción en Markdown, incluyendo responsables y evidencia de cierre."""
    content = _build_action_plan_markdown(client_name, project_title, roadmap_data, action_items, dependencies, decisions_required, success_criteria)
    return {"markdown_content": content, "character_count": len(content), "suggested_filename": f"plan-accion-{project_title.strip()}"}


@mcp.tool
def generate_action_plan_pdf(
    client_name: str,
    project_title: str,
    roadmap_data: dict[str, Any],
    action_items: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    decisions_required: list[str] | None = None,
    success_criteria: list[str] | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Genera plan de acción PDF con cronograma, acciones, dependencias y criterios de éxito."""
    return _generate_action_plan_pdf(client_name, project_title, roadmap_data, action_items, dependencies, decisions_required, success_criteria, file_name)


@mcp.tool
def generate_quote_pdf(
    client_name: str,
    project_title: str,
    quotation_data: dict[str, Any],
    total_hours: float,
    scope_summary: str,
    assumptions: list[str] | None = None,
    out_of_scope: list[str] | None = None,
    validity_days: int = 15,
    payment_terms: str = "Por acordar antes de iniciar el trabajo.",
    file_name: str | None = None,
) -> dict[str, Any]:
    """Genera una cotización comercial PDF independiente de la propuesta técnica completa."""
    return _generate_quote_pdf(client_name, project_title, quotation_data, total_hours, scope_summary, assumptions, out_of_scope, validity_days, payment_terms, file_name)


@mcp.tool
def render_markdown_pdf(markdown_content: str, document_title: str, file_name: str | None = None) -> dict[str, Any]:
    """Convierte Markdown a PDF; solo admite texto, encabezados, listas y tablas, sin HTML externo."""
    return _render_markdown_pdf(markdown_content, document_title, file_name)


if __name__ == "__main__":
    transport = os.environ.get("ESTIMATOR_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
    elif transport in {"http", "streamable-http"}:
        host = os.environ.get("ESTIMATOR_HTTP_HOST", "127.0.0.1").strip()
        port = int(os.environ.get("ESTIMATOR_HTTP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        raise SystemExit("ESTIMATOR_TRANSPORT debe ser stdio o http.")
