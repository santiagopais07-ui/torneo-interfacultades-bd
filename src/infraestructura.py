import mysql.connector

from src.conexion import conectar
from src.jugadores import leer_entero, leer_texto


def listar_complejos(cursor):
    cursor.execute('SELECT id_complejo, nombre, direccion, departamento FROM complejo ORDER BY id_complejo')
    filas = cursor.fetchall()
    print('\nID | Complejo | Dirección | Departamento')
    for fila in filas:
        print(' | '.join(str(dato) if dato is not None else '-' for dato in fila))
    if not filas:
        print('No hay complejos registrados.')


def listar_canchas(cursor):
    cursor.execute('''
        SELECT c.id_complejo, co.nombre, c.nombre_cancha, c.superficie, c.techada
        FROM cancha c JOIN complejo co ON co.id_complejo = c.id_complejo
        ORDER BY c.id_complejo, c.nombre_cancha
    ''')
    filas = cursor.fetchall()
    print('\nID complejo | Complejo | Cancha | Superficie | Techada')
    for identificador, complejo, cancha, superficie, techada in filas:
        techo = '-' if techada is None else ('Sí' if techada else 'No')
        print(f'{identificador} | {complejo or "-"} | {cancha} | {superficie or "-"} | {techo}')
    if not filas:
        print('No hay canchas registradas.')


def buscar_complejo(cursor, identificador):
    cursor.execute('SELECT nombre, direccion, departamento FROM complejo WHERE id_complejo=%s FOR UPDATE', (identificador,))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El complejo no existe.')
    return fila


def leer_cambio(mensaje, actual, limite):
    valor = input(f'{mensaje} [{actual or "-"}] (Enter para mantener): ').strip()
    if not valor:
        return actual
    if len(valor) > limite:
        raise ValueError(f'El campo admite hasta {limite} caracteres.')
    return valor


def crear_complejo(cursor):
    nombre = leer_texto('Nombre del complejo: ')
    direccion = leer_texto('Dirección: ', 100)
    departamento = leer_texto('Departamento: ')
    cursor.execute('INSERT INTO complejo (nombre, direccion, departamento) VALUES (%s,%s,%s)', (nombre, direccion, departamento))
    print(f'Nuevo ID de complejo: {cursor.lastrowid}')


def modificar_complejo(cursor):
    identificador = leer_entero('ID del complejo: ')
    nombre, direccion, departamento = buscar_complejo(cursor, identificador)
    nombre = leer_cambio('Nombre', nombre, 50)
    direccion = leer_cambio('Dirección', direccion, 100)
    departamento = leer_cambio('Departamento', departamento, 50)
    cursor.execute('UPDATE complejo SET nombre=%s, direccion=%s, departamento=%s WHERE id_complejo=%s', (nombre, direccion, departamento, identificador))


def eliminar_complejo(cursor):
    identificador = leer_entero('ID del complejo: ')
    nombre, _, _ = buscar_complejo(cursor, identificador)
    cursor.execute('SELECT COUNT(*) FROM cancha WHERE id_complejo=%s', (identificador,))
    if cursor.fetchone()[0]:
        raise ValueError('No se puede eliminar el complejo: tiene canchas asociadas.')
    if input(f'¿Eliminar el complejo {nombre}? Escribí SI: ').strip() != 'SI':
        return False
    cursor.execute('DELETE FROM complejo WHERE id_complejo=%s', (identificador,))


def leer_superficie(actual=None):
    print('1. Sintético\n2. Parquet')
    opcion = input('Superficie' + (' (Enter para mantener)' if actual else '') + ': ').strip()
    if not opcion and actual is not None:
        return actual
    if opcion == '1':
        return 'sintético'
    if opcion == '2':
        return 'parquet'
    raise ValueError('La superficie debe ser 1 o 2.')


def leer_techo(actual=None):
    opcion = input('¿Techada? S/N' + (' (Enter para mantener)' if actual is not None else '') + ': ').strip().upper()
    if not opcion and actual is not None:
        return actual
    if opcion not in ('S', 'N'):
        raise ValueError('Respondé S o N para indicar si es techada.')
    return opcion == 'S'


def crear_cancha(cursor):
    identificador = leer_entero('ID del complejo: ')
    buscar_complejo(cursor, identificador)
    nombre = leer_texto('Nombre de la cancha: ')
    superficie = leer_superficie()
    techada = leer_techo()
    cursor.execute('INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES (%s,%s,%s,%s)', (nombre, identificador, superficie, techada))


def buscar_cancha(cursor):
    identificador = leer_entero('ID del complejo: ')
    buscar_complejo(cursor, identificador)
    nombre = leer_texto('Nombre exacto de la cancha: ')
    cursor.execute('SELECT superficie, techada FROM cancha WHERE id_complejo=%s AND nombre_cancha=%s FOR UPDATE', (identificador, nombre))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('Esa cancha no existe en el complejo indicado.')
    return identificador, nombre, fila


def modificar_cancha(cursor):
    identificador, nombre, (superficie, techada) = buscar_cancha(cursor)
    print(f'Superficie actual: {superficie or "-"}; techada: {techada}')
    superficie = leer_superficie(superficie)
    techada = leer_techo(techada)
    cursor.execute('UPDATE cancha SET superficie=%s, techada=%s WHERE id_complejo=%s AND nombre_cancha=%s', (superficie, techada, identificador, nombre))


def eliminar_cancha(cursor):
    identificador, nombre, _ = buscar_cancha(cursor)
    cursor.execute('SELECT COUNT(*) FROM partido WHERE id_complejo=%s AND nombre_cancha=%s', (identificador, nombre))
    if cursor.fetchone()[0]:
        raise ValueError('No se puede eliminar la cancha: tiene partidos registrados.')
    if input(f'¿Eliminar la cancha {nombre}? Escribí SI: ').strip() != 'SI':
        return False
    cursor.execute('DELETE FROM cancha WHERE id_complejo=%s AND nombre_cancha=%s', (identificador, nombre))


def menu_infraestructura(usuario):
    if usuario.get('rol') != 'administrador':
        print('Solo el administrador puede gestionar infraestructura.')
        return
    operaciones = {
        '1': listar_complejos, '2': listar_canchas,
        '3': crear_complejo, '4': modificar_complejo, '5': eliminar_complejo,
        '6': crear_cancha, '7': modificar_cancha, '8': eliminar_cancha,
    }
    while True:
        print('\nCOMPLEJOS Y CANCHAS\n1. Listar complejos\n2. Listar canchas\n3. Crear complejo\n4. Modificar complejo\n5. Eliminar complejo\n6. Crear cancha\n7. Modificar cancha\n8. Eliminar cancha\n0. Volver')
        opcion = input('Elegí una opción: ').strip()
        if opcion == '0':
            return
        if opcion not in operaciones:
            print('Opción inválida.')
            continue
        conexion = None
        cursor = None
        try:
            conexion = conectar(usuario['rol'])
            cursor = conexion.cursor()
            resultado = operaciones[opcion](cursor)
            if opcion not in ('1', '2'):
                if resultado is False:
                    print('Operación cancelada.')
                else:
                    conexion.commit()
                    print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('Ya existe una cancha con ese nombre en ese complejo.')
            elif error.errno == 1451:
                print('No se puede eliminar: hay registros relacionados.')
            elif error.errno == 1452:
                print('El registro relacionado no existe.')
            elif error.errno == 3819:
                print('La base rechazó un valor. Revisá los datos y la definición de sus restricciones.')
            else:
                print(f'No se pudo completar la operación (MySQL {error.errno}).')
        finally:
            if conexion is not None:
                try:
                    conexion.rollback()
                finally:
                    try:
                        if cursor is not None:
                            cursor.close()
                    finally:
                        conexion.close()
