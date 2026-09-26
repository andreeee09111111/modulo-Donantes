# Matriz de pruebas

Casos automatizados con pytest; el resultado detallado de cada ejecución se guarda en `evidencias/resultados.xml`. La numeración agrupa parámetros y varios pasos relacionados; no representa el número de funciones de prueba.

| ID | Funcionalidad / rol | Escenario y datos | Esperado | Automatización |
|---|---|---|---|---|
| CP-01 | Login / ambos | Cuenta válida | 200 y JWT con sub textual, rol, exp, iss y aud | test_login_jwt |
| CP-02 | Alta / Usuario | Datos completos válidos | 201, asociado al usuario autenticado | test_crud_and_admin |
| CP-03 | Edición / Usuario | Nombre modificado en perfil propio | 200 y persistencia del nuevo nombre | test_crud_and_admin |
| CP-04 | Estado y baja / Usuario | Intentar PATCH o DELETE | 403 sin ejecutar acción | test_crud_and_admin |
| CP-05 | Estado y baja / Administrador | Desactivar, activar, eliminar | 200, 200 y 204; luego 404 | test_crud_and_admin |
| CP-06 | Privacidad / Usuario | Listar, leer o editar perfil ajeno | Lista vacía; detalle y edición 403 | test_isolation |
| CP-07 | Campos obligatorios | Vacíos, null, número, texto corto o largo | 400 | test_invalid_fields |
| CP-08 | Formatos | Correo inválido, teléfono corto o letras, tipo inválido | 400 | test_invalid_fields |
| CP-09 | Duplicados | Dos perfiles de una cuenta o mismo correo con otras mayúsculas | 409 | test_duplicate |
| CP-10 | Entrada JSON | Array, null, texto, número o booleano | 400 | test_non_object |
| CP-11 | Asignación indebida / Usuario | Enviar usuario_id, activo o rol | 400 | test_mass_assignment |
| CP-12 | JWT | Ausente, malformado, expirado, firma incorrecta, sin exp, sub inválido o inexistente | 401 | test_token_rejection |
| CP-13 | Login | Formato inválido, contraseña incorrecta, seis intentos | 400, 401 y 429 | test_login_validation_and_limit |
| CP-14 | Protocolo HTTP | Sin JSON, JSON roto, >16 KiB, método o ruta inexistente | 400, 400, 413, 405, 404 | test_bad_requests |
| CP-15 | Persistencia | Crear una segunda instancia sobre la misma BD | Perfil conservado | test_persistence |
| CP-16 | Alta / Administrador | Propietario bool, negativo o inexistente; cuenta válida | 400, 400, 404; creación 201 | test_admin_owner_and_status |
| CP-17 | Estado / Administrador | activo como texto; registro inexistente | 400; 404 | test_admin_owner_and_status |
| CP-18 | Seguridad de respuestas | HTML, CSS, JS y health; HTTPS | 200, CSP, nosniff y HSTS en HTTPS | test_headers_and_frontend |
| CP-19 | Configuración y cuentas | Secreto corto, cuenta nueva, repetida o inválida | Arranque rechazado; alta exitosa; errores CLI | test_config_and_cli |
| CP-20 | Normalización / unidad | Correo con espacios y mayúsculas | Correo normalizado | test_validation_normalization |

Resultados obtenidos, estado y evidencia: véase `evidencias/RESUMEN.md` y el reporte JUnit que identifica cada prueba y parámetro. Las capturas de interfaz se documentan aparte y no se deducen de los tests de API.
