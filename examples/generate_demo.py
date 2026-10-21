"""Genera PDFs ficticios para revisar visualmente el formato. No usar como cotización real."""
from __future__ import annotations
import os
from pathlib import Path

from estimation_mcp.domain.estimation import apply_buffers, calculate_pert, calculate_quotation, generate_roadmap, wbs_breakdown
from estimation_mcp.domain.scope import build_risk_register
from estimation_mcp.services.documents import generate_action_plan_pdf, generate_proposal_pdf, generate_quote_pdf

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("ESTIMATOR_OUTPUT_DIR", str(ROOT))

requirement = "Crear un módulo web para registrar, asignar y consultar incidencias internas, con roles de solicitante y soporte, historial de cambios y tablero básico."
wbs = wbs_breakdown(requirement, "feature")
tasks = [
    {"task_id": "T01", "name": "Análisis y criterios", "optimistic_hours": 5, "most_likely_hours": 8, "pessimistic_hours": 13},
    {"task_id": "T02", "name": "Modelo y API", "optimistic_hours": 12, "most_likely_hours": 18, "pessimistic_hours": 28},
    {"task_id": "T03", "name": "Interfaz del tablero", "optimistic_hours": 14, "most_likely_hours": 22, "pessimistic_hours": 34},
    {"task_id": "T04", "name": "Roles y flujo de estado", "optimistic_hours": 8, "most_likely_hours": 12, "pessimistic_hours": 20},
    {"task_id": "T05", "name": "Pruebas y despliegue", "optimistic_hours": 8, "most_likely_hours": 13, "pessimistic_hours": 21},
]
pert = calculate_pert(tasks)
buffers = apply_buffers(pert["total_expected_hours"], "modern", False, "standard", extra_contingency_pct=5)
quote = calculate_quotation(buffers["total_buffered_hours"], 55, 15, 30, 18, "PEN")
roadmap = generate_roadmap(buffers["total_buffered_hours"], 1, 6, "2026-11-02", 90)
risks = build_risk_register("modern", False, False, True, "medium")
common = dict(
    client_name="Cliente de demostración (ficticio)",
    project_title="Módulo de seguimiento de incidencias",
    wbs_data=wbs,
    pert_data=pert,
    quotation_data=quote,
    roadmap_data=roadmap,
    out_of_scope=["Aplicación móvil nativa.", "Migración histórica de tickets desde otra plataforma.", "Licencias de terceros y soporte evolutivo posterior."],
    assumptions=["El cliente aportará usuarios clave y criterios de aceptación.", "La solución se incorporará al entorno de aplicación ya existente.", "Las fechas se confirman después de validar dependencias y capacidad."],
    risk_data=risks,
    buffer_data=buffers,
    validity_days=15,
    payment_terms="40% al inicio, 40% contra entrega a pruebas y 20% después de la aceptación; ejemplo ficticio sujeto a negociación.",
    warranty_days=15,
    proposal_id="DEMO-2026-001",
)

proposal = generate_proposal_pdf(**common, file_name="demo-propuesta")
quote_pdf = generate_quote_pdf(
    client_name=common["client_name"], project_title=common["project_title"], quotation_data=quote,
    total_hours=buffers["total_buffered_hours"],
    scope_summary="Implementar registro, asignación y consulta de incidencias internas con roles, historial y tablero básico. Ejemplo exclusivamente demostrativo.",
    assumptions=common["assumptions"], out_of_scope=common["out_of_scope"],
    validity_days=15, payment_terms=common["payment_terms"], file_name="demo-cotizacion",
)
actions = generate_action_plan_pdf(
    client_name=common["client_name"], project_title=common["project_title"], roadmap_data=roadmap,
    action_items=[
        {"action": "Aprobar alcance y criterios de aceptación", "owner": "Responsable de negocio", "priority": "P0", "done_when": "Alcance aprobado"},
        {"action": "Confirmar ambiente, accesos y modelo de roles", "owner": "Cliente + líder técnico", "priority": "P0", "done_when": "Checklist validado"},
        {"action": "Revisar versión candidata y pruebas", "owner": "QA + usuario clave", "priority": "P1", "done_when": "Pruebas aceptadas"},
        {"action": "Aprobar despliegue y rollback", "owner": "Operaciones", "priority": "P1", "done_when": "Checklist de liberación cerrado"},
    ],
    dependencies=["Disponibilidad de usuario clave.", "Acceso al entorno de pruebas."],
    decisions_required=["Confirmar prioridad de los estados de incidencia.", "Confirmar permisos de cierre y reasignación."],
    file_name="demo-plan-de-accion",
)
for item in (proposal, quote_pdf, actions):
    print(f"{item['file_name']} | {item['size_bytes']} bytes | SHA-256 {item['sha256']}")
