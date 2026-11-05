from datetime import date

import mysql.connector

from src.conexion import conectar
from src.jugadores import leer_entero, leer_texto


def mostrar_filas(cursor, encabezado):
    filas = cursor.fetchall()
    print('\n' + encabezado)
    for fila in filas:
        print(' | '.join(str(dato) if dato is not None else '-' for dato in fila))
    if not filas:
        print('No hay registros.')


def listar_arbitros(cursor):
    cursor.execute('SELECT ci_arbitro, nombre, apellido, email FROM arbitro ORDER BY apellido, nombre, ci_arbitro')
    mostrar_filas(cursor, 'CI | Nombre | Apellido | Email')


def leer_email():
    email = leer_texto('Email: ')
    if email.count('@') != 1 or any(c.isspace() for c in email):
        raise ValueError('El formato del email no es válido.')
    usuario, dominio = email.split('@')
    if not usuario or '.' not in dominio or dominio.startswith('.') or dominio.endswith('.'):
        raise ValueError('El formato del email no es válido.')
    return email


def crear_arbitro(cursor):
    ci = leer_entero('CI del árbitro: ')
    nombre = leer_texto('Nombre: ')
    apellido = leer_texto('Apellido: ')
    email = leer_email()
    cursor.execute('INSERT INTO arbitro (ci_arbitro, nombre, apellido, email) VALUES (%s,%s,%s,%s)', (ci, nombre, apellido, email))


def buscar_arbitro(cursor):
    ci = leer_entero('CI del árbitro: ')
    cursor.execute('SELECT nombre, apellido, email FROM arbitro WHERE ci_arbitro=%s FOR UPDATE', (ci,))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El árbitro no existe.')
    print('Datos actuales: ' + ' | '.join(str(dato) for dato in fila))
    return ci


def modificar_arbitro(cursor):
    ci = buscar_arbitro(cursor)
    print('Ingresá los datos completos nuevos. La CI se mantiene.')
    nombre = leer_texto('Nombre: ')
    apellido = leer_texto('Apellido: ')
    email = leer_email()
    cursor.execute('UPDATE arbitro SET nombre=%s, apellido=%s, email=%s WHERE ci_arbitro=%s', (nombre, apellido, email, ci))


def eliminar_arbitro(cursor):
    ci = buscar_arbitro(cursor)
    cursor.execute('SELECT COUNT(*) FROM partido WHERE ci_arbitro=%s', (ci,))
    if cursor.fetchone()[0]:
        raise ValueError('No se puede eliminar: el árbitro tiene partidos asignados.')
    if input('¿Eliminar árbitro? Escribí SI: ').strip() != 'SI':
        return False
    cursor.execute('DELETE FROM arbitro WHERE ci_arbitro=%s', (ci,))


def listar_espectadores(cursor):
    cursor.execute('''
        SELECT e.id_espectador, e.nombre, e.apellido, e.ci_espectador,
               e.fecha_nacimiento, e.tipo, e.id_partido, p.dia
        FROM espectador e JOIN partido p ON p.id_partido=e.id_partido
        ORDER BY e.id_partido, e.id_espectador
    ''')
    mostrar_filas(cursor, 'ID asistencia | Nombre | Apellido | CI | Nacimiento | Tipo | Partido | Día')


def listar_partidos(cursor):
    cursor.execute('''
        SELECT p.id_partido, p.dia, l.nombre, v.nombre, p.estado
        FROM partido p
        JOIN equipo l ON l.id_equipo=p.id_equipo_local
        JOIN equipo v ON v.id_equipo=p.id_equipo_visitante
        ORDER BY p.id_partido
    ''')
    mostrar_filas(cursor, 'ID partido | Día | Local | Visitante | Estado')


def leer_datos_espectador(cursor):
    nombre = leer_texto('Nombre: ')
    apellido = leer_texto('Apellido: ')
    texto_ci = input('CI (Enter para omitir): ').strip()
    ci = None
    if texto_ci:
        if not texto_ci.isascii() or not texto_ci.isdecimal() or not 1 <= int(texto_ci) <= 2147483647:
            raise ValueError('La CI debe ser un entero positivo válido.')
        ci = int(texto_ci)
    texto_fecha = input('Nacimiento AAAA-MM-DD (Enter para omitir): ').strip()
    nacimiento = None
    if texto_fecha:
        try:
            nacimiento = date.fromisoformat(texto_fecha)
        except ValueError:
            raise ValueError('La fecha de nacimiento no es válida.') from None
        if nacimiento > date.today():
            raise ValueError('La fecha de nacimiento no puede estar en el futuro.')
    tipo = input('Tipo (facultad/externo): ').strip().lower()
    if tipo not in ('facultad', 'externo'):
        raise ValueError('El tipo debe ser facultad o externo.')
    listar_partidos(cursor)
    id_partido = leer_entero('ID del partido: ')
    cursor.execute('SELECT id_partido FROM partido WHERE id_partido=%s', (id_partido,))
    if cursor.fetchone() is None:
        raise ValueError('El partido no existe.')
    return nombre, apellido, ci, nacimiento, tipo, id_partido


def crear_espectador(cursor):
    datos = leer_datos_espectador(cursor)
    cursor.execute('''
        INSERT INTO espectador (nombre, apellido, ci_espectador, fecha_nacimiento, tipo, id_partido)
        VALUES (%s,%s,%s,%s,%s,%s)
    ''', datos)
    print(f'Nuevo ID de asistencia: {cursor.lastrowid}')


def buscar_espectador(cursor):
    identificador = leer_entero('ID del registro de asistencia: ')
    cursor.execute('SELECT nombre, apellido, id_partido FROM espectador WHERE id_espectador=%s FOR UPDATE', (identificador,))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El registro de asistencia no existe.')
    print(f'Registro actual: {fila[0]} {fila[1]}, partido {fila[2]}')
    return identificador


def modificar_espectador(cursor):
    identificador = buscar_espectador(cursor)
    print('Ingresá los datos completos nuevos de esta asistencia.')
    datos = leer_datos_espectador(cursor)
    cursor.execute('''
        UPDATE espectador SET nombre=%s, apellido=%s, ci_espectador=%s,
            fecha_nacimiento=%s, tipo=%s, id_partido=%s
        WHERE id_espectador=%s
    ''', (*datos, identificador))


def eliminar_espectador(cursor):
    identificador = buscar_espectador(cursor)
    if input('¿Eliminar este registro de asistencia? Escribí SI: ').strip() != 'SI':
        return False
    cursor.execute('DELETE FROM espectador WHERE id_espectador=%s', (identificador,))


def menu_personas_partido(usuario):
    if usuario.get('rol') != 'administrador':
        print('Solo el administrador puede gestionar árbitros y espectadores.')
        return
    operaciones = {
        '1': listar_arbitros, '2': crear_arbitro, '3': modificar_arbitro,
        '4': eliminar_arbitro, '5': listar_espectadores, '6': crear_espectador,
        '7': modificar_espectador, '8': eliminar_espectador,
    }
    while True:
        print('\nÁRBITROS Y ESPECTADORES\n1. Listar árbitros\n2. Crear árbitro\n3. Modificar árbitro\n4. Eliminar árbitro\n5. Listar espectadores\n6. Registrar espectador\n7. Modificar asistencia\n8. Eliminar asistencia\n0. Volver')
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
            if opcion not in ('1', '5'):
                if resultado is False:
                    print('Operación cancelada.')
                else:
                    conexion.commit()
                    print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('Ya existe un árbitro con esa CI o email.')
            elif error.errno == 1451:
                print('No se puede eliminar: hay registros relacionados.')
            elif error.errno == 1452:
                print('El registro relacionado no existe.')
            elif error.errno in (1142, 1143):
                print('Faltan permisos de MySQL para esta operación.')
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
