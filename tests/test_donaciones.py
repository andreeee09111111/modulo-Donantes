import sqlite3
from datetime import date, timedelta

import pytest

from test_donantes import app, client, headers, PROFILE
from donations import donation_data, organization_data

ORGANIZATION = dict(nombre='Comedor de prueba', direccion='Avenida Solidaria 123, Ciudad', descripcion='Recibe alimentos para familias de la comunidad.', contacto='contacto@example.com')


@pytest.fixture()
def scenario(client):
    owner, administrator, other = headers(client), headers(client,'admin'), headers(client,'ana')
    donor = client.post('/api/donantes',json=PROFILE,headers=owner)
    assert donor.status_code == 201
    organization = client.post('/api/organizaciones',json=ORGANIZATION,headers=administrator)
    assert organization.status_code == 201
    body = dict(organizacion_id=organization.json['id'],titulo='Paquetes de arroz',categoria='alimentos',
                cantidad=5,unidad='paquetes',descripcion='Paquetes cerrados, sin caducar.',modalidad='entrega_en_sede',fecha_prevista=date.today().isoformat())
    return dict(owner=owner,admin=administrator,other=other,donor=donor.json,organization=organization.json,body=body)


def create(client, scenario, **changes):
    result = client.post('/api/donaciones',json={**scenario['body'],**changes},headers=scenario['owner'])
    assert result.status_code == 201, result.json
    return result.json


def test_complete_lifecycle_and_history(client, scenario):
    donation = create(client, scenario)
    assert donation['folio'].startswith('DON-')
    assert donation['estado'] == 'pendiente'
    assert donation['destino_nombre'] == ORGANIZATION['nombre']
    assert donation['destino_direccion'] == ORGANIZATION['direccion']
    assert len(donation['seguimiento']) == 1
    url = f"/api/donaciones/{donation['id']}"
    assert client.patch(url+'/estado',json={'estado':'aprobada'},headers=scenario['owner']).status_code == 403
    for target in ['aprobada','en_camino','entregada']:
        response = client.patch(url+'/estado',json={'estado':target,'nota':'Actualización de prueba'},headers=scenario['admin'])
        assert response.status_code == 200
        assert response.json['estado'] == target
    assert response.json['acciones'] == []
    assert [entry['estado'] for entry in response.json['seguimiento']] == ['pendiente','aprobada','en_camino','entregada']
    assert client.get(url,headers=scenario['owner']).json['estado'] == 'entregada'
    assert len(client.get('/api/donaciones',headers=scenario['admin']).json) == 1


def test_donation_privacy(client, scenario):
    donation = create(client, scenario)
    url = f"/api/donaciones/{donation['id']}"
    assert client.get('/api/donaciones',headers=scenario['other']).json == []
    assert client.get(url,headers=scenario['other']).status_code == 403
    assert client.patch(url+'/estado',json={'estado':'cancelada','nota':'Intento ajeno'},headers=scenario['other']).status_code == 403
    assert client.get(url,headers=scenario['owner']).json['estado'] == 'pendiente'
    assert client.get('/api/donaciones').status_code == 401
    assert client.get('/api/organizaciones').status_code == 401


def test_cancel_and_terminal_rules(client, scenario):
    donation = create(client, scenario)
    url = f"/api/donaciones/{donation['id']}/estado"
    assert client.patch(url,json={'estado':'entregada'},headers=scenario['admin']).status_code == 409
    assert client.patch(url,json={'estado':'cancelada','nota':'Cambio de planes'},headers=scenario['owner']).status_code == 200
    assert client.patch(url,json={'estado':'aprobada'},headers=scenario['admin']).status_code == 409
    assert client.patch(url,json={'estado':'cancelada','nota':'Cambio de planes'},headers=scenario['owner']).status_code == 409
    assert len(client.get(url.removesuffix('/estado'),headers=scenario['owner']).json['seguimiento']) == 2


def test_status_validation(client, scenario):
    donation = create(client, scenario)
    url = f"/api/donaciones/{donation['id']}/estado"
    for data in [{'estado':'inventado'},{'estado':'rechazada'},{'estado':'cancelada','nota':'no'}, {'estado':'aprobada','cantidad':100}]:
        assert client.patch(url,json=data,headers=scenario['admin']).status_code == 400
    assert client.patch(url,json={'estado':'rechazada','nota':'No se acepta este producto.'},headers=scenario['admin']).status_code == 200
    assert client.patch(url,json={'estado':'aprobada'},headers=scenario['admin']).status_code == 409


@pytest.mark.parametrize('field,value', [
    ('titulo',''),('titulo','a'*121),('cantidad',0),('cantidad',True),('cantidad',1.5),('cantidad',100001),
    ('categoria','dinero'),('unidad','monedas'),('modalidad','otro'),('organizacion_id',True),('organizacion_id',10**30),
    ('fecha_prevista','2025-99-99'),('fecha_prevista',(date.today()-timedelta(days=1)).isoformat()),
    ('fecha_prevista',(date.today()+timedelta(days=366)).isoformat()),('descripcion','a'*1001),
    ('estado','entregada'),('donante_id',999),('titulo','abc\x00'),
])
def test_donation_validation_unit(field, value):
    data = dict(organizacion_id=1,titulo='Donación de prueba',categoria='ropa',cantidad=3,unidad='piezas',modalidad='entrega_en_sede',fecha_prevista=date.today().isoformat())
    with pytest.raises(ValueError):
        donation_data({**data,field:value},False)


def test_validation_endpoints_and_pickup(client, scenario):
    assert client.post('/api/donaciones',json={**scenario['body'],'cantidad':False},headers=scenario['owner']).status_code == 400
    assert client.post('/api/donaciones',json={**scenario['body'],'modalidad':'recoleccion'},headers=scenario['owner']).status_code == 400
    donation = create(client,scenario,modalidad='recoleccion',direccion_recoleccion='Calle del donante 456')
    assert donation['direccion_recoleccion'] == 'Calle del donante 456'
    assert create(client,scenario,direccion_recoleccion='No debe guardarse')['direccion_recoleccion'] == ''


def test_creation_restrictions(client, scenario):
    assert client.post('/api/donaciones',json=scenario['body'],headers=scenario['other']).status_code == 409
    body = {**scenario['body'],'donante_id':scenario['donor']['id']}
    assert client.post('/api/donaciones',json=body,headers=scenario['admin']).status_code == 201
    assert client.post('/api/donaciones',json={**body,'donante_id':999},headers=scenario['admin']).status_code == 409
    assert client.post('/api/donaciones',json={**scenario['body'],'organizacion_id':999},headers=scenario['owner']).status_code == 404
    client.patch(f"/api/donantes/{scenario['donor']['id']}/estado",json={'activo':False},headers=scenario['admin'])
    assert client.post('/api/donaciones',json=scenario['body'],headers=scenario['owner']).status_code == 403


def test_organization_permissions_and_inactive(client, scenario):
    url = f"/api/organizaciones/{scenario['organization']['id']}"
    assert client.post('/api/organizaciones',json=ORGANIZATION,headers=scenario['owner']).status_code == 403
    assert client.put(url,json=ORGANIZATION,headers=scenario['owner']).status_code == 403
    assert client.patch(url+'/estado',json={'activo':False},headers=scenario['owner']).status_code == 403
    assert client.patch(url+'/estado',json={'activo':'false'},headers=scenario['admin']).status_code == 400
    assert client.patch(url+'/estado',json={'activo':False},headers=scenario['admin']).status_code == 200
    assert client.get('/api/organizaciones',headers=scenario['owner']).json == []
    assert len(client.get('/api/organizaciones',headers=scenario['admin']).json) == 1
    assert client.post('/api/donaciones',json=scenario['body'],headers=scenario['owner']).status_code == 409


def test_destination_snapshot_and_prevent_history_deletion(client, scenario):
    donation = create(client,scenario)
    org_url = f"/api/organizaciones/{scenario['organization']['id']}"
    assert client.put(org_url,json={**ORGANIZATION,'nombre':'Nueva organización','direccion':'Nueva dirección 100'},headers=scenario['admin']).status_code == 200
    assert client.get(f"/api/donaciones/{donation['id']}",headers=scenario['owner']).json['destino_direccion'] == ORGANIZATION['direccion']
    assert client.delete(f"/api/donantes/{scenario['donor']['id']}",headers=scenario['admin']).status_code == 409
    assert len(client.get('/api/donaciones',headers=scenario['owner']).json) == 1


def test_organization_duplicates_and_missing(client, scenario):
    assert client.post('/api/organizaciones',json=ORGANIZATION,headers=scenario['admin']).status_code == 409
    second = client.post('/api/organizaciones',json={**ORGANIZATION,'nombre':'Otro comedor'},headers=scenario['admin']).json
    assert client.put(f"/api/organizaciones/{second['id']}",json=ORGANIZATION,headers=scenario['admin']).status_code == 409
    for identifier in [999,10**30]:
        assert client.put(f'/api/organizaciones/{identifier}',json=ORGANIZATION,headers=scenario['admin']).status_code == 404
        assert client.patch(f'/api/organizaciones/{identifier}/estado',json={'activo':False},headers=scenario['admin']).status_code == 404
        assert client.get(f'/api/donaciones/{identifier}',headers=scenario['owner']).status_code == 404
        assert client.patch(f'/api/donaciones/{identifier}/estado',json={'estado':'aprobada'},headers=scenario['admin']).status_code == 404


def test_organization_validation_unit():
    with pytest.raises(ValueError): organization_data({**ORGANIZATION,'activo':True})
    with pytest.raises(ValueError): organization_data({**ORGANIZATION,'descripcion':'corto'})
    assert organization_data(ORGANIZATION) == ORGANIZATION


def test_persistence_of_donations(app, client, scenario):
    from app import create_app
    create(client,scenario)
    second = create_app({'TESTING':True,'SECRET_KEY':app.config['SECRET_KEY'],'DATABASE':app.config['DATABASE']})
    next_client = second.test_client()
    response = next_client.get('/api/donaciones',headers=headers(next_client))
    assert len(response.json) == 1
    assert response.json[0]['destino_nombre'] == ORGANIZATION['nombre']


def test_additive_migration_preserves_accounts(tmp_path):
    from app import create_app
    database = str(tmp_path/'old.db')
    connection = sqlite3.connect(database)
    connection.executescript('''CREATE TABLE usuarios(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, rol TEXT NOT NULL);
    INSERT INTO usuarios VALUES(1,'existing','unchanged-hash','usuario');''')
    connection.close()
    create_app({'TESTING':True,'SECRET_KEY':'migration-test-secret-with-at-least-32-characters','DATABASE':database})
    connection = sqlite3.connect(database)
    assert connection.execute('SELECT username,password_hash FROM usuarios').fetchone() == ('existing','unchanged-hash')
    assert connection.execute('SELECT count(*) FROM donaciones').fetchone()[0] == 0
    connection.close()
