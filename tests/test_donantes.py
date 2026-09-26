import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from validation import validate_donor

SECRET = 'test-only-secret-key-with-more-than-32-characters'
PROFILE = dict(nombre='Juan Pérez', email='juan@example.com', telefono='5512345678', direccion='Calle Uno 123', tipo='persona')


@pytest.fixture()
def app(tmp_path):
    application = create_app({'TESTING': True, 'SECRET_KEY': SECRET, 'DATABASE': str(tmp_path / 'test.db')})
    with sqlite3.connect(application.config['DATABASE']) as connection:
        for username, role in [('admin','administrador'), ('juan','usuario'), ('ana','usuario')]:
            connection.execute('INSERT INTO usuarios(username,password_hash,rol) VALUES (?,?,?)',
                               (username, generate_password_hash('ClavePrueba123!'), role))
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def headers(client, username='juan'):
    response = client.post('/api/auth/login', json={'username':username,'password':'ClavePrueba123!'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json['token']}


def test_login_jwt(client):
    auth = headers(client)
    payload = jwt.decode(auth['Authorization'][7:], SECRET, algorithms=['HS256'], audience='donantes-api', issuer='modulo-donantes')
    assert payload['sub'] == '2' and payload['rol'] == 'usuario'
    assert client.get('/api/auth/me', headers=auth).json['username'] == 'juan'


def test_crud_and_admin(client):
    owner, admin = headers(client), headers(client, 'admin')
    result = client.post('/api/donantes', json=PROFILE, headers=owner)
    assert result.status_code == 201
    url = f"/api/donantes/{result.json['id']}"
    assert client.get(url, headers=owner).json['email'] == PROFILE['email']
    assert len(client.get('/api/donantes', headers=owner).json) == 1
    assert client.put(url, json={**PROFILE,'nombre':'Nombre Editado'}, headers=owner).json['nombre'] == 'Nombre Editado'
    assert client.patch(url+'/estado', json={'activo':False}, headers=owner).status_code == 403
    assert client.delete(url, headers=owner).status_code == 403
    assert client.patch(url+'/estado', json={'activo':False}, headers=admin).status_code == 200
    assert client.put(url, json=PROFILE, headers=owner).status_code == 403
    assert client.patch(url+'/estado', json={'activo':True}, headers=admin).json['activo'] == 1
    assert client.delete(url, headers=admin).status_code == 204
    assert client.get(url, headers=owner).status_code == 404


def test_isolation(client):
    owner, other, admin = headers(client), headers(client,'ana'), headers(client,'admin')
    donor = client.post('/api/donantes', json=PROFILE, headers=owner).json
    assert client.get('/api/donantes', headers=other).json == []
    for method in ['get','put']:
        assert getattr(client, method)(f"/api/donantes/{donor['id']}", headers=other, json=PROFILE).status_code == 403
    assert len(client.get('/api/donantes', headers=admin).json) == 1
    assert client.get('/api/usuarios', headers=other).status_code == 403
    assert len(client.get('/api/usuarios', headers=admin).json) == 3


@pytest.mark.parametrize('field,value', [('nombre',''),('nombre','a'),('nombre','a'*121),('nombre',12),('nombre',None),('nombre','a\nb'),('email','incorrecto'),('telefono','123'),('telefono','abcdefghij'),('tipo','otro'),('direccion','')])
def test_invalid_fields(client, field, value):
    assert client.post('/api/donantes', json={**PROFILE,field:value}, headers=headers(client)).status_code == 400


def test_duplicate(client):
    owner = headers(client)
    assert client.post('/api/donantes', json=PROFILE, headers=owner).status_code == 201
    assert client.post('/api/donantes', json={**PROFILE,'email':'otro@example.com'}, headers=owner).status_code == 409
    assert client.post('/api/donantes', json={**PROFILE,'email':'JUAN@EXAMPLE.COM'}, headers=headers(client,'ana')).status_code == 409


@pytest.mark.parametrize('body', [[], None, 'texto', 1, True])
def test_non_object(client, body):
    import json
    assert client.post('/api/donantes', data=json.dumps(body), content_type='application/json', headers=headers(client)).status_code == 400


def test_mass_assignment(client):
    for field,value in [('usuario_id',3),('activo',False),('rol','administrador')]:
        assert client.post('/api/donantes', json={**PROFILE,field:value}, headers=headers(client)).status_code == 400


@pytest.mark.parametrize('mode', ['missing','garbage','expired','forged','no-exp','bad-sub','unknown-user'])
def test_token_rejection(client, mode):
    now = datetime.now(timezone.utc)
    payload = dict(sub='2',iat=now,exp=now+timedelta(minutes=5),iss='modulo-donantes',aud='donantes-api')
    if mode == 'expired': payload['exp'] = now-timedelta(minutes=1)
    if mode == 'no-exp': del payload['exp']
    if mode == 'bad-sub': payload['sub'] = 'not-a-user'
    if mode == 'unknown-user': payload['sub'] = '999'
    token = jwt.encode(payload, SECRET if mode != 'forged' else 'different-secret-with-at-least-32-characters', algorithm='HS256')
    auth = {} if mode == 'missing' else {'Authorization':'Bearer '+('invalid' if mode == 'garbage' else token)}
    assert client.get('/api/donantes', headers=auth).status_code == 401


def test_login_validation_and_limit(client):
    assert client.post('/api/auth/login', json={'username':[],'password':4}).status_code == 400
    for _ in range(5):
        assert client.post('/api/auth/login', json={'username':'juan','password':'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'username':'juan','password':'ClavePrueba123!'}).status_code == 429
    assert client.post('/api/auth/login', json={'username':'unknown','password':'wrong'}).status_code == 401


def test_bad_requests(client):
    auth = headers(client)
    assert client.post('/api/donantes', data='bad', headers=auth).status_code == 400
    assert client.post('/api/donantes', data='{', content_type='application/json', headers=auth).status_code == 400
    assert client.post('/api/donantes', data='x'*20000, content_type='application/json', headers=auth).status_code == 413
    assert client.post('/health').status_code == 405
    assert client.get('/missing').status_code == 404


def test_persistence(app, client):
    client.post('/api/donantes', json=PROFILE, headers=headers(client))
    second = create_app({'TESTING':True,'SECRET_KEY':SECRET,'DATABASE':app.config['DATABASE']}).test_client()
    assert len(second.get('/api/donantes', headers=headers(second)).json) == 1


def test_admin_owner_and_status(client):
    auth = headers(client,'admin')
    for value,code in [(False,400),(-1,400),(10**30,400),(999,404)]:
        assert client.post('/api/donantes', json={**PROFILE,'usuario_id':value}, headers=auth).status_code == code
    result = client.post('/api/donantes', json={**PROFILE,'usuario_id':3}, headers=auth)
    assert result.status_code == 201 and result.json['usuario_id'] == 3
    url = f"/api/donantes/{result.json['id']}"
    assert client.patch(url+'/estado', json={'activo':'false'}, headers=auth).status_code == 400
    assert client.get('/api/donantes/'+str(10**30), headers=auth).status_code == 404
    for method,suffix in [('put',''),('patch','/estado'),('delete','')]:
        assert getattr(client,method)('/api/donantes/999'+suffix, json=PROFILE, headers=auth).status_code == 404


def test_headers_and_frontend(client):
    for path in ['/', '/app', '/static/app.js','/static/style.css','/health']:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert "script-src 'self'" in response.headers['Content-Security-Policy']
    assert 'Strict-Transport-Security' in client.get('/health', base_url='https://localhost').headers


def test_config_and_cli(app):
    with pytest.raises(RuntimeError): create_app({'SECRET_KEY':'short'})
    runner = app.test_cli_runner()
    args = ['crear-usuario','--username','nuevo','--password','UnaClaveLarga123!']
    assert runner.invoke(args=args).exit_code == 0
    assert runner.invoke(args=args).exit_code != 0
    assert runner.invoke(args=['crear-usuario','--username','xx','--password','x']).exit_code != 0


def test_validation_normalization():
    assert validate_donor({**PROFILE,'email':' JUAN@EXAMPLE.COM '})['email'] == 'juan@example.com'
