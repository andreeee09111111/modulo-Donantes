# Ampliación del módulo de donantes

Esta versión añade el panel de donaciones solicitado: el donante registra bienes, elige una organización y conoce la dirección de destino. El administrador coordina el avance y cada movimiento queda en una línea de tiempo.

## Pruebas nuevas

| Caso | Comprobación | Resultado esperado | Prueba automatizada |
|---|---|---|---|
| DON-01 | Registro y ciclo hasta entrega | 201, destino correcto y cuatro eventos ordenados | test_complete_lifecycle_and_history |
| DON-02 | Privacidad de donaciones | Otro usuario obtiene lista vacía y 403 en detalle/cancelación | test_donation_privacy |
| DON-03 | Cancelación y estados terminales | Cancelación válida; no se puede reabrir ni saltar etapas | test_cancel_and_terminal_rules |
| DON-04 | Motivos y datos de estado | 400 en estado inválido o motivo insuficiente | test_status_validation |
| DON-05 | Validaciones unitarias parametrizadas | Rechazar cantidades, tipos, fechas y campos indebidos | test_donation_validation_unit |
| DON-06 | Recolección | Dirección obligatoria; no guardar dirección innecesaria en entrega en sede | test_validation_endpoints_and_pickup |
| DON-07 | Donante sin perfil/inactivo y destino inexistente | 409, 403 y 404 según escenario | test_creation_restrictions |
| DON-08 | Catálogo de destinos por rol | Usuario no puede crear/editar; destinos inactivos no reciben aportes | test_organization_permissions_and_inactive |
| DON-09 | Historial protegido | Cambiar catálogo no cambia el destino histórico; impedir borrar donante con aportes | test_destination_snapshot_and_prevent_history_deletion |
| DON-10 | Duplicados y registros inexistentes | 409 por nombres duplicados, 404 por IDs ausentes o enormes | test_organization_duplicates_and_missing |
| DON-11 | Persistencia | Donaciones conservadas entre instancias | test_persistence_of_donations |
| DON-12 | Actualización del esquema | Conservar usuarios existentes y crear tablas nuevas vacías | test_additive_migration_preserves_accounts |

Resultado obtenido y evidencia: la ejecución completa se guarda en `evidencias/pytest.txt` y `evidencias/resultados.xml`. Los casos nuevos y los anteriores aprobaron. La matriz original de donantes continúa en `MATRIZ_PRUEBAS.md`.

## Conservación de datos

Se agregan tablas `organizaciones`, `donaciones` y `seguimiento` mediante CREATE TABLE IF NOT EXISTS. No se reinician tablas anteriores. No se incluyen datos de demostración en la base del usuario. El destino de cada donación conserva nombre y dirección al momento del registro.

## Alcance de la entrega

Los bienes donados no se descuentan de inventario y no se integran con transportistas ni pagos. La fecha propuesta requiere coordinación. La gestión de destinos funciona dentro de esta aplicación; no presupone una conexión con módulos de otros equipos. Es posible sustituir el catálogo por una integración posterior conservando los contratos API.
