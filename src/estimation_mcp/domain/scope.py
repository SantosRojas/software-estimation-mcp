"""Herramientas deterministas de análisis de alcance y riesgos."""
from __future__ import annotations

from typing import Any

CHECKLIST = {
    "objetivos_y_usuarios": ["objetivo de negocio", "usuarios/roles involucrados", "resultado verificable esperado"],
    "alcance_y_aceptacion": ["incluido y excluido", "criterios de aceptación", "flujos alternativos y casos límite"],
    "datos": ["fuentes y propietarios de datos", "calidad/volumen/retención", "migración o carga inicial, si aplica"],
    "integraciones": ["sistemas externos y responsables", "contratos/API y sandbox", "límites, autenticación y gestión de errores"],
    "seguridad_y_privacidad": ["roles y permisos", "datos personales o sensibles", "auditoría y requisitos de seguridad"],
    "plataforma_y_operación": ["entornos disponibles", "restricciones de hosting/red", "monitorización, soporte y recuperación"],
    "calidad_y_entrega": ["rendimiento y disponibilidad esperados", "matriz de pruebas", "responsable de aprobación y ventana de despliegue"],
    "gestión": ["fecha objetivo y motivo", "disponibilidad de usuarios clave", "dependencias, presupuesto y restricciones"],
}


def analyze_scope_gaps(requirement_description: str, provided_details: list[str] | None = None, confirmed_categories: list[str] | None = None) -> dict[str, Any]:
    desc = requirement_description.strip()
    if not desc:
        raise ValueError("requirement_description no puede estar vacío.")
    if len(desc) > 12_000:
        raise ValueError("La descripción supera el límite de 12 000 caracteres.")
    if provided_details and len(provided_details) > 100:
        raise ValueError("Se permiten hasta 100 detalles proporcionados.")
    if confirmed_categories and len(confirmed_categories) > len(CHECKLIST):
        raise ValueError("Demasiadas categorías confirmadas.")
    known = set(CHECKLIST)
    confirmed = set(confirmed_categories or [])
    unknown = confirmed - known
    if unknown:
        raise ValueError(f"Categorías desconocidas: {', '.join(sorted(unknown))}.")
    details = [x.strip() for x in (provided_details or []) if x and x.strip()]
    categories = []
    for category, questions in CHECKLIST.items():
        categories.append({
            "category": category,
            "status": "confirmado_por_usuario" if category in confirmed else "pendiente_de_validacion",
            "questions_to_resolve": [] if category in confirmed else questions,
        })
    pending = [c for c in categories if c["status"] != "confirmado_por_usuario"]
    return {
        "requirement_summary": desc,
        "provided_details": details,
        "coverage_categories": categories,
        "pending_categories_count": len(pending),
        "clarification_questions": [q for c in pending for q in c["questions_to_resolve"]],
        "recommended_next_step": "Realizar una sesión breve de descubrimiento y convertir las respuestas en criterios de aceptación, exclusiones y supuestos aprobados.",
        "limitation_note": "La herramienta no infiere que un aspecto esté resuelto porque aparezca implícito en una descripción; solo marca una categoría como confirmada cuando el solicitante la declara explícitamente.",
    }


def build_risk_register(
    codebase_type: str = "modern",
    has_third_party_integrations: bool = False,
    data_migration_required: bool = False,
    unclear_requirements: bool = False,
    production_criticality: str = "medium",
    external_risks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if codebase_type not in {"modern", "legacy", "scratch"}:
        raise ValueError("codebase_type debe ser modern, legacy o scratch.")
    if production_criticality not in {"low", "medium", "high", "mission_critical"}:
        raise ValueError("production_criticality debe ser low, medium, high o mission_critical.")
    risks: list[dict[str, Any]] = []

    def add(risk_id: str, title: str, probability: int, impact: int, mitigation: str, owner: str = "Líder técnico / PM") -> None:
        score = probability * impact
        level = "ALTO" if score >= 15 else "MEDIO" if score >= 8 else "BAJO"
        risks.append({"risk_id": risk_id, "title": title, "probability_1_to_5": probability, "impact_1_to_5": impact, "score": score, "level": level, "mitigation": mitigation, "suggested_owner": owner})

    if codebase_type == "legacy":
        add("R-LEG-01", "Comportamiento implícito o deuda técnica del legado", 4, 4, "Hacer inventario de dependencias, reproducir comportamiento actual y validar en entorno similar a producción.")
    if codebase_type == "scratch":
        add("R-NEW-01", "Descubrimiento incompleto en desarrollo desde cero", 3, 4, "Validar prototipo, arquitectura mínima y criterios de aceptación antes de comprometer el alcance completo.")
    if has_third_party_integrations:
        add("R-INT-01", "Dependencia de API o proveedor externo", 4, 4, "Confirmar SLA, límites, sandbox, credenciales, reintentos, idempotencia y plan manual de contingencia.")
    if data_migration_required:
        add("R-DAT-01", "Migración de datos incompleta o inconsistente", 3, 5, "Ensayar migración con copia anonimizada, reconciliar conteos y definir backup, rollback y ventana aprobada.", "Responsable de datos / DBA")
    if unclear_requirements:
        add("R-SCP-01", "Cambios de alcance por requisitos ambiguos", 4, 4, "Cerrar criterios de aceptación, exclusiones, responsables de aprobación y proceso de control de cambios.", "Product owner / PM")
    criticality_risk = {"low": (1, 2), "medium": (2, 3), "high": (3, 5), "mission_critical": (4, 5)}[production_criticality]
    if production_criticality in {"high", "mission_critical"}:
        add("R-OPS-01", "Incidente durante el despliegue o interrupción del servicio", *criticality_risk, "Exigir checklist de liberación, monitoreo, responsables de guardia, backup verificable y rollback ensayado.", "Operaciones / responsable de servicio")
    for idx, item in enumerate(external_risks or [], start=1):
        title = str(item.get("title", "")).strip()
        mitigation = str(item.get("mitigation", "")).strip()
        probability = item.get("probability_1_to_5", 3)
        impact = item.get("impact_1_to_5", 3)
        if not title or len(title) > 240:
            raise ValueError(f"Riesgo externo {idx}: title es obligatorio y admite hasta 240 caracteres.")
        if not mitigation or len(mitigation) > 1500:
            raise ValueError(f"Riesgo externo {idx}: mitigation es obligatoria y admite hasta 1 500 caracteres.")
        if not isinstance(probability, int) or isinstance(probability, bool) or not 1 <= probability <= 5:
            raise ValueError(f"Riesgo externo {idx}: probability_1_to_5 debe estar entre 1 y 5.")
        if not isinstance(impact, int) or isinstance(impact, bool) or not 1 <= impact <= 5:
            raise ValueError(f"Riesgo externo {idx}: impact_1_to_5 debe estar entre 1 y 5.")
        add(f"R-EXT-{idx:02d}", title, probability, impact, mitigation, str(item.get("owner", "Por asignar"))[:120])
    risks.sort(key=lambda r: (-r["score"], r["risk_id"]))
    return {
        "risk_register": risks,
        "risk_count": len(risks),
        "high_risk_count": sum(1 for r in risks if r["level"] == "ALTO"),
        "risk_scale": "Probabilidad e impacto se califican de 1 a 5; score = probabilidad x impacto. Bajo: 1-7; medio: 8-14; alto: 15-25.",
        "risk_note": "Registro inicial de riesgos típicos basado únicamente en los factores ingresados; debe revisarse con el equipo y el cliente.",
    }
