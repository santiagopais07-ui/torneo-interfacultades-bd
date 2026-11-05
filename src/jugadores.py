from datetime import date

import mysql.connector

from src.conexion import conectar


TIPOS = ('grado', 'posgrado', 'docente', 'funcionario')


def leer_entero(mensaje):
    valor = input(mensaje).strip()
    if not valor.isdecimal() or not 1 <= int(valor) <= 2147483647:
        raise ValueError('Ingresá un número entero positivo válido.')
    return int(valor)


def leer_texto(mensaje, limite=50):
    valor = input(mensaje).strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'El campo es obligatorio y admite hasta {limite} caracteres.')
    return valor


def leer_datos(cursor):
    nombre = leer_texto('Nombre: ')
    apellido = leer_texto('Apellido: ')
    email = leer_texto('Email: ')
    if email.count('@') != 1 or any(c.isspace() for c in email):
        raise ValueError('El email debe tener usuario y dominio separados por @.')
    usuario, dominio = email.split('@')
    if not usuario or not dominio or '.' not in dominio or dominio.startswith('.') or dominio.endswith('.'):
        raise ValueError('El formato del email no es válido.')
    texto_fecha = input('Nacimiento (AAAA-MM-DD, Enter para omitir): ').strip()
    nacimiento = None
    if texto_fecha:
        try:
            nacimiento = date.fromisoformat(texto_fecha)
        except ValueError:
            raise ValueError('La fecha debe ser válida y tener formato AAAA-MM-DD.') from None
        if nacimiento > date.today():
            raise ValueError('La fecha de nacimiento no puede estar en el futuro.')
    cursor.execute('SELECT id_facultad, nombre FROM facultad ORDER BY id_facultad')
    for identificador, facultad in cursor.fetchall():
        print(f'{identificador}. {facultad}')
    id_facultad = leer_entero('ID de facultad: ')
    cursor.execute('SELECT id_facultad FROM facultad WHERE id_facultad = %s', (id_facultad,))
    if cursor.fetchone() is None:
        raise ValueError('La facultad no existe.')
    print('Tipos: ' + ', '.join(TIPOS))
    tipo = input('Tipo: ').strip().lower()
    if tipo not in TIPOS:
        raise ValueError('Elegí uno de los tipos indicados.')
    return nombre, apellido, email, nacimiento, id_facultad, tipo


def listar(cursor):
    cursor.execute('''
        SELECT j.ci, j.nombre, j.apellido, j.email, j.fecha_nacimiento, f.nombre, j.tipo
        FROM jugador j JOIN facultad f ON f.id_facultad = j.id_facultad
        ORDER BY j.apellido, j.nombre, j.ci
    ''')
    filas = cursor.fetchall()
    if not filas:
        print('No hay jugadores registrados.')
    for fila in filas:
        print(' | '.join(str(valor) if valor is not None else '-' for valor in fila))


def agregar(cursor):
    ci = leer_entero('CI sin puntos ni guiones: ')
    datos = leer_datos(cursor)
    cursor.execute('''
        INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (ci, *datos))


def modificar(cursor):
    ci = leer_entero('CI del jugador a modificar: ')
    cursor.execute('SELECT id_facultad, tipo FROM jugador WHERE ci = %s FOR UPDATE', (ci,))
    anterior = cursor.fetchone()
    if anterior is None:
        raise ValueError('El jugador no existe.')
    print('Ingresá los datos completos nuevos. La CI se mantiene.')
    datos = leer_datos(cursor)
    if (datos[4], datos[5]) != anterior:
        cursor.execute('SELECT id_equipo FROM equipo_jugador_torneo WHERE ci_jugador = %s', (ci,))
        planteles = cursor.fetchall()
        cursor.execute('SELECT id_equipo FROM equipo WHERE ci_capitan = %s', (ci,))
        capitanias = cursor.fetchall()
        if planteles or capitanias:
            raise ValueError('No se puede cambiar facultad o tipo mientras el jugador integre un plantel o sea capitán. Podría incumplir las reglas del equipo.')
    cursor.execute('''
        UPDATE jugador SET nombre=%s, apellido=%s, email=%s, fecha_nacimiento=%s,
            id_facultad=%s, tipo=%s WHERE ci=%s
    ''', (*datos, ci))


def eliminar(cursor):
    ci = leer_entero('CI del jugador a dar de baja: ')
    cursor.execute('SELECT nombre, apellido FROM jugador WHERE ci = %s FOR UPDATE', (ci,))
    jugador = cursor.fetchone()
    if jugador is None:
        raise ValueError('El jugador no existe.')
    if input(f'Eliminar a {jugador[0]} {jugador[1]}? Escribí SI para confirmar: ').strip() != 'SI':
        return False
    # Las claves foráneas impiden borrar jugadores con registros relacionados.
    cursor.execute('DELETE FROM jugador WHERE ci = %s', (ci,))
    return True


def menu_jugadores(usuario):
    if usuario.get('rol') != 'administrador':
        print('Solo el administrador puede gestionar jugadores.')
        return
    while True:
        print('\nJUGADORES\n1. Listar\n2. Agregar\n3. Modificar\n4. Dar de baja\n0. Volver')
        opcion = input('Elegí una opción: ').strip()
        if opcion == '0':
            return
        if opcion not in ('1', '2', '3', '4'):
            print('Opción inválida.')
            continue
        conexion = None
        cursor = None
        try:
            conexion = conectar(usuario['rol'])
            cursor = conexion.cursor()
            if opcion == '1':
                listar(cursor)
            else:
                operacion = {'2': agregar, '3': modificar, '4': eliminar}[opcion]
                resultado = operacion(cursor)
                if resultado is False:
                    print('Baja cancelada.')
                else:
                    conexion.commit()
                    print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('Ya existe un jugador con esa CI o email.')
            elif error.errno == 1451:
                print('No se puede borrar: el jugador tiene registros relacionados. Se conserva su historial.')
            elif error.errno == 1452:
                print('El registro relacionado no existe. Revisá los datos.')
            else:
                print(f'No se pudo completar la operación (MySQL {error.errno}).')
        finally:
            if conexion is not None:
                conexion.rollback()
            if cursor is not None:
                cursor.close()
            if conexion is not None:
                conexion.close()
