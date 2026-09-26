"""Destinos, donaciones y seguimiento persistente con autorización por propietario."""
import sqlite3
from datetime import date, datetime, timezone

from flask import g, jsonify, request

from validation import object_body

CATEGORIES = ('alimentos', 'ropa', 'higiene', 'utiles', 'otros')
UNITS = ('piezas', 'paquetes', 'cajas', 'kilogramos', 'litros')
TRANSITIONS = {
    'pendiente': ('aprobada', 'rechazada', 'cancelada'),
    'aprobada': ('en_camino', 'cancelada'),
    'en_camino': ('entregada',),
    'entregada': (), 'rechazada': (), 'cancelada': (),
}
SCHEMA = '''
CREATE TABLE IF NOT EXISTS organizaciones (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
 direccion TEXT NOT NULL, descripcion TEXT NOT NULL,
 contacto TEXT NOT NULL, activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
);
CREATE TABLE IF NOT EXISTS donaciones (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 donante_id INTEGER NOT NULL REFERENCES donantes(id) ON DELETE RESTRICT,
 organizacion_id INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE RESTRICT,
 destino_nombre TEXT NOT NULL, destino_direccion TEXT NOT NULL,
 titulo TEXT NOT NULL, categoria TEXT NOT NULL,
 cantidad INTEGER NOT NULL CHECK(cantidad BETWEEN 1 AND 100000),
 unidad TEXT NOT NULL, descripcion TEXT NOT NULL,
 modalidad TEXT NOT NULL, direccion_recoleccion TEXT NOT NULL,
 fecha_prevista TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'pendiente'
 CHECK(estado IN ('pendiente','aprobada','en_camino','entregada','rechazada','cancelada')),
 creado TEXT NOT NULL, actualizado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_donaciones_donante ON donaciones(donante_id);
CREATE TABLE IF NOT EXISTS seguimiento (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 donacion_id INTEGER NOT NULL REFERENCES donaciones(id) ON DELETE RESTRICT,
 estado TEXT NOT NULL, nota TEXT NOT NULL,
 actor_id INTEGER NOT NULL REFERENCES usuarios(id), fecha TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_seguimiento_donacion ON seguimiento(donacion_id);
'''


def text_field(data, key, minimum, maximum, default=None):
    value = data.get(key, default)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f'{key}: escribe entre {minimum} y {maximum} caracteres.')
    value = value.strip()
    if any(ord(char) < 32 and char not in '\n\r\t' for char in value):
        raise ValueError(f'{key}: caracteres no permitidos.')
    return value


def positive_id(value, field):
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise ValueError(f'{field}: debe ser un entero positivo válido.')
    return value


def organization_data(data):
    if set(data) - {'nombre', 'direccion', 'descripcion', 'contacto'}:
        raise ValueError('La organización contiene campos no permitidos.')
    return {key: text_field(data, key, low, high) for key, low, high in (
        ('nombre', 3, 120), ('direccion', 5, 250), ('descripcion', 10, 600), ('contacto', 5, 150))}


def donation_data(data, is_admin):
    fields = {'organizacion_id','titulo','categoria','cantidad','unidad','descripcion',
              'modalidad','direccion_recoleccion','fecha_prevista'}
    if is_admin:
        fields.add('donante_id')
    if set(data) - fields:
        raise ValueError('La donación contiene campos no permitidos.')
    organization_id = positive_id(data.get('organizacion_id'), 'organizacion_id')
    title = text_field(data, 'titulo', 3, 120)
    category = text_field(data, 'categoria', 1, 20)
    if category not in CATEGORIES:
        raise ValueError('Selecciona una categoría válida.')
    quantity = data.get('cantidad')
    if type(quantity) is not int or not 1 <= quantity <= 100000:
        raise ValueError('cantidad: debe ser un entero entre 1 y 100000.')
    unit = text_field(data, 'unidad', 1, 20)
    if unit not in UNITS:
        raise ValueError('Selecciona una unidad válida.')
    description = text_field(data, 'descripcion', 0, 1000, '')
    mode = text_field(data, 'modalidad', 1, 30)
    if mode not in ('entrega_en_sede', 'recoleccion'):
        raise ValueError('Selecciona entrega en sede o recolección.')
    address = text_field(data, 'direccion_recoleccion', 5 if mode == 'recoleccion' else 0, 250, '')
    planned = text_field(data, 'fecha_prevista', 10, 10)
    try:
        parsed = date.fromisoformat(planned)
    except ValueError as exc:
        raise ValueError('fecha_prevista: usa el formato AAAA-MM-DD.') from exc
    if parsed < date.today() or (parsed - date.today()).days > 365:
        raise ValueError('La fecha debe estar entre hoy y los próximos 365 días.')
    return dict(organizacion_id=organization_id, titulo=title, categoria=category,
                cantidad=quantity, unidad=unit, descripcion=description, modalidad=mode,
                direccion_recoleccion=address if mode == 'recoleccion' else '', fecha_prevista=planned)


def register_donations(app, db, authenticated, error):
    with app.app_context():
        g.app_database = app.config['DATABASE']
        db().executescript(SCHEMA)

    def is_admin():
        return g.user['rol'] == 'administrador'

    def get_organization(identifier):
        if identifier > 2147483647:
            return None
        return db().execute('SELECT * FROM organizaciones WHERE id=?', (identifier,)).fetchone()

    @app.get('/api/organizaciones')
    @authenticated()
    def organizations():
        query = 'SELECT * FROM organizaciones'
        if not is_admin():
            query += ' WHERE activo=1'
        return jsonify([dict(row) for row in db().execute(query + ' ORDER BY nombre')])

    @app.post('/api/organizaciones')
    @authenticated(admin=True)
    def create_organization():
        data = organization_data(object_body(request))
        try:
            with db() as connection:
                cursor = connection.execute('INSERT INTO organizaciones(nombre,direccion,descripcion,contacto) VALUES (?,?,?,?)', tuple(data.values()))
        except sqlite3.IntegrityError:
            return error('Ya existe una organización con ese nombre.', 409)
        return jsonify(dict(get_organization(cursor.lastrowid))), 201

    @app.put('/api/organizaciones/<int:identifier>')
    @authenticated(admin=True)
    def update_organization(identifier):
        if not get_organization(identifier):
            return error('Organización no encontrada.', 404)
        data = organization_data(object_body(request))
        try:
            with db() as connection:
                connection.execute('UPDATE organizaciones SET nombre=?,direccion=?,descripcion=?,contacto=? WHERE id=?', (*data.values(), identifier))
        except sqlite3.IntegrityError:
            return error('Ya existe una organización con ese nombre.', 409)
        return jsonify(dict(get_organization(identifier)))

    @app.patch('/api/organizaciones/<int:identifier>/estado')
    @authenticated(admin=True)
    def organization_status(identifier):
        if not get_organization(identifier):
            return error('Organización no encontrada.', 404)
        data = object_body(request)
        if set(data) != {'activo'} or type(data['activo']) is not bool:
            raise ValueError('Envía únicamente activo como true o false.')
        with db() as connection:
            connection.execute('UPDATE organizaciones SET activo=? WHERE id=?', (int(data['activo']), identifier))
        return jsonify(dict(get_organization(identifier)))

    select_donations = '''SELECT d.*, p.nombre AS donante_nombre, p.usuario_id
                         FROM donaciones d JOIN donantes p ON p.id=d.donante_id'''

    def find_donation(identifier):
        if identifier > 2147483647:
            return None, error('Donación no encontrada.', 404)
        row = db().execute(select_donations + ' WHERE d.id=?', (identifier,)).fetchone()
        if row is None:
            return None, error('Donación no encontrada.', 404)
        if not is_admin() and row['usuario_id'] != g.user['id']:
            return None, error('No puedes acceder a donaciones de otro donante.', 403)
        return row, None

    def serialize(row):
        result = dict(row)
        result['folio'] = f"DON-{row['id']:05d}"
        options = TRANSITIONS[row['estado']]
        result['acciones'] = list(options) if is_admin() else (['cancelada'] if 'cancelada' in options else [])
        return result

    @app.get('/api/donaciones')
    @authenticated()
    def donation_list():
        query, args = select_donations, ()
        if not is_admin():
            query += ' WHERE p.usuario_id=?'
            args = (g.user['id'],)
        return jsonify([serialize(row) for row in db().execute(query + ' ORDER BY d.id DESC', args)])

    @app.get('/api/donaciones/<int:identifier>')
    @authenticated()
    def donation_detail(identifier):
        row, failure = find_donation(identifier)
        if failure:
            return failure
        result = serialize(row)
        result['seguimiento'] = [dict(event) for event in db().execute(
            'SELECT estado,nota,fecha FROM seguimiento WHERE donacion_id=? ORDER BY id', (identifier,))]
        return jsonify(result)

    @app.post('/api/donaciones')
    @authenticated()
    def create_donation():
        body = object_body(request)
        data = donation_data(body, is_admin())
        connection = db()
        # Evita que una desactivación simultánea se intercale con el registro.
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            if is_admin():
                donor_id = positive_id(body.get('donante_id'), 'donante_id')
                donor = connection.execute('SELECT * FROM donantes WHERE id=?', (donor_id,)).fetchone()
            else:
                donor = connection.execute('SELECT * FROM donantes WHERE usuario_id=?', (g.user['id'],)).fetchone()
            if donor is None:
                return error('Primero registra el perfil del donante.', 409)
            if not donor['activo']:
                return error('El perfil del donante está inactivo.', 403)
            organization = get_organization(data['organizacion_id'])
            if organization is None:
                return error('La organización de destino no existe.', 404)
            if not organization['activo']:
                return error('La organización no está recibiendo donaciones.', 409)
            now = datetime.now(timezone.utc).isoformat()
            cursor = connection.execute('''INSERT INTO donaciones
                (donante_id,organizacion_id,destino_nombre,destino_direccion,titulo,categoria,
                 cantidad,unidad,descripcion,modalidad,direccion_recoleccion,fecha_prevista,creado,actualizado)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (donor['id'], data['organizacion_id'], organization['nombre'], organization['direccion'],
                 data['titulo'], data['categoria'], data['cantidad'], data['unidad'], data['descripcion'],
                 data['modalidad'], data['direccion_recoleccion'], data['fecha_prevista'], now, now))
            identifier = cursor.lastrowid
            connection.execute('INSERT INTO seguimiento(donacion_id,estado,nota,actor_id,fecha) VALUES (?,?,?,?,?)',
                               (identifier, 'pendiente', 'Donación registrada. Pendiente de revisión del administrador.', g.user['id'], now))
        return donation_detail(identifier), 201

    @app.patch('/api/donaciones/<int:identifier>/estado')
    @authenticated()
    def donation_status(identifier):
        data = object_body(request)
        if set(data) - {'estado','nota'}:
            raise ValueError('Solo se permite estado y nota.')
        target = text_field(data, 'estado', 1, 20)
        if target not in TRANSITIONS:
            raise ValueError('Estado inválido.')
        note = text_field(data, 'nota', 0, 500, '')
        if not is_admin() and target != 'cancelada':
            return error('Solo el Administrador puede actualizar el seguimiento.', 403)
        if target in ('rechazada','cancelada') and len(note) < 5:
            raise ValueError('Escribe un motivo de al menos 5 caracteres.')
        with db() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row, failure = find_donation(identifier)
            if failure:
                return failure
            if target not in TRANSITIONS[row['estado']]:
                return error('Ese cambio de estado ya no está permitido. Actualiza la lista.', 409)
            now = datetime.now(timezone.utc).isoformat()
            connection.execute('UPDATE donaciones SET estado=?,actualizado=? WHERE id=?', (target, now, identifier))
            connection.execute('INSERT INTO seguimiento(donacion_id,estado,nota,actor_id,fecha) VALUES (?,?,?,?,?)',
                               (identifier, target, note or 'Estado actualizado por el Administrador.', g.user['id'], now))
        return donation_detail(identifier)
