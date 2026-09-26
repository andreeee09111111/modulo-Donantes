"""Inicio local con la base existente y clave persistente, sin crear cuentas demo."""
import os
import secrets
from pathlib import Path

from waitress import serve
from app import create_app


if __name__ == '__main__':
    folder = Path(__file__).resolve().parent / 'instance'
    folder.mkdir(exist_ok=True)
    key_file = folder / 'local-secret.key'
    if not os.environ.get('SECRET_KEY'):
        if not key_file.exists():
            try:
                with key_file.open('x', encoding='utf-8') as file:
                    file.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        os.environ['SECRET_KEY'] = key_file.read_text(encoding='utf-8').strip()
    print('Manos que Ayudan · Panel de donaciones', flush=True)
    print('Abre http://127.0.0.1:5000/app · Para detener: Ctrl+C', flush=True)
    serve(create_app(), host='127.0.0.1', port=5000)
