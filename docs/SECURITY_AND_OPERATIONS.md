# Seguridad y operación

## Límites deliberados

- No hay acceso a red, bases de datos, shell, navegador ni ejecución de código suministrado por el agente.
- Los archivos se escriben únicamente en `ESTIMATOR_OUTPUT_DIR`. Los argumentos de nombre se reducen a un nombre base sanitizado; no se aceptan directorios arbitrarios.
- Si el nombre de archivo ya existe, se selecciona un sufijo, no se sobrescribe.
- El conversor interpreta un subconjunto de Markdown; escapa texto antes de generar las etiquetas de formato que usa ReportLab.
- Las entradas numéricas tienen límites, deben ser finitas, y las tareas PERT deben respetar O <= M <= P.
- Las herramientas PDF devuelven la huella SHA-256 para identificar exactamente el artefacto generado.
- El directorio de salida y todos sus PDF contienen posibles datos comerciales/confidenciales. Asigna permisos restrictivos, evita un directorio web público y establece una política de retención.
- STDIO es el modo local recomendado. Si se usa HTTP, mantener el bind en loopback por defecto o proteger el acceso con autenticación/autorización y TLS en un gateway confiable antes de exponerlo.

## Lista de verificación antes de cotizar

1. Confirmar alcance incluido, exclusiones, criterios de aceptación y responsables de aprobación.
2. Validar horas O/M/P, dependencias, capacidad real, disponibilidad del cliente, QA y el buffer de contingencia.
3. Confirmar la moneda, coste horario, overhead, margen sobre venta y tratamiento tributario con la parte responsable.
4. Confirmar vigencia de la oferta, hitos/condiciones de pago, licencias y servicios de terceros, garantía, soporte, despliegue y rollback.
5. Abrir el PDF final, verificar números/formato y conseguir aprobación humana antes de enviarlo.

## Limitación

La protección de ruta del generador no reemplaza permisos del sistema operativo ni un aislamiento del proceso. La herramienta tampoco tiene autenticación propia configurada en modo STDIO, porque el control de acceso lo administra el host MCP local. Un despliegue HTTP necesita su propio diseño de identidad y seguridad antes de producción.
