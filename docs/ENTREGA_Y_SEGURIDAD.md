# Evidencias y cierre

## Correcciones observadas en el código recibido

| Hallazgo de revisión | Corrección en esta entrega | Verificación |
|---|---|---|
| El dominio era Donaciones, no Donantes | Modelo y UI de perfiles de personas y empresas | CRUD y permisos en tests |
| Datos globales en memoria reiniciados en create_app | SQLite con restricciones únicas y claves foráneas | test_persistence |
| Clave JWT fija de respaldo y cuentas conocidas publicadas | Clave requerida por entorno y cuentas creadas explícitamente | test_config_and_cli |
| JWT sub numérico | sub textual y validación estricta de claims | test_login_jwt / test_token_rejection |
| Servidor arrancaba con debug=True | Waitress y debug desactivado | Revisión de configuración |
| Faltaba la entidad donante con correo único y propiedad | Validaciones, unicidad y control de propietario | test_duplicate / test_isolation |

Estos son hallazgos de revisión manual y pruebas, **no resultados de OWASP ZAP ni SonarQube**.

## Capturas que debe incluir la entrega

1. Inicio de sesión y vista de Usuario después de autenticarse.
2. Perfil propio creado y modificado.
3. Vista del Administrador con activar/desactivar y eliminar.
4. Herramientas del navegador, Network: login 200 (oculta el JWT completo); muestra sus claims decodificados localmente si lo necesitas.
5. Petición con token de Usuario a PATCH `/api/donantes/{id}/estado`, respuesta 403; misma operación con Administrador, respuesta 200.
6. Reporte de cobertura, ejecución de GitHub Actions completa y despliegue.

No publiques contraseñas, tokens completos ni datos personales reales en capturas.

## OWASP ZAP

Workflow manual `security.yml`: ejecuta un baseline **sin autenticación**, exclusivamente sobre la superficie pública. Genera HTML y JSON; alertas pueden dejar el job fallido, por lo que se conservan artefactos incluso en fallos. Para cubrir el módulo completo configura también un contexto autenticado en ZAP sobre tu instancia de prueba, inyecta `Authorization: Bearer <token>` y explora las rutas de la tabla API con cuentas de Usuario y Administrador. Usa datos desechables para un escaneo activo.

No se ejecutó ZAP en esta sesión. Completa con la salida real:

| Alerta ZAP | Riesgo informado | Causa confirmada | Corrección | Resultado del nuevo escaneo |
|---|---|---|---|---|
| Pendiente de ejecución | — | — | — | — |

## SonarQube

Configura un proyecto con key `modulo-donantes`, `SONAR_ENABLED=true`, variable `SONAR_HOST_URL` y secreto `SONAR_TOKEN` en GitHub. Ejecuta el workflow manual. SonarQube debe ser accesible desde el runner. `sonar-project.properties` importa el reporte de cobertura real. No se ejecutó el servidor SonarQube aquí.

| Métrica | Significado | Resultado real |
|---|---|---|
| Bugs / fiabilidad | Problemas potenciales de comportamiento | Pendiente |
| Vulnerabilidades | Fallos señalados por reglas de seguridad | Pendiente |
| Code smells | Problemas de mantenibilidad | Pendiente |
| Deuda técnica | Estimación de esfuerzo de corrección de la herramienta | Pendiente |
| Cobertura | Código cubierto por pruebas, importado por Sonar | Pendiente de importación; pytest disponible |

## Tiempos planeados frente a reales

No se proporcionó el cronograma del primer avance. Completa los datos reales del equipo; no uses la fecha de esta revisión como fecha histórica del proyecto.

| Actividad | Planeado | Real | Diferencia | Motivo |
|---|---|---|---|---|
| Desarrollo del módulo donantes | Por completar | Por completar | Por calcular | — |
| Pruebas y seguridad | Por completar | Por completar | Por calcular | — |
| Integración y despliegue | Por completar | Por completar | Por calcular | — |

## Lecciones de esta revisión

1. La entrega recibida implementaba donaciones. Revisar la entidad y el equipo asignado antes de desarrollar evita adaptar formularios y pruebas al final. En la siguiente iteración aprobar primero el contrato API y el modelo.
2. La aplicación reiniciaba sus diccionarios al crear la app. Persistir en SQLite y probar una segunda instancia evita confundir una demostración temporal con almacenamiento real. Agregar pruebas de persistencia desde el inicio.
3. La autenticación publicaba cuentas de prueba y aceptaba una clave fija por defecto. Separar configuración, creación de cuentas y código elimina esos valores del despliegue. Verificar las variables obligatorias antes de arrancar.

Estas lecciones corresponden al código revisado, no atribuyen experiencias o retrasos no documentados al equipo.

## Plan de mejora

| Oportunidad | Mejora y acción específica | Indicador | Beneficio |
|---|---|---|---|
| Token copiado sigue válido tras salir | Agregar revocación por jti y endpoint de logout | Token revocado devuelve 401 inmediatamente | Cierre de sesión efectivo en servidor |
| Directorio sin paginación | Agregar paginación y búsqueda por nombre/correo con índices | Página de 50 registros en <500 ms en el entorno acordado | Mejor desempeño con más donantes |
| SQLite y análisis externos pendientes | Ejecutar ZAP autenticado y SonarQube; definir umbrales y, si hay concurrencia alta, migrar a PostgreSQL | Sin riesgos altos confirmados; quality gate aprobado; prueba de carga documentada | Calidad verificable y capacidad de crecimiento |
| Falta trazabilidad de cambios administrativos | Añadir auditoría con actor, fecha y acción sin contraseñas ni tokens | 100% de cambios de estado y bajas auditados | Investigación de incidencias |

Innovación propuesta: preferencias de colaboración y recordatorios con consentimiento del donante, relacionados con solicitudes compatibles de las organizaciones. Medir la tasa de participación y permitir cancelar notificaciones; requiere integración con los otros módulos y no está implementada en esta versión.
