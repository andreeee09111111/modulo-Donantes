import re


def object_body(request):
    if not request.is_json:
        raise ValueError('Se requiere Content-Type: application/json.')
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError('El cuerpo debe ser un objeto JSON.')
    return data


def validate_donor(data, extra_allowed=None):
    limits = {'nombre': (2, 120), 'email': (5, 254), 'telefono': (10, 16),
              'direccion': (5, 250), 'tipo': (1, 10)}
    unknown = set(data) - set(limits) - (extra_allowed or set())
    if unknown:
        raise ValueError('Campos no permitidos: ' + ', '.join(sorted(unknown)))
    result = {}
    for field, (minimum, maximum) in limits.items():
        value = data.get(field)
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ValueError(f'{field}: se requiere texto entre {minimum} y {maximum} caracteres.')
        value = value.strip()
        if any(ord(char) < 32 for char in value):
            raise ValueError(f'{field}: no admite caracteres de control.')
        result[field] = value
    result['email'] = result['email'].lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', result['email']):
        raise ValueError('Correo electrónico inválido.')
    if not re.fullmatch(r'\+?[0-9]{10,15}', result['telefono']):
        raise ValueError('Teléfono: 10–15 dígitos y un + opcional al inicio.')
    if result['tipo'] not in ('persona', 'empresa'):
        raise ValueError('tipo debe ser persona o empresa.')
    return result
