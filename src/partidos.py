"""Programación de partidos por consola, con SQL directo y reglas del torneo."""
from datetime import date

import mysql.connector

from src.conexion import conectar
from src.jugadores import leer_entero, leer_texto
from src.reglas import validar_alta_partido, validar_baja_partido


def mostrar_filas(cursor, encabezado):
    filas = cursor.fetchall()
    print('\n' + encabezado)
    for fila in filas:
        print(' | '.join(str(dato) if dato is not None else '-' for dato in fila))
    if not filas:
        print('No hay registros.')
    return filas


def listar_partidos(cursor):
    cursor.execute('''
        SELECT p.id_partido, p.id_torneo, p.numero_fecha, p.dia,
               l.nombre, v.nombre, t.hora_inicio, t.hora_fin,
               co.nombre, p.nombre_cancha,
               CONCAT_WS(' ', a.nombre, a.apellido), p.estado
        FROM partido p
        JOIN equipo l ON l.id_equipo = p.id_equipo_local
        JOIN equipo v ON v.id_equipo = p.id_equipo_visitante
        JOIN turno t ON t.id_turno = p.id_turno
        JOIN complejo co ON co.id_complejo = p.id_complejo
        JOIN arbitro a ON a.ci_arbitro = p.ci_arbitro
        ORDER BY p.id_torneo, p.numero_fecha, p.dia, t.hora_inicio, p.id_partido
    ''')
    mostrar_filas(cursor, 'ID | Torneo | Fecha nro. | Día | Local | Visitante | Inicio | Fin | Complejo | Cancha | Árbitro | Estado')


def obtener_partido(cursor, id_partido, bloquear=False):
    consulta = '''
        SELECT id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante,
               dia, id_turno, nombre_cancha, id_complejo, ci_arbitro, estado
        FROM partido WHERE id_partido = %s
    '''
    if bloquear:
        consulta += ' FOR UPDATE'
    cursor.execute(consulta, (id_partido,))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El partido no existe.')
    campos = ('id_torneo', 'numero_fecha', 'id_equipo_local', 'id_equipo_visitante',
              'dia', 'id_turno', 'nombre_cancha', 'id_complejo', 'ci_arbitro', 'estado')
    return dict(zip(campos, fila))


def bloquear_torneo(cursor, id_torneo):
    # Serializa las operaciones de programación de una misma edición.
    cursor.execute('SELECT estado FROM torneo WHERE id_torneo = %s FOR UPDATE', (id_torneo,))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El torneo no existe.')
    if fila[0] == 'finalizado':
        raise ValueError('No se puede cambiar la programación de un torneo finalizado.')


def validar_sin_planilla(cursor, id_partido):
    cursor.execute('SELECT COUNT(*) FROM planilla_partido WHERE id_partido = %s', (id_partido,))
    if cursor.fetchone()[0]:
        raise ValueError('El partido ya tiene planilla. No se puede cambiar su programación ni cancelarlo.')


def guardar_programacion(cursor, datos, id_partido=None):
    """Valida y escribe; el menú confirma la transacción con commit."""
    id_torneo = datos['id_torneo']
    bloquear_torneo(cursor, id_torneo)

    if id_partido is not None:
        actual = obtener_partido(cursor, id_partido, bloquear=True)
        if actual['id_torneo'] != id_torneo:
            raise ValueError('No se puede trasladar un partido a otra edición.')
        if actual['estado'] in ('jugado', 'cancelado'):
            raise ValueError('No se puede reprogramar un partido jugado o cancelado.')
        validar_sin_planilla(cursor, id_partido)

    local = datos['id_equipo_local']
    visitante = datos['id_equipo_visitante']
    if local == visitante:
        raise ValueError('Un equipo no puede enfrentarse a sí mismo.')
    if not isinstance(datos['numero_fecha'], int) or datos['numero_fecha'] < 1:
        raise ValueError('El número de fecha debe ser un entero positivo.')
    if not isinstance(datos['dia'], date):
        raise ValueError('El día debe ser una fecha válida.')

    # Bloqueamos los equipos en orden para evitar altas simultáneas sobre sus planteles.
    for id_equipo in sorted((local, visitante)):
        cursor.execute('SELECT id_torneo FROM equipo WHERE id_equipo = %s FOR UPDATE', (id_equipo,))
        equipo = cursor.fetchone()
        if equipo is None or equipo[0] != id_torneo:
            raise ValueError('Ambos equipos deben pertenecer a la edición elegida.')

    validar_alta_partido(cursor, id_torneo, datos['numero_fecha'], local, visitante, id_partido)

    cursor.execute('SELECT hora_inicio, hora_fin FROM turno WHERE id_turno = %s', (datos['id_turno'],))
    if cursor.fetchone() is None:
        raise ValueError('El turno no existe.')

    cursor.execute('''
        SELECT nombre_cancha FROM cancha
        WHERE id_complejo = %s AND nombre_cancha = %s FOR UPDATE
    ''', (datos['id_complejo'], datos['nombre_cancha']))
    if cursor.fetchone() is None:
        raise ValueError('La cancha no existe en ese complejo.')

    cursor.execute('SELECT ci_arbitro FROM arbitro WHERE ci_arbitro = %s FOR UPDATE', (datos['ci_arbitro'],))
    if cursor.fetchone() is None:
        raise ValueError('El árbitro no existe.')

    cursor.execute('''
        SELECT COUNT(*) FROM partido
        WHERE dia = %s AND id_turno = %s
          AND id_complejo = %s AND nombre_cancha = %s
          AND (%s IS NULL OR id_partido <> %s)
    ''', (datos['dia'], datos['id_turno'], datos['id_complejo'], datos['nombre_cancha'], id_partido, id_partido))
    if cursor.fetchone()[0]:
        raise ValueError('La cancha ya está ocupada ese día y turno, incluso si el partido está cancelado.')

    cursor.execute('''
        SELECT COUNT(*) FROM partido
        WHERE dia = %s AND id_turno = %s AND ci_arbitro = %s
          AND (%s IS NULL OR id_partido <> %s)
    ''', (datos['dia'], datos['id_turno'], datos['ci_arbitro'], id_partido, id_partido))
    if cursor.fetchone()[0]:
        raise ValueError('El árbitro ya tiene un partido ese día y turno.')

    valores = (id_torneo, datos['numero_fecha'], local, visitante, datos['dia'],
               datos['id_turno'], datos['nombre_cancha'], datos['id_complejo'], datos['ci_arbitro'])
    if id_partido is None:
        cursor.execute('''
            INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local,
                id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, ci_arbitro, estado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'programado')
        ''', valores)
        return cursor.lastrowid

    cursor.execute('''
        UPDATE partido SET id_torneo=%s, numero_fecha=%s, id_equipo_local=%s,
            id_equipo_visitante=%s, dia=%s, id_turno=%s, nombre_cancha=%s,
            id_complejo=%s, ci_arbitro=%s, estado='programado'
        WHERE id_partido=%s
    ''', (*valores, id_partido))
    return id_partido


def leer_programacion(cursor, id_torneo):
    cursor.execute('''
        SELECT e.id_equipo, e.nombre, COUNT(p.ci_jugador)
        FROM equipo e LEFT JOIN equipo_jugador_torneo p
          ON p.id_equipo=e.id_equipo AND p.id_torneo=e.id_torneo
        WHERE e.id_torneo=%s GROUP BY e.id_equipo, e.nombre ORDER BY e.id_equipo
    ''', (id_torneo,))
    equipos = mostrar_filas(cursor, 'ID equipo | Nombre | Integrantes')
    if len(equipos) < 2:
        raise ValueError('La edición necesita al menos dos equipos para programar un partido.')
    numero_fecha = leer_entero('Número de fecha o jornada: ')
    local = leer_entero('ID del equipo local: ')
    visitante = leer_entero('ID del equipo visitante: ')
    texto_dia = leer_texto('Día (AAAA-MM-DD): ', 10)
    try:
        dia = date.fromisoformat(texto_dia)
        if dia.isoformat() != texto_dia:
            raise ValueError
    except ValueError:
        raise ValueError('Ingresá una fecha válida con formato AAAA-MM-DD.') from None

    cursor.execute('SELECT id_turno, hora_inicio, hora_fin FROM turno ORDER BY hora_inicio')
    mostrar_filas(cursor, 'ID turno | Inicio | Fin')
    id_turno = leer_entero('ID del turno: ')
    cursor.execute('''
        SELECT c.id_complejo, co.nombre, c.nombre_cancha
        FROM cancha c JOIN complejo co ON co.id_complejo=c.id_complejo
        ORDER BY c.id_complejo, c.nombre_cancha
    ''')
    mostrar_filas(cursor, 'ID complejo | Complejo | Nombre de cancha')
    id_complejo = leer_entero('ID del complejo: ')
    nombre_cancha = leer_texto('Nombre exacto de la cancha: ')
    cursor.execute('SELECT ci_arbitro, nombre, apellido FROM arbitro ORDER BY apellido, nombre')
    mostrar_filas(cursor, 'CI árbitro | Nombre | Apellido')
    ci_arbitro = leer_entero('CI del árbitro: ')
    return dict(id_torneo=id_torneo, numero_fecha=numero_fecha,
                id_equipo_local=local, id_equipo_visitante=visitante, dia=dia,
                id_turno=id_turno, id_complejo=id_complejo,
                nombre_cancha=nombre_cancha, ci_arbitro=ci_arbitro)


def crear_partido(cursor):
    cursor.execute("SELECT id_torneo, nombre, estado FROM torneo WHERE estado <> 'finalizado' ORDER BY id_torneo")
    torneos = mostrar_filas(cursor, 'ID torneo | Nombre | Estado')
    if not torneos:
        raise ValueError('No hay ediciones disponibles.')
    id_torneo = leer_entero('ID del torneo: ')
    if id_torneo not in [fila[0] for fila in torneos]:
        raise ValueError('Elegí una de las ediciones mostradas.')
    datos = leer_programacion(cursor, id_torneo)
    identificador = guardar_programacion(cursor, datos)
    print(f'ID del nuevo partido: {identificador}')


def modificar_partido(cursor):
    identificador = leer_entero('ID del partido a modificar: ')
    actual = obtener_partido(cursor, identificador)
    if actual['estado'] in ('jugado', 'cancelado'):
        raise ValueError('No se puede reprogramar un partido jugado o cancelado.')
    validar_sin_planilla(cursor, identificador)
    print(f"Edición: {actual['id_torneo']} | Fecha nro.: {actual['numero_fecha']} | Día: {actual['dia']} | Estado: {actual['estado']}")
    print('Ingresá la programación completa nueva. Se conserva el ID y la edición.')
    datos = leer_programacion(cursor, actual['id_torneo'])
    guardar_programacion(cursor, datos, identificador)
    print('El partido queda en estado programado.')


def cambiar_estado_partido(cursor, id_partido, nuevo_estado):
    if nuevo_estado not in ('postergado', 'cancelado'):
        raise ValueError('Esta operación solo permite postergar o cancelar.')
    actual = obtener_partido(cursor, id_partido)
    bloquear_torneo(cursor, actual['id_torneo'])
    actual = obtener_partido(cursor, id_partido, bloquear=True)
    validar_baja_partido(cursor, id_partido)
    if actual['estado'] == 'cancelado':
        raise ValueError('El partido ya está cancelado.')
    if actual['estado'] == nuevo_estado:
        raise ValueError('El partido ya tiene ese estado.')
    validar_sin_planilla(cursor, id_partido)
    cursor.execute('UPDATE partido SET estado=%s WHERE id_partido=%s', (nuevo_estado, id_partido))


def postergar_partido(cursor):
    identificador = leer_entero('ID del partido a postergar: ')
    if input('¿Postergar el partido? Escribí SI: ').strip() != 'SI':
        return False
    cambiar_estado_partido(cursor, identificador, 'postergado')


def cancelar_partido(cursor):
    identificador = leer_entero('ID del partido a cancelar: ')
    print('La cancelación conserva el historial, la jornada y la reserva de cancha y árbitro.')
    if input('¿Cancelar el partido? Escribí SI: ').strip() != 'SI':
        return False
    cambiar_estado_partido(cursor, identificador, 'cancelado')


def menu_partidos(usuario):
    if usuario.get('rol') != 'administrador':
        print('Solo el administrador puede gestionar la programación de partidos.')
        return
    operaciones = {'1': listar_partidos, '2': crear_partido, '3': modificar_partido,
                   '4': postergar_partido, '5': cancelar_partido}
    while True:
        print('\nPARTIDOS\n1. Listar partidos\n2. Programar partido\n3. Modificar o reprogramar partido\n4. Postergar partido\n5. Cancelar partido\n0. Volver')
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
            # Las consultas posteriores a cada bloqueo ven los últimos cambios confirmados.
            conexion.start_transaction(isolation_level='READ COMMITTED')
            cursor = conexion.cursor()
            resultado = operaciones[opcion](cursor)
            if opcion != '1':
                if resultado is False:
                    print('Operación cancelada.')
                else:
                    conexion.commit()
                    print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('La cancha o el árbitro ya están ocupados ese día y turno.')
            elif error.errno == 1452:
                print('Uno de los registros elegidos ya no existe o no pertenece a la edición.')
            elif error.errno in (1205, 1213):
                print('Otra operación está usando esos datos. Volvé a intentarlo.')
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
