"""Cálculos deterministas de estimación, buffers, cotización y calendario."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class TaskEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=240)
    optimistic_hours: float = Field(ge=0, le=1_000_000)
    most_likely_hours: float = Field(ge=0, le=1_000_000)
    pessimistic_hours: float = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def check_order(self) -> TaskEstimate:
        if not self.optimistic_hours <= self.most_likely_hours <= self.pessimistic_hours:
            raise ValueError("Debe cumplirse optimista <= más probable <= pesimista.")
        return self


def _finite_nonnegative(value: float, name: str, *, maximum: float = 1_000_000_000) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} debe ser numérico.") from exc
    if not math.isfinite(number) or number < 0 or number > maximum:
        raise ValueError(f"{name} debe ser finito y estar entre 0 y {maximum}.")
    return number


def _round(number: float, digits: int = 2) -> float:
    return round(number + 1e-12, digits)


def wbs_breakdown(requirement_description: str, work_type: str) -> dict[str, Any]:
    description = requirement_description.strip()
    if not description:
        raise ValueError("requirement_description no puede estar vacío.")
    if len(description) > 12_000:
        raise ValueError("La descripción supera el límite de 12 000 caracteres.")
    choices = {
        "feature": [
            ("Descubrimiento y análisis", ["Aclarar objetivo, usuarios y criterios de aceptación", "Mapear reglas de negocio, casos límite y permisos", "Identificar dependencias, datos y restricciones no funcionales"]),
            ("Diseño", ["Definir arquitectura y contratos", "Diseñar modelo de datos y migraciones", "Preparar prototipos o especificación de interfaz cuando aplique"]),
            ("Implementación", ["Implementar lógica de negocio y validaciones", "Implementar interfaz y flujos de usuario", "Implementar telemetría, errores y controles de acceso"]),
            ("Verificación", ["Pruebas unitarias", "Pruebas de integración y regresión", "Revisión de seguridad, accesibilidad y rendimiento según alcance"]),
            ("Entrega", ["Revisión funcional con el cliente", "Despliegue controlado y plan de reversa", "Documentación operativa y transferencia de conocimiento"]),
        ],
        "bugfix": [
            ("Triage y reproducción", ["Recolectar evidencia y pasos reproducibles", "Confirmar impacto, severidad y alcance afectado", "Definir resultado esperado y criterio de cierre"]),
            ("Diagnóstico", ["Revisar logs, cambios recientes y rutas de ejecución", "Identificar causa raíz o hipótesis verificable", "Definir estrategia de corrección y riesgos de regresión"]),
            ("Corrección", ["Aplicar cambio mínimo localizado", "Agregar o actualizar pruebas de regresión", "Revisión por pares y análisis estático disponible"]),
            ("Validación y liberación", ["Validar en entorno controlado", "Verificar escenarios relacionados", "Desplegar con monitoreo y procedimiento de reversa"]),
        ],
        "legacy_patch": [
            ("Evaluación del legado", ["Identificar versión, dependencias y puntos de entrada", "Revisar deuda técnica y restricciones de compatibilidad", "Preparar respaldo y procedimiento de reversa"]),
            ("Diseño de parche", ["Aislar el cambio mínimo seguro", "Evaluar efectos laterales e interfaces compartidas", "Definir pruebas en versiones/entornos relevantes"]),
            ("Implementación controlada", ["Aplicar parche compatible con la plataforma existente", "Agregar pruebas que no requieran modernización completa", "Documentar deuda técnica que queda fuera del parche"]),
            ("Liberación", ["Ensayo en entorno similar a producción", "Liberación gradual o ventana aprobada", "Verificación posterior y plan de rollback"]),
        ],
        "refactor": [
            ("Línea base", ["Documentar comportamiento observable actual", "Medir cobertura y riesgos de regresión", "Identificar límites del refactor y dependencias"]),
            ("Diseño de refactor", ["Definir estructura objetivo sin cambios funcionales involuntarios", "Definir interfaces y estrategia de migración incremental", "Acordar métricas de calidad"]),
            ("Refactor incremental", ["Aplicar cambios pequeños verificables", "Eliminar duplicación y mejorar responsabilidades", "Actualizar pruebas y documentación técnica"]),
            ("Validación", ["Ejecutar pruebas de regresión", "Comparar métricas acordadas", "Liberar con rollback y seguimiento"]),
        ],
        "integration": [
            ("Análisis de integración", ["Definir contratos, autenticación y límites del proveedor", "Confirmar rate limits, errores y disponibilidad", "Acordar propiedad de datos y estrategia de reintentos"]),
            ("Diseño", ["Definir mapeo y validación de datos", "Diseñar idempotencia, colas y manejo de fallos si aplica", "Definir secretos, auditoría y observabilidad"]),
            ("Implementación", ["Construir cliente/adaptador y configuración por entorno", "Implementar reintentos seguros y circuit breaking cuando aplique", "Implementar manejo de errores y reconciliación"]),
            ("Pruebas y puesta en marcha", ["Pruebas con sandbox y casos de error", "Pruebas de contrato y seguridad", "Despliegue, monitoreo y documentación operativa"]),
        ],
    }
    if work_type not in choices:
        raise ValueError("work_type debe ser feature, bugfix, legacy_patch, refactor o integration.")
    labels = {"feature": "Nueva funcionalidad", "bugfix": "Corrección de defecto", "legacy_patch": "Parche sobre sistema legado", "refactor": "Refactorización", "integration": "Integración"}
    return {
        "project_type": labels[work_type],
        "work_type": work_type,
        "requirement_summary": description,
        "recommended_wbs": [
            {"phase": phase, "mandatory_tasks": tasks}
            for phase, tasks in choices[work_type]
        ],
        "usage_note": "WBS inicial para revisar con el responsable funcional y técnico; no sustituye la confirmación de alcance ni los criterios de aceptación.",
    }


def calculate_pert(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    if not tasks:
        raise ValueError("Debe incluir al menos una tarea.")
    if len(tasks) > 300:
        raise ValueError("Se permite un máximo de 300 tareas por cálculo.")
    validated: list[TaskEstimate] = []
    ids: set[str] = set()
    for index, task in enumerate(tasks):
        try:
            item = TaskEstimate.model_validate(task)
        except ValidationError as exc:
            raise ValueError(f"Tarea en posición {index}: {exc.errors()[0]['msg']}.") from exc
        if item.task_id in ids:
            raise ValueError(f"task_id duplicado: {item.task_id}.")
        ids.add(item.task_id)
        validated.append(item)

    calculated: list[dict[str, Any]] = []
    expected_total = 0.0
    total_variance = 0.0
    for task in validated:
        o, m, p = task.optimistic_hours, task.most_likely_hours, task.pessimistic_hours
        expected = (o + 4 * m + p) / 6
        sd = (p - o) / 6
        risk = "ALTO" if (expected > 0 and sd > expected * 0.25) else ("MEDIO" if (expected > 0 and sd > expected * 0.15) else "BAJO")
        expected_total += expected
        total_variance += sd**2
        calculated.append({
            "task_id": task.task_id,
            "name": task.name,
            "optimistic_hours": _round(o),
            "most_likely_hours": _round(m),
            "pessimistic_hours": _round(p),
            "expected_hours": _round(expected),
            "standard_deviation": _round(sd),
            "variance": _round(sd**2),
            "risk_level": risk,
        })
    project_sd = math.sqrt(total_variance)
    return {
        "tasks_calculated": calculated,
        "total_expected_hours": _round(expected_total),
        "project_standard_deviation": _round(project_sd),
        "confidence_intervals": {
            "68_percent_confidence": _round(expected_total + project_sd),
            "95_percent_confidence": _round(expected_total + 2 * project_sd),
        },
        "methodology_note": "Los valores 68_percent_confidence y 95_percent_confidence representan E + 1 SD y E + 2 SD (límites superiores aproximados, no intervalos simétricos); asumen independencia entre tareas y no sustituyen un análisis de ruta crítica.",
    }


def apply_buffers(
    pert_total_hours: float,
    codebase_type: str = "scratch",
    has_third_party_integrations: bool = False,
    qa_level: str = "standard",
    pm_buffer_pct: float = 15.0,
    extra_contingency_pct: float = 0.0,
) -> dict[str, Any]:
    base = _finite_nonnegative(pert_total_hours, "pert_total_hours")
    codebase_map = {"scratch": 10.0, "modern": 5.0, "legacy": 25.0}
    qa_map = {"basic": 10.0, "standard": 15.0, "rigorous": 25.0}
    if codebase_type not in codebase_map:
        raise ValueError("codebase_type debe ser scratch, modern o legacy.")
    if qa_level not in qa_map:
        raise ValueError("qa_level debe ser basic, standard o rigorous.")
    pm = _finite_nonnegative(pm_buffer_pct, "pm_buffer_pct", maximum=100.0)
    contingency = _finite_nonnegative(extra_contingency_pct, "extra_contingency_pct", maximum=100.0)
    values = {
        "codebase_buffer_pct": codebase_map[codebase_type],
        "integrations_buffer_pct": 20.0 if has_third_party_integrations else 0.0,
        "pm_buffer_pct": pm,
        "qa_buffer_pct": qa_map[qa_level],
        "extra_contingency_pct": contingency,
    }
    total_pct = sum(values.values())
    total = base * (1 + total_pct / 100)
    risk_bits = []
    if codebase_type == "legacy":
        risk_bits.append("base de código legado (+25%)")
    if has_third_party_integrations:
        risk_bits.append("integraciones externas (+20%)")
    if qa_level == "rigorous":
        risk_bits.append("QA riguroso (+25%)")
    if contingency > 0:
        risk_bits.append(f"contingencia adicional (+{contingency:g}%)")
    risk_summary = ("Factores considerados: " + "; ".join(risk_bits) + ".") if risk_bits else "Sin factores adicionales de alto impacto en los buffers configurados."
    return {
        "base_hours": _round(base),
        "buffers_applied": values,
        "total_buffer_pct": _round(total_pct),
        "total_buffered_hours": _round(total),
        "risk_summary": risk_summary,
        "calculation_method": "Los porcentajes se suman de forma aditiva sobre las horas PERT base, tal como especifica la metodología; no se capitalizan entre sí.",
    }


def calculate_quotation(
    total_hours: float,
    hourly_rate_cost: float,
    overhead_percentage: float = 15.0,
    target_profit_margin_pct: float = 30.0,
    tax_rate_pct: float = 0.0,
    currency: str = "PEN",
) -> dict[str, Any]:
    hours = _finite_nonnegative(total_hours, "total_hours")
    rate = _finite_nonnegative(hourly_rate_cost, "hourly_rate_cost", maximum=10_000_000)
    overhead_pct = _finite_nonnegative(overhead_percentage, "overhead_percentage", maximum=300)
    margin_pct = _finite_nonnegative(target_profit_margin_pct, "target_profit_margin_pct", maximum=99.9)
    tax_pct = _finite_nonnegative(tax_rate_pct, "tax_rate_pct", maximum=100)
    currency = currency.strip().upper()
    if not currency or len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency debe ser un código alfabético de 3 letras, por ejemplo PEN, USD o EUR.")

    direct = hours * rate
    overhead = direct * overhead_pct / 100
    cost_total = direct + overhead
    sale = cost_total / (1 - margin_pct / 100) if margin_pct < 100 else math.inf
    profit = sale - cost_total
    tax = sale * tax_pct / 100
    final_price = sale + tax
    if not all(math.isfinite(v) for v in (direct, overhead, cost_total, sale, profit, tax, final_price)):
        raise ValueError("Los parámetros generan un resultado numérico no finito; revise horas y tarifas.")
    effective_margin = (profit / sale * 100) if sale else 0.0
    return {
        "currency": currency,
        "total_hours": _round(hours),
        "hourly_rate_cost": _round(rate),
        "direct_cost": _round(direct),
        "overhead_percentage": _round(overhead_pct),
        "overhead_cost": _round(overhead),
        "subtotal_cost": _round(cost_total),
        "target_profit_margin_pct": _round(margin_pct),
        "profit_amount": _round(profit),
        "sale_price_before_tax": _round(sale),
        "tax_rate_pct": _round(tax_pct),
        "tax_amount": _round(tax),
        "final_price_client": _round(final_price),
        "effective_margin_pct": _round(effective_margin),
        "financial_note": "Impuesto calculado con la tasa indicada por el usuario. Verifique tratamiento tributario, moneda, condiciones de pago y retenciones aplicables antes de emitir una cotización formal.",
    }


def _add_business_days(start: date, days: int) -> date:
    current = start
    remaining = max(days, 0)
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _next_business_day(value: date) -> date:
    while value.weekday() >= 5:
        value += timedelta(days=1)
    return value


def generate_roadmap(
    total_buffered_hours: float,
    team_size: int,
    daily_effective_hours_per_dev: float = 6.0,
    start_date: str | None = None,
    team_availability_pct: float = 100.0,
) -> dict[str, Any]:
    hours = _finite_nonnegative(total_buffered_hours, "total_buffered_hours")
    if not isinstance(team_size, int) or isinstance(team_size, bool) or team_size < 1 or team_size > 100:
        raise ValueError("team_size debe ser un entero entre 1 y 100.")
    daily_hours = _finite_nonnegative(daily_effective_hours_per_dev, "daily_effective_hours_per_dev", maximum=24)
    if daily_hours <= 0:
        raise ValueError("daily_effective_hours_per_dev debe ser mayor que cero.")
    availability = _finite_nonnegative(team_availability_pct, "team_availability_pct", maximum=100)
    if availability <= 0:
        raise ValueError("team_availability_pct debe ser mayor que cero.")
    start = None
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError as exc:
            raise ValueError("start_date debe tener formato YYYY-MM-DD.") from exc
        start = _next_business_day(start)

    capacity_per_day = team_size * daily_hours * availability / 100
    days = math.ceil(hours / capacity_per_day) if hours else 0
    weeks = math.ceil(days / 5) if days else 0
    phases = [
        ("Fase 1: Análisis y arquitectura", 15),
        ("Fase 2: Desarrollo e integración", 55),
        ("Fase 3: Pruebas, ajustes y QA", 20),
        ("Fase 4: Despliegue y entrega", 10),
    ]
    # Hamilton/largest-remainder allocation reconciles phase days to the total duration,
    # even for short projects where independently rounding each phase would overcount.
    exact_days = [days * pct / 100 for _, pct in phases]
    phase_days_alloc = [math.floor(value) for value in exact_days]
    remaining_days = days - sum(phase_days_alloc)
    order = sorted(range(len(phases)), key=lambda idx: (-(exact_days[idx] - phase_days_alloc[idx]), idx))
    for idx in order[:remaining_days]:
        phase_days_alloc[idx] += 1
    phases_out: list[dict[str, Any]] = []
    cursor = start
    for idx, (name, pct) in enumerate(phases):
        phase_hours = hours * pct / 100
        phase_days = phase_days_alloc[idx]
        phase: dict[str, Any] = {
            "phase_name": name,
            "percentage_alloc": pct,
            "estimated_hours": _round(phase_hours),
            "estimated_days": phase_days,
        }
        if cursor is not None and phase_days:
            phase_start = cursor
            phase_end = _add_business_days(phase_start, max(phase_days - 1, 0))
            phase["start_date"] = phase_start.isoformat()
            phase["end_date"] = phase_end.isoformat()
            cursor = _next_business_day(_add_business_days(phase_end, 1))
        elif cursor is not None:
            phase["start_date"] = None
            phase["end_date"] = None
        phases_out.append(phase)
    return {
        "total_buffered_hours": _round(hours),
        "team_size": team_size,
        "daily_effective_hours_per_dev": _round(daily_hours),
        "team_availability_pct": _round(availability),
        "capacity_hours_per_working_day": _round(capacity_per_day),
        "total_days_required": days,
        "total_weeks_required": weeks,
        "start_date": start.isoformat() if start else None,
        "phases_timeline": phases_out,
        "calendar_assumptions": [
            "Se consideran días laborables de lunes a viernes; no se descuentan feriados ni vacaciones individuales.",
            "El cálculo de días es una aproximación de capacidad agregada; dependencias, ruta crítica, reuniones, onboarding y trabajo no paralelizable pueden extender el calendario.",
        ],
    }
