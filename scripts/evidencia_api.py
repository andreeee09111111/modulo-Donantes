"""Evidencia reproducible sin cuentas persistentes ni exposición de JWT completos."""
import json
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import jwt
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def main():
    with TemporaryDirectory() as folder:
        secret = 'clave-exclusiva-de-prueba-no-usar-en-servidor'
        app = create_app({'TESTING':True,'SECRET_KEY':secret,'DATABASE':str(Path(folder)/'demo.db')})
        with sqlite3.connect(app.config['DATABASE']) as connection:
            for username, role in [('admin','administrador'),('usuario','usuario')]:
                connection.execute('INSERT INTO usuarios(username,password_hash,rol) VALUES (?,?,?)',
                                   (username, generate_password_hash('PruebaTemporal123!'),role))
        connection.close()
        client = app.test_client()
        evidence, tokens = [], {}
        for username in ['usuario','admin']:
            response = client.post('/api/auth/login',json={'username':username,'password':'PruebaTemporal123!'})
            assert response.status_code == 200
            token = response.json['token']
            tokens[username] = {'Authorization':'Bearer '+token}
            claims = jwt.decode(token,secret,algorithms=['HS256'],audience='donantes-api',issuer='modulo-donantes')
            evidence.append({'accion':'login '+username,'http':response.status_code,'claims_verificados':claims})
        profile = dict(nombre='Donante de prueba',email='demo@example.com',telefono='5512345678',direccion='Calle de prueba 123',tipo='persona')
        response = client.post('/api/donantes',json=profile,headers=tokens['usuario'])
        assert response.status_code == 201
        evidence.append({'accion':'alta propia Usuario','http':response.status_code,'resultado':response.json})
        url = f"/api/donantes/{response.json['id']}/estado"
        for username, expected in [('usuario',403),('admin',200)]:
            response = client.patch(url,json={'activo':False},headers=tokens[username])
            assert response.status_code == expected
            evidence.append({'accion':'desactivar como '+username,'http':response.status_code,'resultado':response.json})
        destination = Path(__file__).resolve().parents[1]/'evidencias'/'api.json'
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Evidencia real guardada en evidencias/api.json; base temporal eliminada.')


if __name__ == '__main__':
    main()
