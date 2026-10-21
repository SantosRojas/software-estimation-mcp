# Estado de validación

## Cómo validar este proyecto

El entorno se define únicamente en `pyproject.toml` + `uv.lock` (fuente única de dependencias). No existe `requirements.txt`.

```powershell
uv sync --extra dev   # crea/actualiza .venv con fastmcp, reportlab, pytest y ruff
uv run pytest -q      # suite completa
uv run ruff check src tests
```

## Comprobaciones ejecutadas

- Instalación reproducible desde `uv.lock` en un `.venv` limpio (sin heredar paquetes de otros proyectos).
- Handshake real con FastMCP 4.1.3: las 14 herramientas se enumeran vía `mcp.list_tools()`.
- Pipeline end-to-end: PERT → buffers → cotización → roadmap → PDF de propuesta, cotización, plan de acción y Markdown libre. Cabecera PDF válida y huella SHA-256 devuelta.
- Separación de canales: en STDIO, `stdout` queda en 0 bytes durante la ejecución (transporta el protocolo) y los logs de observabilidad salen por `stderr`.
- Pruebas automatizadas: 23/23.
- Lint (`ruff check`): sin errores.
- Protección contra path traversal verificada empíricamente y cubierta por test de regresión.

## Cobertura de pruebas

- `tests/test_estimation.py`: fórmulas PERT, validación de orden O<=M<=P, buffers aditivos, margen sobre venta e impuesto, reparto de fases con días cortos, validación de WBS, no-inferencia de categorías de alcance y orden del registro de riesgos.
- `tests/test_documents.py`: generación de PDF, neutralización de path traversal (`../../`, rutas absolutas, Windows), no sobrescritura, rechazo de nombres vacíos, buffers en Markdown y advertencia de datos faltantes.
- `tests/test_server.py`: `compare_scenarios` (cálculo, límites de 1 y 10 escenarios, entrada no numérica).

## Limitación conocida

La suite se ejecuta en el host; no hay aún un despliegue HTTP con autenticación real probado. Para red, ver `docs/SECURITY_AND_OPERATIONS.md`.
