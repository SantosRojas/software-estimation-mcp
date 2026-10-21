# Referencia de herramientas MCP

Todas las herramientas usan JSON tipado generado a partir de las firmas Python y validado por FastMCP. Las respuestas de cálculo son deterministas; la interpretación de texto natural, la recopilación de supuestos y la aprobación final corresponden al agente y al usuario.

## 1. Secuencia principal

### `wbs_breakdown`
- Entrada: `requirement_description`, `work_type`.
- Tipos: `feature`, `bugfix`, `legacy_patch`, `refactor`, `integration`.
- Salida: `project_type`, `recommended_wbs[]`, `usage_note`.
- Use la WBS como borrador y elimine o agregue tareas conforme se confirme el alcance.

### `calculate_pert`
- Entrada: `tasks[]` con `task_id`, `name`, `optimistic_hours`, `most_likely_hours`, `pessimistic_hours`.
- Límites: de 1 a 300 tareas; IDs únicos; horas finitas no negativas y O <= M <= P.
- Salida: horas esperadas por tarea, SD, varianza, nivel de riesgo, total e intervalos orientativos.

### `apply_buffers`
- Entrada: `pert_total_hours`, `codebase_type`, `has_third_party_integrations`, `qa_level`, `pm_buffer_pct`, `extra_contingency_pct`.
- Porcentajes por defecto del documento fuente: scratch 10%, modern 5%, legacy 25%, integraciones 20% si aplican, PM 15%, QA basic 10%, standard 15%, rigorous 25%.
- La contingencia adicional empieza en 0% para evitar duplicarla sin intención.

### `calculate_quotation`
- Entrada: `total_hours`, `hourly_rate_cost`, `overhead_percentage` (15), `target_profit_margin_pct` (30), `tax_rate_pct` (0), `currency` (PEN).
- La tasa de impuesto es explícita; el MCP no presume que aplique IGV/IVA ni determina obligaciones tributarias.
- `target_profit_margin_pct` significa margen sobre precio de venta, no markup sobre costes.

### `generate_roadmap`
- Entrada: `total_buffered_hours`, `team_size`, `daily_effective_hours_per_dev` (6), `start_date` opcional, `team_availability_pct` (100).
- Devuelve días y semanas, horas y fechas por fase. Excluye festivos, vacaciones y análisis formal de dependencias.

## 2. Análisis profesional

### `analyze_scope_gaps`
Recibe una descripción y detalles conocidos opcionales. No deduce que una categoría está aprobada a partir del texto; `confirmed_categories` sirve para registrar confirmaciones explícitas. La salida incluye categorías, preguntas y siguiente paso sugerido.

Categorías admitidas: `objetivos_y_usuarios`, `alcance_y_aceptacion`, `datos`, `integraciones`, `seguridad_y_privacidad`, `plataforma_y_operación`, `calidad_y_entrega`, `gestión`.

### `build_risk_register`
Recibe codebase, integraciones, migración, claridad de requisitos y criticidad operativa; admite riesgos adicionales con `title`, `mitigation`, `probability_1_to_5`, `impact_1_to_5` y `owner` opcional. Escala de 1 a 5, score = probabilidad x impacto; bajo 1-7, medio 8-14, alto 15-25.

### `compare_scenarios`
Acepta de 1 a 10 objetos de escenario. Cada uno requiere `total_hours` (esfuerzo que ya incorpora buffers) y `hourly_rate_cost`; admite `name`, overhead, margen, impuesto, moneda, equipo, horas efectivas y disponibilidad. Cada escenario devuelve cotización y duración resumida.

## 3. Documentos

### `generate_proposal_markdown`
Requiere `client_name`, `project_title`, `wbs_data`, `pert_data`, `quotation_data` y `roadmap_data`. Admite `buffer_data` para documentar el desglose de buffers; también `out_of_scope`, `assumptions`, `risk_data`, vigencia, pago, garantía y referencia.

### `generate_proposal_pdf`
Usa la misma estructura y persiste un PDF con resumen ejecutivo, alcance, supuestos, exclusiones, PERT, cronograma, inversión, riesgos, aceptación y notas de validez/condiciones.

### `generate_action_plan_markdown` / `generate_action_plan_pdf`
Requiere cliente, título y roadmap; permite definir `action_items` como objetos con `action`, `owner`, `priority`, `done_when`, además de dependencias, decisiones y criterios de éxito. Si no se proporcionan acciones, usa una lista base que debe revisarse.

### `generate_quote_pdf`
Cotización independiente con cliente, proyecto, estructura de `quotation_data`, esfuerzo total y `scope_summary`; admite supuestos, exclusiones, vigencia y condiciones de pago.

### `render_markdown_pdf`
Convierte contenido Markdown controlado a PDF. No permite incluir recursos web, incrustar HTML externo ni ejecutar código.

## 4. Resultado al crear un PDF

Devuelve `status`, `document_title`, `file_name`, `file_path`, `file_uri`, `size_bytes`, `sha256`, `created_at` y una nota de acceso local. La ruta es del host que ejecuta el MCP; no presuponga que el cliente MCP remoto podrá descargarla automáticamente.
