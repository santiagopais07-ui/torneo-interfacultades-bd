"""Crea las cuentas iniciales de la aplicación si faltan en la tabla login."""
from getpass import getpass

from werkzeug.security import generate_password_hash

from src.conexion import conectar


USUARIOS_INICIALES = (
    ('admin@correo.ucu.edu.uy', 'administrador'),
    ('planillero@correo.ucu.edu.uy', 'planillero'),
)


def pedir_clave(correo, rol):
    print(f'\nFalta la cuenta {correo} ({rol}). Vamos a crearla.')
    while True:
        clave = getpass('Elegí una contraseña de al menos 8 caracteres: ')
        confirmacion = getpass('Repetí la contraseña: ')
        if len(clave) < 8:
            print('La contraseña debe tener al menos 8 caracteres.')
        elif clave != confirmacion:
            print('Las contraseñas no coinciden.')
        else:
            return clave


def crear_usuarios_faltantes(cursor):
    """No confirma la transacción: registro() guarda ambas cuentas juntas."""
    creados = []
    for correo, rol in USUARIOS_INICIALES:
        cursor.execute('SELECT rol FROM login WHERE correo=%s', (correo,))
        existente = cursor.fetchone()
        if existente is not None:
            if existente[0] != rol:
                raise ValueError(
                    f'La cuenta {correo} existe con un rol distinto. '
                    'Revisá ese registro antes de iniciar; no se modificó.'
                )
            continue

        clave = pedir_clave(correo, rol)
        hash_clave = generate_password_hash(clave)
        cursor.execute('''
            INSERT INTO login (correo, password_hash, rol)
            VALUES (%s, %s, %s)
        ''', (correo, hash_clave, rol))
        creados.append(correo)
    return creados


def registro(mostrar_resumen=True):
    conexion = conectar('administrador')
    cursor = None
    try:
        cursor = conexion.cursor()
        creados = crear_usuarios_faltantes(cursor)
        conexion.commit()
        if creados:
            print('Cuentas iniciales creadas: ' + ', '.join(creados))
        elif mostrar_resumen:
            print('Las cuentas iniciales ya existen. No se modificaron.')
        return creados
    finally:
        try:
            conexion.rollback()
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                conexion.close()


if __name__ == '__main__':
    try:
        registro()
    except (KeyboardInterrupt, EOFError):
        print('\nPreparación de usuarios cancelada.')
