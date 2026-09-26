"""Módulo de donantes: aplicación Flask con SQLite y JWT."""
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import click
import jwt
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from validation import object_body, validate_donor
from donations import register_donations


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(g.app_database, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def create_app(config=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY'),
                      DATABASE=os.environ.get('DATABASE', str(Path(app.instance_path) / 'donantes.db')),
                      MAX_CONTENT_LENGTH=16384, JWT_MINUTES=30)
    app.config.update(config or {})
    if not isinstance(app.config['SECRET_KEY'], str) or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Configura SECRET_KEY con al menos 32 caracteres aleatorios.')
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def prepare():
        g.app_database = app.config['DATABASE']

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()

    with app.app_context():
        g.app_database = app.config['DATABASE']
        db().executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          rol TEXT NOT NULL CHECK(rol IN ('usuario','administrador')));
        CREATE TABLE IF NOT EXISTS donantes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
          nombre TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
          telefono TEXT NOT NULL, direccion TEXT NOT NULL,
          tipo TEXT NOT NULL CHECK(tipo IN ('persona','empresa')),
          activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
          creado TEXT NOT NULL, actualizado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS intentos (
          username TEXT PRIMARY KEY, cantidad INTEGER NOT NULL, inicio REAL NOT NULL);
        ''')

    def error(message, status):
        return jsonify(error=message), status

    def authenticated(admin=False):
        def decorate(function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                parts = request.headers.get('Authorization', '').split()
                if len(parts) != 2 or parts[0].lower() != 'bearer':
                    return error('Se requiere Authorization: Bearer <token>.', 401)
                try:
                    payload = jwt.decode(parts[1], app.config['SECRET_KEY'], algorithms=['HS256'],
                                         issuer='modulo-donantes', audience='donantes-api',
                                         options={'require': ['sub', 'exp', 'iat', 'iss', 'aud']})
                    subject = payload['sub']
                    if not isinstance(subject, str) or not subject.isascii() or not subject.isdigit() or len(subject) > 10:
                        raise jwt.InvalidTokenError()
                except jwt.InvalidTokenError:
                    return error('Token inválido o vencido. Inicia sesión nuevamente.', 401)
                g.user = db().execute('SELECT id, username, rol FROM usuarios WHERE id=?', (subject,)).fetchone()
                if g.user is None:
                    return error('Usuario no disponible.', 401)
                if admin and g.user['rol'] != 'administrador':
                    return error('Acción exclusiva del Administrador.', 403)
                return function(*args, **kwargs)
            return wrapped
        return decorate

    @app.errorhandler(HTTPException)
    def http_error(exception):
        return error(exception.description, exception.code)

    @app.errorhandler(ValueError)
    def invalid(exception):
        return error(str(exception), 400)

    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(_exception):
        return error('Ya existe un donante con ese correo o para ese usuario.', 409)

    @app.errorhandler(500)
    def internal(_exception):
        return error('Error interno. Intenta nuevamente.', 500)

    @app.after_request
    def security(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cache-Control'] = 'no-store'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get('/')
    @app.get('/app')
    def index():
        return app.send_static_file('index.html')

    @app.get('/health')
    def health():
        db().execute('SELECT 1')
        return jsonify(status='ok')

    @app.post('/api/auth/login')
    def login():
        data = object_body(request)
        username, password = data.get('username'), data.get('password')
        if not isinstance(username, str) or not 3 <= len(username.strip()) <= 50 or not isinstance(password, str) or not 1 <= len(password) <= 128:
            raise ValueError('Usuario o contraseña con formato inválido.')
        username = username.strip().lower()
        now = time.time()
        connection = db()
        # Transacción para que los intentos simultáneos no evadan el límite.
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('DELETE FROM intentos WHERE inicio < ?', (now - 900,))
        attempt = connection.execute('SELECT cantidad FROM intentos WHERE username=?', (username,)).fetchone()
        if attempt and attempt['cantidad'] >= 5:
            connection.commit()
            return error('Demasiados intentos. Espera 15 minutos.', 429)
        user = connection.execute('SELECT * FROM usuarios WHERE username=?', (username,)).fetchone()
        valid = check_password_hash(user['password_hash'] if user else app.config['DUMMY_HASH'], password)
        if not user or not valid:
            connection.execute('INSERT INTO intentos VALUES (?,1,?) ON CONFLICT(username) DO UPDATE SET cantidad=cantidad+1', (username, now))
            connection.commit()
            return error('Credenciales incorrectas.', 401)
        connection.execute('DELETE FROM intentos WHERE username=?', (username,))
        connection.commit()
        issued = datetime.now(timezone.utc)
        token = jwt.encode({'sub': str(user['id']), 'rol': user['rol'], 'iat': issued,
                            'exp': issued + timedelta(minutes=app.config['JWT_MINUTES']),
                            'iss': 'modulo-donantes', 'aud': 'donantes-api', 'jti': secrets.token_hex(16)},
                           app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify(token=token, usuario={key: user[key] for key in ('id', 'username', 'rol')})

    app.config['DUMMY_HASH'] = generate_password_hash(secrets.token_urlsafe(32))

    @app.get('/api/auth/me')
    @authenticated()
    def me():
        return jsonify(dict(g.user))

    @app.get('/api/usuarios')
    @authenticated(admin=True)
    def users():
        return jsonify([dict(row) for row in db().execute('SELECT id,username,rol FROM usuarios ORDER BY id')])

    @app.get('/api/donantes')
    @authenticated()
    def listing():
        query, params = 'SELECT * FROM donantes', ()
        if g.user['rol'] != 'administrador':
            query, params = query + ' WHERE usuario_id=?', (g.user['id'],)
        return jsonify([dict(row) for row in db().execute(query + ' ORDER BY id DESC', params)])

    def find(donor_id):
        if donor_id > 2147483647:
            return None, error('Donante no encontrado.', 404)
        row = db().execute('SELECT * FROM donantes WHERE id=?', (donor_id,)).fetchone()
        if row is None:
            return None, error('Donante no encontrado.', 404)
        if g.user['rol'] != 'administrador' and row['usuario_id'] != g.user['id']:
            return None, error('No puedes acceder a otro donante.', 403)
        return row, None

    @app.get('/api/donantes/<int:donor_id>')
    @authenticated()
    def detail(donor_id):
        row, failure = find(donor_id)
        return failure if failure else jsonify(dict(row))

    @app.post('/api/donantes')
    @authenticated()
    def create():
        data = object_body(request)
        allowed = {'usuario_id'} if g.user['rol'] == 'administrador' else set()
        clean = validate_donor(data, allowed)
        owner = data.get('usuario_id', g.user['id'])
        if type(owner) is not int or not 1 <= owner <= 2147483647:
            raise ValueError('usuario_id debe ser un entero entre 1 y 2147483647.')
        if not db().execute('SELECT id FROM usuarios WHERE id=?', (owner,)).fetchone():
            return error('Usuario no encontrado.', 404)
        now = datetime.now(timezone.utc).isoformat()
        with db() as connection:
            cursor = connection.execute('INSERT INTO donantes (usuario_id,nombre,email,telefono,direccion,tipo,creado,actualizado) VALUES (?,?,?,?,?,?,?,?)',
                                        (owner, *clean.values(), now, now))
        return jsonify(dict(db().execute('SELECT * FROM donantes WHERE id=?', (cursor.lastrowid,)).fetchone())), 201

    @app.put('/api/donantes/<int:donor_id>')
    @authenticated()
    def update(donor_id):
        row, failure = find(donor_id)
        if failure:
            return failure
        if not row['activo'] and g.user['rol'] != 'administrador':
            return error('El perfil está inactivo. Contacta al Administrador.', 403)
        clean = validate_donor(object_body(request))
        with db() as connection:
            connection.execute('UPDATE donantes SET nombre=?,email=?,telefono=?,direccion=?,tipo=?,actualizado=? WHERE id=?',
                               (*clean.values(), datetime.now(timezone.utc).isoformat(), donor_id))
        return detail(donor_id)

    @app.patch('/api/donantes/<int:donor_id>/estado')
    @authenticated(admin=True)
    def status(donor_id):
        _, failure = find(donor_id)
        if failure:
            return failure
        data = object_body(request)
        if set(data) != {'activo'} or type(data['activo']) is not bool:
            raise ValueError('Envía únicamente activo como true o false.')
        with db() as connection:
            connection.execute('UPDATE donantes SET activo=?,actualizado=? WHERE id=?',
                               (int(data['activo']), datetime.now(timezone.utc).isoformat(), donor_id))
        return detail(donor_id)

    @app.delete('/api/donantes/<int:donor_id>')
    @authenticated(admin=True)
    def delete(donor_id):
        _, failure = find(donor_id)
        if failure:
            return failure
        if db().execute('SELECT 1 FROM donaciones WHERE donante_id=? LIMIT 1', (donor_id,)).fetchone():
            return error('Este donante tiene historial de donaciones. Puedes desactivarlo, pero no eliminarlo.', 409)
        with db() as connection:
            connection.execute('DELETE FROM donantes WHERE id=?', (donor_id,))
        return '', 204

    @app.cli.command('crear-usuario')
    @click.option('--username', prompt=True)
    @click.option('--rol', type=click.Choice(['usuario', 'administrador']), default='usuario')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(username, rol, password):
        username = username.strip().lower()
        if not 3 <= len(username) <= 50 or not 12 <= len(password) <= 128:
            raise click.ClickException('Usuario: 3–50 caracteres. Contraseña: 12–128 caracteres.')
        g.app_database = app.config['DATABASE']
        try:
            with db() as connection:
                connection.execute('INSERT INTO usuarios(username,password_hash,rol) VALUES (?,?,?)',
                                   (username, generate_password_hash(password), rol))
        except sqlite3.IntegrityError as exc:
            raise click.ClickException('Ese usuario ya existe.') from exc
        click.echo('Usuario creado.')

    register_donations(app, db, authenticated, error)
    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False)
