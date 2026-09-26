# Manos que Ayudan · Donantes y panel de donaciones

Aplicación Flask + SQLite + HTML/CSS/JavaScript. Esta versión amplía la gestión de donantes con registro de donaciones, organizaciones de destino y seguimiento hasta la entrega. Conserva las cuentas y perfiles de la versión anterior.

## Si ya lo tenías funcionando

1. Detén el servidor anterior con **Ctrl+C** en la terminal donde se ejecuta.
2. Desde la carpeta del proyecto, ejecuta:

```powershell
.\.venv\Scripts\python.exe iniciar.py
```

También puedes abrir `INICIAR.bat` con doble clic. Abre **http://127.0.0.1:5000/app** y actualiza con **Ctrl+F5**. Usa tus mismos usuarios y contraseñas.

La base `instance/donantes.db` se conserva. Al arrancar se agregan tablas nuevas; no se borran usuarios ni perfiles. `iniciar.py` conserva una clave local en `instance/local-secret.key` si no existe SECRET_KEY en el entorno. No compartas la carpeta `instance`. En producción configura SECRET_KEY mediante tu gestor de secretos.

## Empieza a usar el panel

1. Entra como **administrador** y abre **Destinos → Agregar organización**. Escribe el nombre, dirección de recepción, descripción y contacto de cada organización real.
2. Entra como **usuario** y completa **Mi perfil** si todavía no lo has registrado.
3. Pulsa **Nueva donación**. Indica el contenido, categoría, cantidad, unidad, fecha propuesta, organización y modalidad de entrega.
4. En **Mis donaciones** consulta el folio, destino y estado. Usa el buscador o el filtro por estado.
5. Pulsa **Ver seguimiento** para ver la dirección exacta, los detalles y la línea de tiempo.
6. El administrador abre la donación y actualiza su avance: **Aprobar → Marcar en camino → Confirmar entrega**. Puede añadir una nota en cada paso.

No se agregan organizaciones ni donaciones ficticias a tu base. Las capturas incluidas usan una base de demostración independiente. El catálogo estará vacío hasta que el administrador publique los destinos.

## Qué incluye

- **Resumen:** total de donaciones, aportes en proceso, entregas confirmadas, destinos elegidos y actividad reciente.
- **Mis donaciones:** historial propio con búsqueda por título, folio, destino o nombre del donante; filtro por estado; detalle y seguimiento.
- **Nueva donación:** alimentos, ropa, higiene, útiles u otros bienes. Cantidades enteras de 1 a 100000, unidades explícitas y fecha propuesta entre hoy y un año. No procesa dinero ni pagos.
- **Destino:** organización y dirección guardadas en cada donación. Si el catálogo cambia después, el historial conserva el destino registrado originalmente.
- **Entrega:** entrega en sede o solicitud de recolección en la dirección indicada. La fecha y la recolección deben ser coordinadas por el administrador; el sistema no contrata transportistas.
- **Administración:** todas las donaciones, gestión de organizaciones, perfiles de donantes y cambios de estado con notas.
- **Perfil:** datos de contacto, edición y activación/desactivación por administrador.
- **Seguridad:** JWT, roles, autorización por propietario, datos persistentes, validación en servidor y protección contra acceso a donaciones ajenas.

## Estados y permisos

| Estado actual | Siguiente estado permitido | Quién |
|---|---|---|
| Pendiente | Aprobada o rechazada | Administrador |
| Pendiente | Cancelada, con motivo | Donante propietario o Administrador |
| Aprobada | En camino | Administrador |
| Aprobada | Cancelada, con motivo | Donante propietario o Administrador |
| En camino | Entregada | Administrador |
| Entregada, rechazada o cancelada | Ninguno: estado final | — |

El registro inicia en pendiente. Una aprobación no cuenta como entrega. Las donaciones no se eliminan para preservar su historial. Un perfil con donaciones puede desactivarse, pero no eliminarse. Las organizaciones inactivas no admiten nuevos aportes; el historial previo sigue disponible.

## Instalación desde cero

Abre la carpeta en VS Code y usa PowerShell. Requiere Python 3.12 o superior. Si tu instalación no tiene el lanzador `py`, usa la ruta de tu `python.exe` seguida de `-m venv .venv`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\.venv\Scripts\python.exe -m flask --app app crear-usuario --username admin --rol administrador
.\.venv\Scripts\python.exe -m flask --app app crear-usuario --username juan --rol usuario
.\.venv\Scripts\python.exe iniciar.py
```

Los comandos `crear-usuario` se ejecutan solo una vez por cuenta. `--username` determina el usuario; el comando pide escribir y confirmar la contraseña (12–128 caracteres, no se muestra mientras escribes). No existen contraseñas predefinidas.

## API

Excepto login y health, todas las rutas requieren `Authorization: Bearer <JWT>`.

| Ruta | Método | Permiso |
|---|---|---|
| `/api/auth/login` | POST | Cuenta y contraseña válidas |
| `/api/auth/me` | GET | Sesión autenticada |
| `/api/donantes` | GET, POST | Perfil propio; Administrador gestiona otros |
| `/api/donantes/{id}` | GET, PUT | Propietario o Administrador |
| `/api/donantes/{id}` | DELETE | Administrador; solo sin historial |
| `/api/donantes/{id}/estado` | PATCH | Administrador |
| `/api/usuarios` | GET | Administrador |
| `/api/organizaciones` | GET | Usuario: activas; Administrador: todas |
| `/api/organizaciones` | POST | Administrador |
| `/api/organizaciones/{id}` | PUT | Administrador |
| `/api/organizaciones/{id}/estado` | PATCH | Administrador |
| `/api/donaciones` | GET | Usuario: propias; Administrador: todas |
| `/api/donaciones` | POST | Donante activo; Administrador indica donante_id |
| `/api/donaciones/{id}` | GET | Propietario o Administrador |
| `/api/donaciones/{id}/estado` | PATCH | Según la tabla de transiciones |

Ejemplo de alta de donación (usa un ID de organización existente y una fecha válida actual):

```json
{
  "titulo": "Ropa de invierno",
  "categoria": "ropa",
  "cantidad": 15,
  "unidad": "piezas",
  "organizacion_id": 1,
  "fecha_prevista": "AAAA-MM-DD",
  "modalidad": "recoleccion",
  "direccion_recoleccion": "Calle, número, colonia y ciudad",
  "descripcion": "Ropa limpia y en buen estado."
}
```

Para Administrador, agrega `donante_id`. El Usuario no puede enviarlo: la propiedad se determina desde su JWT. Cambio de estado: `{"estado":"aprobada","nota":"Entrega coordinada con la organización."}`. Cancelar o rechazar requiere motivo de al menos cinco caracteres.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -v --cov=app --cov=validation --cov=donations --cov-branch --cov-fail-under=90 --cov-report=term-missing --cov-report=xml:evidencias/coverage.xml --cov-report=html:evidencias/cobertura --junitxml=evidencias/resultados.xml
```

Resultados de esta versión: **65 pruebas aprobadas**, cobertura de backend **99,47 %** (líneas y ramas combinadas). Incluye pruebas del módulo anterior y nuevas pruebas de donaciones, destinos, transiciones, privacidad y migración aditiva. Ver `evidencias/pytest.txt` y abrir `evidencias/cobertura/index.html`. Las pruebas usan bases temporales separadas.

La interfaz también se comprobó en Microsoft Edge con Playwright: alta de organizaciones, perfil y donación, seguimiento completo, cancelación, filtros, privacidad y vista móvil. Reporte en `evidencias/prueba-navegador.json` y capturas PNG.

## CI/CD y Docker

Sube el contenido del proyecto a la raíz del repositorio, incluyendo `.github`. `ci.yml` ejecuta pruebas con cobertura, construye Docker, despliega un contenedor temporal en el runner y comprueba su disponibilidad. Publica informes e imagen como artefactos. Incluye ahora `donations.py` en build, cobertura y SonarQube.

Para Docker local configura SECRET_KEY y ejecuta `docker compose up --build -d`. El volumen mantiene SQLite. Crea usuarios con `docker compose exec donantes flask --app app crear-usuario --username admin --rol administrador`.

El despliegue persistente opcional requiere `DEPLOY_ENABLED=true`, secreto `DEPLOY_HOOK`, variable `HEALTH_URL`, un proveedor configurado y volumen `/data`. Un health check no demuestra por sí solo que esté publicado el último commit: adjunta el registro del proveedor. No se ejecutaron Docker ni GitHub Actions en esta sesión.

ZAP y SonarQube siguen configurados para ejecutarse en tu entorno. El baseline público de ZAP no analiza automáticamente todas las rutas autenticadas: configura también un contexto con JWT para los roles. No se inventan resultados externos. Consulta `docs/ENTREGA_Y_SEGURIDAD.md`.

## Consideraciones de uso

- JWT de 30 minutos. La sesión se conserva solo en memoria del navegador; al recargar debes iniciar sesión. Cerrar sesión borra el token del navegador, pero un token copiado sigue válido hasta vencer.
- Contraseñas con hash, SQL parametrizado, límites de entrada, CSP y respuestas sin caché. Cinco fallos de login por cuenta bloquean 15 minutos.
- El historial refleja los cambios registrados por el administrador; no representa rastreo GPS ni confirmación externa del transporte.
- Respalda `instance/donantes.db` con el servidor detenido. No incluyas esa carpeta al compartir el proyecto.
- El sistema consulta el listado completo; para miles de registros conviene añadir paginación en servidor y migrar a PostgreSQL si aumenta la concurrencia.
