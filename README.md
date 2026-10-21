# Software Estimation MCP

Servidor MCP en Python para convertir requerimientos de desarrollo de software en una estimación trazable, riesgos, cronograma, cotización y documentos PDF listos para revisión comercial.

## Decisión de ecosistema

**Python + FastMCP 4 + Pydantic + ReportLab.** El dominio contiene cálculos deterministas y validaciones, y ReportLab genera PDF directamente sin necesitar Chromium, Node, fuentes descargadas o un servicio de conversión externo. El núcleo de negocio está separado de la capa MCP para que se pueda probar sin iniciar un agente.

Requiere Python 3.11 o superior. La línea `fastmcp>=4,<5` corresponde a la versión estable actual de FastMCP a octubre de 2026. Para conectores de escritorio, el transporte por defecto es `stdio`; para despliegues en red se ofrece HTTP Streamable.

## Funcionalidades y herramientas MCP

| Herramienta | Para qué sirve |
|---|---|
| `wbs_breakdown` | Genera una WBS inicial para una nueva funcionalidad, bugfix, parche legado, refactor o integración. |
| `calculate_pert` | Calcula tiempo esperado, desviación, varianza, nivel de riesgo e intervalos orientativos a partir de O/M/P. |
| `apply_buffers` | Aplica buffers de codebase, integraciones, PM, QA y contingencia explícita. Los porcentajes se suman de forma aditiva sobre PERT, como en la especificación. |
| `calculate_quotation` | Calcula coste directo, overhead, precio a partir de margen sobre venta, impuesto indicado y total. |
| `generate_roadmap` | Estima días laborables y distribuye esfuerzo entre análisis, desarrollo, QA y despliegue, con fechas cuando se proporciona inicio. |
| `analyze_scope_gaps` | Produce preguntas de descubrimiento para evitar comprometer plazo/precio con alcance ambiguo. |
| `build_risk_register` | Genera un registro de riesgos típico, puntuación, nivel, mitigación y propietario sugerido. |
| `compare_scenarios` | Compara hasta diez escenarios de coste/precio y calendario bajo los supuestos recibidos. |
| `generate_proposal_markdown` | Unifica WBS, PERT, precio, calendario, exclusiones, supuestos y riesgos en Markdown. |
| `generate_proposal_pdf` | Genera una propuesta técnica/comercial en PDF. |
| `generate_action_plan_markdown` | Genera un plan de acción con fases, responsables, dependencias y evidencia de cierre. |
| `generate_action_plan_pdf` | Genera un plan de acción independiente en PDF. |
| `generate_quote_pdf` | Genera una cotización PDF independiente, con desglose financiero, supuestos y exclusiones. |
| `render_markdown_pdf` | Convierte Markdown a PDF para otros documentos. Admite títulos, listas y tablas; no descarga ni ejecuta HTML externo. |

## Instalación en Windows (PowerShell)

Desde la carpeta del proyecto descomprimido:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# Prueba rápida del núcleo de negocio y del generador PDF
python -m pytest -q

# Iniciar el MCP en STDIO (normalmente lo inicia el cliente MCP)
python -m estimation_mcp.server
```

Si la política de PowerShell bloquea la activación, puede usar directamente el ejecutable virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

## Conectar con un cliente MCP

Configura `mcpServers` en el cliente (Cursor, Claude Desktop u otro cliente compatible). Cambia las rutas por la ubicación real del proyecto:

```json
{
  "mcpServers": {
    "software-estimation": {
      "command": "C:\\Projects\\software-estimation-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "estimation_mcp.server"],
      "env": {
        "ESTIMATOR_OUTPUT_DIR": "C:\\Projects\\software-estimation-mcp\\output",
        "ESTIMATOR_TRANSPORT": "stdio"
      }
    }
  }
}
```

El cliente ejecuta un proceso independiente. Reinicia el cliente MCP después de modificar su configuración. No escribas mensajes de depuración en `stdout` de un servidor `stdio`; ese canal transporta el protocolo.

## Transporte HTTP Streamable

Solo para despliegues en red. Primero instala el paquete en un entorno virtual del host; después configura:

```powershell
$env:ESTIMATOR_TRANSPORT = "http"
$env:ESTIMATOR_HTTP_HOST = "127.0.0.1"
$env:ESTIMATOR_HTTP_PORT = "8000"
$env:ESTIMATOR_OUTPUT_DIR = "C:\\ProgramData\\SoftwareEstimationMCP\\output"
python -m estimation_mcp.server
```

El endpoint queda en `http://127.0.0.1:8000/mcp`. El valor predeterminado es loopback intencionalmente. **No lo expongas directamente a Internet**: ponlo detrás de un gateway/proxy con autenticación, autorización, TLS, límites de solicitudes y registro operativo. Para una instalación remota real, habilita la autenticación de FastMCP o la del gateway y prueba los permisos del directorio de documentos antes de producción.

## Configuración de archivos de salida

Los PDF se guardan en `ESTIMATOR_OUTPUT_DIR`; por defecto, en `./output` relativo al directorio desde donde se inició el proceso. La herramienta devuelve ruta absoluta, URI local, nombre, tamaño y SHA-256. El cliente/usuario debe tener acceso a la ruta del servidor: la ruta local no se transfiere automáticamente al agente remoto.

Los nombres se convierten a slug seguro, se ignoran directorios indicados por el modelo y se usa un nombre alternativo si el archivo ya existe. No se sobrescriben documentos anteriores de forma silenciosa.

## Flujo de trabajo recomendado

1. Ejecutar `analyze_scope_gaps` con el requerimiento disponible. Resolver con el usuario las preguntas críticas; no marcar una categoría como cerrada por inferencia.
2. Ejecutar `wbs_breakdown` y ajustar las tareas al alcance confirmado. Solicitar O/M/P por tarea y ejecutar `calculate_pert`.
3. Ejecutar `apply_buffers` usando el tipo de código, integraciones y QA reales. La contingencia extra debe justificarse para no duplicar reservas.
4. Ejecutar `calculate_quotation` con tarifa de coste, overhead, margen, moneda y tasa tributaria confirmados. La tasa fiscal por defecto es 0; la herramienta no adivina el tratamiento tributario.
5. Ejecutar `generate_roadmap` con capacidad efectiva, disponibilidad real y fecha objetivo cuando se conozca.
6. Usar `build_risk_register`; revisar probabilidad/impacto y asignar responsables reales.
7. Generar `generate_proposal_markdown` y revisar supuestos, exclusiones, alcance, impuesto, cronograma y condiciones comerciales.
8. Generar `generate_proposal_pdf` para la propuesta completa, `generate_quote_pdf` para una cotización corta o `generate_action_plan_pdf` para el plan interno/de ejecución.
9. Revisar el PDF final manualmente antes de enviarlo al cliente.

## Metodología y límites importantes

- **PERT:** `E = (O + 4M + P) / 6`; `SD = (P - O) / 6`; se combina varianza asumiendo independencia. `E + SD` y `E + 2SD` son referencias aproximadas, no promesas de fecha ni intervalos calibrados para todos los proyectos.
- **Buffers:** los porcentajes se suman sobre la estimación base, de acuerdo con la especificación original; no se aplican en cascada. No dupliques una reserva ya incluida en cada tarea.
- **Margen:** el precio antes de impuestos es `coste total / (1 - margen objetivo)`, es decir, margen sobre venta y no recargo sobre coste.
- **Calendario:** se estiman días laborables lunes-viernes, sin festivos, vacaciones, ruta crítica o asignaciones parciales por persona. Es una primera aproximación de capacidad.
- **Cotización:** la moneda predeterminada es `PEN`, pero la tasa tributaria predeterminada es `0%` y debe indicarse explícitamente. Verifica la normativa aplicable, IGV/IVA, retenciones, licencias, alcance, plazos, vigencia y condiciones de pago.
- La WBS, preguntas y riesgos son ayudas para el profesional; no reemplazan el juicio técnico, la validación con el cliente ni un contrato aprobado.

## Pruebas

```powershell
python -m pytest -q
```

Las pruebas cubren fórmulas, validaciones de entradas, suma de buffers, cálculo de margen e impuesto, reparto de días de fases, preguntas de alcance, orden del registro de riesgos y escritura de PDF. Los archivos `examples/demo-*.pdf` son ejemplos ficticios, no cotizaciones reales.

## Estructura

```text
src/estimation_mcp/
  domain/estimation.py       # cálculos de estimación y cronograma
  domain/scope.py            # preguntas de alcance y registro de riesgos
  services/documents.py      # Markdown y PDF
  server.py                  # herramientas y transporte MCP
  cli.py                     # entry point opcional
 tests/                       # pruebas automatizadas
 examples/                    # configuración y PDFs ficticios
 docs/                        # guía y referencia de herramientas
```
