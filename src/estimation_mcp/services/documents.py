"""Construcción de propuestas, planes de acción y PDF de aspecto profesional."""
from __future__ import annotations

import html
import os
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#245B83")
TEAL = colors.HexColor("#167D8D")
PALE = colors.HexColor("#EEF4F8")
LIGHT = colors.HexColor("#F6F8FA")
MID = colors.HexColor("#CBD5DF")
DARK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#5F6B76")
WHITE = colors.white


def _output_dir() -> Path:
    configured = os.environ.get("ESTIMATOR_OUTPUT_DIR", "output").strip()
    path = Path(configured).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slug(value: str, fallback: str = "documento") -> str:
    ascii_text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", ascii_text).strip("-_ ").lower()
    return (slug[:72].rstrip("-_")) or fallback


def _target_path(file_name: str | None, default_stem: str) -> Path:
    supplied = (file_name or "").strip()
    if supplied:
        # Only a basename is accepted. Paths are never honored from tool arguments.
        supplied = supplied.replace("\\", "/").split("/")[-1]
        stem = Path(supplied).stem
        if not stem or stem in {".", ".."}:
            raise ValueError("file_name no contiene un nombre válido.")
        stem = _slug(stem)
    else:
        stem = _slug(default_stem)
    output = _output_dir()
    target = output / f"{stem}.pdf"
    suffix = 2
    while target.exists():
        target = output / f"{stem}-{suffix}.pdf"
        suffix += 1
    # Defense in depth: target must remain directly inside output directory.
    if target.parent != output:
        raise ValueError("La ruta de destino no es válida.")
    return target


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ProposalTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=NAVY, alignment=TA_LEFT, spaceAfter=9),
        "subtitle": ParagraphStyle("ProposalSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=11, leading=16, textColor=MUTED, spaceAfter=8),
        "h1": ParagraphStyle("ProposalH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=15, spaceAfter=8, keepWithNext=True),
        "h2": ParagraphStyle("ProposalH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "h3": ParagraphStyle("ProposalH3", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=TEAL, spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "body": ParagraphStyle("ProposalBody", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=DARK, spaceAfter=5, wordWrap="LTR"),
        "small": ParagraphStyle("ProposalSmall", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, spaceAfter=3),
        "bullet": ParagraphStyle("ProposalBullet", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=12, leftIndent=12, firstLineIndent=-8, textColor=DARK, spaceAfter=3),
        "table_header": ParagraphStyle("ProposalTableHeader", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=WHITE),
        "table_cell": ParagraphStyle("ProposalTableCell", parent=base["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=DARK),
        "callout": ParagraphStyle("ProposalCallout", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=NAVY, spaceAfter=5),
    }


def _header_footer(canvas: Any, doc: Any, header_title: str) -> None:
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(MID)
        canvas.setLineWidth(0.5)
        canvas.line(19 * mm, height - 15 * mm, width - 19 * mm, height - 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(19 * mm, height - 12 * mm, header_title[:74])
    canvas.setStrokeColor(MID)
    canvas.line(19 * mm, 14 * mm, width - 19 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(19 * mm, 9 * mm, f"Generado el {date.today().isoformat()} | Estimación orientativa, sujeta a validación")
    canvas.drawRightString(width - 19 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _document(path: Path, title: str) -> SimpleDocTemplate:
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=19 * mm, leftMargin=19 * mm,
        topMargin=21 * mm, bottomMargin=19 * mm,
        title=title[:200], author="Software Estimation MCP", subject="Estimación, cotización y plan de acción",
    )
    return doc


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    # All arbitrary user text is escaped; only our own inline markup is introduced later.
    return Paragraph(str(text), style)


def _safe_inline(text: str) -> str:
    result = html.escape(text, quote=False)
    result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
    result = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", result)
    result = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", result)
    return result


def _money(value: Any, currency: str = "PEN") -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{currency} {amount:,.2f}"


def _table(data: list[list[Any]], col_widths: list[float] | None = None, *, repeat_rows: int = 1) -> Table:
    styles = _styles()
    cooked: list[list[Any]] = []
    for r, row in enumerate(data):
        style = styles["table_header"] if r == 0 else styles["table_cell"]
        cooked.append([x if isinstance(x, (Paragraph, Table)) else Paragraph(_safe_inline(str(x)), style) for x in row])
    table = Table(cooked, colWidths=col_widths, repeatRows=repeat_rows, hAlign="LEFT", splitByRow=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.35, MID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_proposal_markdown(
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
) -> str:
    client = client_name.strip()
    title = project_title.strip()
    if not client or not title:
        raise ValueError("client_name y project_title son obligatorios.")
    if len(client) > 200 or len(title) > 240:
        raise ValueError("client_name admite 200 y project_title 240 caracteres como máximo.")
    if not 1 <= validity_days <= 180:
        raise ValueError("validity_days debe estar entre 1 y 180.")
    if not 0 <= warranty_days <= 365:
        raise ValueError("warranty_days debe estar entre 0 y 365.")
    currency = str(quotation_data.get("currency", "PEN"))
    generated = date.today()
    lines = [
        f"# Propuesta técnica y comercial: {title}",
        f"**Cliente:** {client}  ",
        f"**Fecha de emisión:** {generated.isoformat()}  ",
        f"**Válida hasta:** {(generated + timedelta(days=validity_days)).isoformat()}  ",
        f"**Referencia:** {proposal_id or 'PROP-' + generated.strftime('%Y%m%d')}",
        "",
        "## 1. Resumen ejecutivo",
        f"Esta propuesta presenta un alcance de trabajo, estimación de esfuerzo, calendario y modelo económico para **{title}**. Los importes y plazos se basan en los datos suministrados y deben validarse con el cliente antes de su aprobación.",
        "",
        "## 2. Alcance de trabajo propuesto",
    ]
    for phase in wbs_data.get("recommended_wbs", []):
        lines.append(f"### {phase.get('phase', 'Fase')}")
        lines.extend([f"- {task}" for task in phase.get("mandatory_tasks", [])])
        lines.append("")
    if assumptions:
        lines.extend(["## 3. Supuestos de estimación", *[f"- {x}" for x in assumptions], ""])
    else:
        lines.extend(["## 3. Supuestos de estimación", "- Las estimaciones son preliminares y requieren validación de alcance, dependencias y aceptación.", "- El cliente facilitará oportunamente accesos, datos, ambientes y responsables necesarios.", "- Todo cambio de alcance se evaluará mediante control de cambios.", ""])
    lines.extend(["## 4. Elementos fuera de alcance", *([f"- {x}" for x in (out_of_scope or ["Requisitos no descritos ni aprobados expresamente en esta propuesta.", "Licencias, servicios cloud y costes de terceros, salvo indicación explícita.", "Soporte evolutivo posterior al periodo de garantía indicado."])]), ""])
    lines.extend(["## 5. Estimación de esfuerzo PERT", "| Tarea | Optimista (h) | Más probable (h) | Pesimista (h) | Esperado (h) | Riesgo |", "|---|---:|---:|---:|---:|---|"])
    for task in pert_data.get("tasks_calculated", []):
        lines.append(f"| {task.get('name','')} | {task.get('optimistic_hours', 0):.2f} | {task.get('most_likely_hours', 0):.2f} | {task.get('pessimistic_hours', 0):.2f} | {task.get('expected_hours', 0):.2f} | {task.get('risk_level','')} |")
    lines.extend([
        "",
        f"**Esfuerzo esperado:** {pert_data.get('total_expected_hours', 0):.2f} h  ",
        f"**Referencia +1 SD:** {pert_data.get('confidence_intervals', {}).get('68_percent_confidence', 0):.2f} h  ",
        f"**Referencia +2 SD:** {pert_data.get('confidence_intervals', {}).get('95_percent_confidence', 0):.2f} h  ",
        str(pert_data.get("methodology_note", "")),
        "",
    ])
    if buffer_data:
        lines.extend(["## 6. Buffers de planificación", f"**Horas PERT base:** {buffer_data.get('base_hours', pert_data.get('total_expected_hours', 0)):.2f} h  ", f"**Buffer total:** {buffer_data.get('total_buffer_pct', 0):.2f}%  ", f"**Horas con buffers:** {buffer_data.get('total_buffered_hours', quotation_data.get('total_hours', 0)):.2f} h", "| Factor | Porcentaje aplicado |", "|---|---:|"])
        for key, label in [("codebase_buffer_pct", "Tipo de base de código"), ("integrations_buffer_pct", "Integraciones de terceros"), ("pm_buffer_pct", "Gestión y comunicación"), ("qa_buffer_pct", "QA y garantía"), ("extra_contingency_pct", "Contingencia adicional")]:
            value = buffer_data.get("buffers_applied", {}).get(key, 0)
            lines.append(f"| {label} | {float(value):.2f}% |")
        lines.extend(["", str(buffer_data.get("calculation_method", "")), str(buffer_data.get("risk_summary", "")), ""])
    else:
        lines.extend(["## 6. Buffers de planificación", "No se recibió el desglose de buffers en los datos de entrada. Antes de formalizar la propuesta, confirmar si las horas y el precio incluyen gestión, QA, integraciones y contingencia.", ""])
    lines.extend([
        "## 7. Calendario preliminar",
        f"**Duración calculada:** {roadmap_data.get('total_days_required', 0)} días laborables (aprox. {roadmap_data.get('total_weeks_required', 0)} semanas). **Equipo:** {roadmap_data.get('team_size', 'N/D')} persona(s).",
        "| Fase | Asignación | Horas estimadas | Días laborables | Inicio | Fin |",
        "|---|---:|---:|---:|---|---|",
    ])
    for phase in roadmap_data.get("phases_timeline", []):
        lines.append(f"| {phase.get('phase_name','')} | {phase.get('percentage_alloc',0)}% | {phase.get('estimated_hours',0):.2f} | {phase.get('estimated_days',0)} | {phase.get('start_date','Por definir')} | {phase.get('end_date','Por definir')} |")
    lines.extend(["", "## 8. Inversión propuesta", "| Concepto | Importe |", "|---|---:|"])
    for label, key in [
        ("Coste directo", "direct_cost"),
        (f"Overhead ({quotation_data.get('overhead_percentage', 0):g}%)", "overhead_cost"),
        ("Coste total interno", "subtotal_cost"),
        ("Ganancia objetivo", "profit_amount"),
        ("Precio antes de impuestos", "sale_price_before_tax"),
        (f"Impuesto ({quotation_data.get('tax_rate_pct', 0):g}%)", "tax_amount"),
        ("**Precio total al cliente**", "final_price_client"),
    ]:
        lines.append(f"| {label} | {_money(quotation_data.get(key, 0), currency)} |")
    lines.extend(["", f"**Condiciones de pago:** {payment_terms}", f"**Garantía correctiva propuesta:** {warranty_days} días calendario desde la aceptación, limitada a defectos reproducibles del alcance entregado.", str(quotation_data.get("financial_note", "")), ""])
    lines.extend(["## 9. Registro inicial de riesgos"])
    if risk_data and risk_data.get("risk_register"):
        lines.extend(["| Riesgo | Probabilidad | Impacto | Nivel | Mitigación |", "|---|---:|---:|---|---|"])
        for risk in risk_data["risk_register"]:
            lines.append(f"| {risk.get('title','')} | {risk.get('probability_1_to_5','')} / 5 | {risk.get('impact_1_to_5','')} / 5 | {risk.get('level','')} | {risk.get('mitigation','')} |")
    else:
        lines.append("No se proporcionó un registro de riesgos. Antes de aprobación, identificar y asignar responsable a los riesgos relevantes.")
    lines.append("")
    lines.extend([
        "<!-- PAGEBREAK -->",
        "## 10. Aceptación y próximos pasos",
        "1. Confirmar alcance, exclusiones, supuestos y criterios de aceptación.",
        "2. Nombrar responsables del cliente y del proveedor; confirmar dependencias y accesos.",
        "3. Aprobar el monto, calendario, condiciones de pago y ventana de despliegue.",
        "4. Iniciar la fase de análisis y actualizar la estimación con la información validada.",
        "",
        "## Aprobación de la propuesta",
        "| Por el cliente | Por el proveedor |",
        "|---|---|",
        "| Nombre y cargo: __________________ | Nombre y cargo: __________________ |",
        "| Fecha: ___________________________ | Fecha: ___________________________ |",
        "| Firma: ___________________________ | Firma: ___________________________ |",
        "",
        "---",
        "**Nota:** Este documento es una propuesta de trabajo y no constituye asesoría legal, tributaria ni una garantía de duración. La aceptación debe formalizarse con las condiciones contractuales acordadas entre las partes.",
    ])
    return "\n".join(lines)


def build_action_plan_markdown(
    client_name: str,
    project_title: str,
    roadmap_data: dict[str, Any],
    action_items: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    decisions_required: list[str] | None = None,
    success_criteria: list[str] | None = None,
) -> str:
    if not client_name.strip() or not project_title.strip():
        raise ValueError("client_name y project_title son obligatorios.")
    lines = [
        f"# Plan de acción: {project_title}",
        f"**Cliente:** {client_name.strip()}  ",
        f"**Fecha:** {date.today().isoformat()}  ",
        f"**Duración de referencia:** {roadmap_data.get('total_days_required', 0)} días laborables / {roadmap_data.get('total_weeks_required', 0)} semanas  ",
        f"**Equipo considerado:** {roadmap_data.get('team_size', 'N/D')} persona(s)",
        "",
        "## 1. Objetivo",
        f"Organizar la ejecución de {project_title.strip()} en fases verificables, con responsables, dependencias y criterios de cierre acordados antes de comprometer fechas definitivas.",
        "",
        "## 2. Cronograma de trabajo",
        "| Fase | Asignación | Esfuerzo (h) | Días laborables | Inicio | Fin |",
        "|---|---:|---:|---:|---|---|",
    ]
    for phase in roadmap_data.get("phases_timeline", []):
        lines.append(f"| {phase.get('phase_name','')} | {phase.get('percentage_alloc',0)}% | {phase.get('estimated_hours',0):.2f} | {phase.get('estimated_days',0)} | {phase.get('start_date','Por definir')} | {phase.get('end_date','Por definir')} |")
    lines.extend(["", "## 3. Acciones y responsables", "| Acción | Responsable sugerido | Prioridad | Evidencia de cierre |", "|---|---|---|---|"])
    defaults = [
        {"action": "Confirmar alcance, exclusiones y criterios de aceptación", "owner": "Product owner / cliente", "priority": "P0", "done_when": "Alcance aprobado por escrito"},
        {"action": "Validar accesos, ambientes, datos y dependencias", "owner": "Cliente + líder técnico", "priority": "P0", "done_when": "Checklist de accesos y dependencias completo"},
        {"action": "Aprobar diseño y plan de pruebas", "owner": "Líder técnico + QA", "priority": "P1", "done_when": "Diseño y pruebas revisados"},
        {"action": "Ejecutar desarrollo y revisiones por iteración", "owner": "Equipo de desarrollo", "priority": "P1", "done_when": "Tareas aceptadas y pruebas verdes"},
        {"action": "Realizar validación de usuario y aprobación de liberación", "owner": "Usuario clave + operaciones", "priority": "P1", "done_when": "Acta de aceptación o defectos registrados"},
        {"action": "Desplegar, monitorear y transferir documentación", "owner": "Operaciones + líder técnico", "priority": "P1", "done_when": "Checklist de despliegue cerrado"},
    ]
    for item in (action_items or defaults):
        lines.append(f"| {item.get('action','')} | {item.get('owner','Por asignar')} | {item.get('priority','P1')} | {item.get('done_when','Evidencia acordada')} |")
    lines.extend(["", "## 4. Dependencias y prerrequisitos", *[f"- {x}" for x in (dependencies or ["Accesos a repositorios y entornos de desarrollo/pruebas.", "Disponibilidad de usuarios clave para resolver dudas y aceptar entregables.", "Credenciales y documentación de sistemas externos, si aplican."])], "", "## 5. Decisiones pendientes", *[f"- {x}" for x in (decisions_required or ["Confirmar fecha objetivo y disponibilidad real del equipo.", "Aprobar criterios de aceptación, presupuesto y condiciones comerciales.", "Confirmar responsable de producción y procedimiento de reversa."])], "", "## 6. Criterios de éxito", *[f"- {x}" for x in (success_criteria or ["Todos los criterios de aceptación aprobados.", "Sin defectos críticos abiertos al momento de liberación.", "Documentación mínima de operación y rollback entregada.", "Aceptación formal registrada por el responsable designado."])], "", "## 7. Cadencia de seguimiento", "- Reunión semanal de estado con avance, próximos hitos, riesgos y decisiones bloqueantes.", "- Actualizar estimación y fechas cuando cambien alcance, capacidad o dependencias.", "- Mantener un registro de decisiones y cambios aprobados.", "", "**Nota de calendario:** las fechas son preliminares; el cálculo considera lunes a viernes y no descuenta feriados ni ausencias."])
    return "\n".join(lines)


def _markdown_flowables(markdown_content: str, title: str) -> list[Any]:
    if not markdown_content.strip():
        raise ValueError("markdown_content no puede estar vacío.")
    if len(markdown_content) > 100_000:
        raise ValueError("El documento supera el límite de 100 000 caracteres.")
    styles = _styles()
    flow: list[Any] = []
    lines = markdown_content.splitlines()
    i = 0
    bullet_buffer: list[str] = []

    def flush_bullets() -> None:
        nonlocal bullet_buffer
        for item in bullet_buffer:
            flow.append(Paragraph("&#8226; " + _safe_inline(item), styles["bullet"]))
        bullet_buffer = []

    while i < len(lines):
        line = lines[i].rstrip()
        if line.strip() == "<!-- PAGEBREAK -->":
            flush_bullets()
            flow.append(PageBreak())
            i += 1
            continue
        if not line.strip():
            flush_bullets()
            i += 1
            continue
        if line.strip() == "---":
            flush_bullets()
            flow.extend([Spacer(1, 4), HRFlowable(width="100%", thickness=0.7, color=MID), Spacer(1, 5)])
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            flush_bullets()
            raw_rows = [line]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                raw_rows.append(lines[i].rstrip())
                i += 1
            table_data = []
            for row_idx, row in enumerate(raw_rows):
                cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
                if row_idx == 0:
                    table_data.append(cells)
                else:
                    table_data.append(cells)
            if table_data:
                max_cols = max(len(row) for row in table_data)
                normalized = [row + [""] * (max_cols - len(row)) for row in table_data]
                usable = A4[0] - 38 * mm
                widths = [usable / max_cols] * max_cols
                flow.append(_table(normalized, widths))
                flow.append(Spacer(1, 7))
            continue
        match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if match:
            flush_bullets()
            level = len(match.group(1))
            text = _safe_inline(match.group(2))
            if level == 1 and len(flow) == 0:
                flow.append(Paragraph(text, styles["title"]))
                flow.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=8))
            else:
                flow.append(Paragraph(text, styles[{2: "h1", 3: "h2"}.get(level, "h3")]))
            i += 1
            continue
        if line.startswith("- ") or re.match(r"^\d+\.\s+", line):
            bullet_buffer.append(re.sub(r"^(?:-\s+|\d+\.\s+)", "", line))
            i += 1
            continue
        flush_bullets()
        if line.startswith("**") and line.endswith("**") and len(line) > 4:
            flow.append(Paragraph(_safe_inline(line), styles["callout"]))
        else:
            flow.append(Paragraph(_safe_inline(line.replace("  ", " ")), styles["body"]))
        i += 1
    flush_bullets()
    return flow


def render_markdown_pdf(markdown_content: str, document_title: str, file_name: str | None = None) -> dict[str, Any]:
    title = document_title.strip() or "Documento de proyecto"
    if len(title) > 200:
        raise ValueError("document_title admite hasta 200 caracteres.")
    path = _target_path(file_name, title)
    flowables = _markdown_flowables(markdown_content, title)
    lowered = title.casefold()
    if lowered.startswith("propuesta"):
        header_title = "PROPUESTA TÉCNICA Y COMERCIAL"
    elif lowered.startswith("cotización") or lowered.startswith("cotizacion"):
        header_title = "COTIZACIÓN DE SERVICIOS DE SOFTWARE"
    elif lowered.startswith("plan de acción") or lowered.startswith("plan de accion"):
        header_title = "PLAN DE ACCIÓN"
    else:
        header_title = title.upper()[:74]
    def page_callback(canvas: Any, doc: Any) -> None:
        _header_footer(canvas, doc, header_title)
    _document(path, title).build(flowables, onFirstPage=page_callback, onLaterPages=page_callback)
    return _file_result(path, title)


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
    markdown_content = build_proposal_markdown(client_name, project_title, wbs_data, pert_data, quotation_data, roadmap_data, out_of_scope, assumptions, risk_data, validity_days, payment_terms, warranty_days, proposal_id, buffer_data)
    result = render_markdown_pdf(markdown_content, f"Propuesta - {project_title}", file_name or f"propuesta-{project_title}")
    result["document_type"] = "proposal"
    result["client_name"] = client_name
    result["project_title"] = project_title
    result["currency"] = quotation_data.get("currency", "PEN")
    result["final_price_client"] = quotation_data.get("final_price_client")
    return result


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
    markdown_content = build_action_plan_markdown(client_name, project_title, roadmap_data, action_items, dependencies, decisions_required, success_criteria)
    result = render_markdown_pdf(markdown_content, f"Plan de acción - {project_title}", file_name or f"plan-accion-{project_title}")
    result["document_type"] = "action_plan"
    result["client_name"] = client_name
    result["project_title"] = project_title
    return result


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
    if not client_name.strip() or not project_title.strip() or not scope_summary.strip():
        raise ValueError("client_name, project_title y scope_summary son obligatorios.")
    if not 1 <= validity_days <= 180:
        raise ValueError("validity_days debe estar entre 1 y 180.")
    currency = str(quotation_data.get("currency", "PEN"))
    today = date.today()
    expiry = date.fromordinal(today.toordinal() + validity_days)
    lines = [
        f"# Cotización de servicios de software: {project_title.strip()}",
        f"**Cliente:** {client_name.strip()}  ",
        f"**Fecha de emisión:** {today.isoformat()}  ",
        f"**Validez hasta:** {expiry.isoformat()}",
        "",
        "## Resumen de la propuesta",
        scope_summary.strip(),
        "",
        "## Base económica",
        f"- Esfuerzo calculado: {float(total_hours):.2f} horas.",
        f"- Tarifa de coste por hora: {_money(quotation_data.get('hourly_rate_cost', 0), currency)}.",
        f"- Overhead aplicado: {float(quotation_data.get('overhead_percentage', 0)):.2f}%.",
        f"- Margen objetivo sobre venta: {float(quotation_data.get('target_profit_margin_pct', 0)):.2f}%.",
        "",
        "## Desglose de importes",
        "| Concepto | Importe |",
        "|---|---:|",
    ]
    for label, key in [("Coste directo", "direct_cost"), ("Overhead", "overhead_cost"), ("Coste total interno", "subtotal_cost"), ("Ganancia", "profit_amount"), ("Precio antes de impuestos", "sale_price_before_tax"), (f"Impuesto ({quotation_data.get('tax_rate_pct', 0):g}%)", "tax_amount"), ("**Total a pagar**", "final_price_client")]:
        lines.append(f"| {label} | {_money(quotation_data.get(key, 0), currency)} |")
    lines.extend(["", "## Supuestos", *[f"- {x}" for x in (assumptions or ["El precio se basa en el alcance descrito en esta cotización.", "Cambios de alcance requieren evaluación y aprobación antes de ejecutarse.", "El cliente facilitará oportunamente accesos y validaciones."])], "", "## Exclusiones", *[f"- {x}" for x in (out_of_scope or ["Servicios o licencias de terceros no descritos expresamente.", "Nuevas funcionalidades no incluidas en el alcance.", "Soporte evolutivo posterior a la garantía acordada."])], "", f"## Condiciones comerciales\n{payment_terms}", "", str(quotation_data.get("financial_note", "")), "", "**Aceptación:** la cotización queda aprobada cuando ambas partes confirmen por escrito alcance, importe, plazo y condiciones comerciales.", "", "## Aprobación de la cotización", "| Por el cliente | Por el proveedor |", "|---|---|", "| Nombre y cargo: __________________ | Nombre y cargo: __________________ |", "| Fecha: ___________________________ | Fecha: ___________________________ |", "| Firma: ___________________________ | Firma: ___________________________ |"])
    result = render_markdown_pdf("\n".join(lines), f"Cotización - {project_title}", file_name or f"cotizacion-{project_title}")
    result["document_type"] = "quotation"
    result["client_name"] = client_name
    result["project_title"] = project_title
    result["currency"] = currency
    result["final_price_client"] = quotation_data.get("final_price_client")
    return result


def _file_result(path: Path, title: str) -> dict[str, Any]:
    import hashlib
    payload = path.read_bytes()
    if not payload.startswith(b"%PDF-"):
        path.unlink(missing_ok=True)
        raise RuntimeError("El motor PDF no produjo un PDF válido.")
    return {
        "status": "created",
        "document_title": title,
        "file_name": path.name,
        "file_path": str(path),
        "file_uri": path.as_uri(),
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": "El archivo se creó en el directorio configurado en el servidor MCP. El cliente MCP debe tener acceso a esa ruta local para abrirlo.",
    }
