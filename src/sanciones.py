"""Consulta de sanciones y ABM disciplinario con SQL directo."""
import mysql.connector
from src.conexion import conectar
from src.jugadores import leer_entero


def exigir_administrador(usuario):
    if usuario.get('rol') != 'administrador':
        raise ValueError('Solo el administrador puede gestionar sanciones.')


def bloquear_edicion(cursor, id_torneo):
    # El mismo bloqueo que usa planillas evita cargas simultáneas incompatibles.
    cursor.execute('SELECT GET_LOCK(CONCAT(DATABASE(), %s, %s), 5)', (':registro:', id_torneo))
    if cursor.fetchone()[0] != 1:
        raise ValueError('Otra operación está usando la edición. Intentá nuevamente.')
    cursor.execute('SELECT id_torneo FROM torneo WHERE id_torneo=%s', (id_torneo,))
    if cursor.fetchone() is None:
        raise ValueError('No existe esa edición.')


def listar_sanciones(cursor, id_torneo):
    cursor.execute("""
        SELECT s.id_sancion, s.ci_jugador, j.nombre, j.apellido, s.motivo,
               s.numero_fecha_inicio, s.cantidad_fechas,
               s.numero_fecha_inicio+s.cantidad_fechas-1
        FROM sancion_jugador s JOIN jugador j ON j.ci=s.ci_jugador
        WHERE s.id_torneo=%s ORDER BY s.numero_fecha_inicio, s.id_sancion
    """, (id_torneo,))
    filas = cursor.fetchall()
    print('ID | CI | Nombre | Apellido | Motivo | Desde jornada | Cantidad | Hasta jornada')
    for fila in filas:
        print(' | '.join(str(valor) for valor in fila))
    if not filas:
        print('No hay sanciones para esta edición.')


def validar_datos(cursor, id_torneo, ci, inicio, cantidad):
    if any(type(v) is not int or not 1 <= v <= 2147483647 for v in (inicio, cantidad)):
        raise ValueError('La jornada inicial y la cantidad deben ser enteros positivos.')
    if inicio+cantidad-1 > 2147483647:
        raise ValueError('La jornada final supera el límite permitido.')
    cursor.execute('SELECT 1 FROM equipo_jugador_torneo WHERE id_torneo=%s AND ci_jugador=%s', (id_torneo, ci))
    if cursor.fetchone() is None:
        raise ValueError('El jugador no está inscripto en esta edición.')
    cursor.execute("""
        SELECT p.id_partido FROM planilla_partido pp
        JOIN partido p ON p.id_partido=pp.id_partido
        WHERE pp.ci_jugador=%s AND p.id_torneo=%s
          AND p.numero_fecha BETWEEN %s AND %s LIMIT 1
    """, (ci, id_torneo, inicio, inicio+cantidad-1))
    fila = cursor.fetchone()
    if fila is not None:
        raise ValueError(f'El jugador ya tiene participación registrada en el partido {fila[0]} de ese período. Revisá esa planilla antes de sancionarlo.')


def crear_sancion(cursor, usuario, id_torneo, ci, inicio, cantidad):
    exigir_administrador(usuario)
    bloquear_edicion(cursor, id_torneo)
    validar_datos(cursor, id_torneo, ci, inicio, cantidad)
    cursor.execute("""
        INSERT INTO sancion_jugador
          (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas)
        VALUES (%s,%s,'disciplinaria',%s,%s)
    """, (ci, id_torneo, inicio, cantidad))
    return cursor.lastrowid


def buscar_disciplinaria(cursor, usuario, id_torneo, id_sancion):
    exigir_administrador(usuario)
    bloquear_edicion(cursor, id_torneo)
    cursor.execute('SELECT ci_jugador, motivo FROM sancion_jugador WHERE id_sancion=%s AND id_torneo=%s FOR UPDATE', (id_sancion, id_torneo))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('No existe esa sanción en esta edición.')
    if fila[1] != 'disciplinaria':
        raise ValueError('Las sanciones automáticas se corrigen desde las tarjetas que las originaron.')
    return fila[0]


def modificar_sancion(cursor, usuario, id_torneo, id_sancion, inicio, cantidad):
    ci = buscar_disciplinaria(cursor, usuario, id_torneo, id_sancion)
    validar_datos(cursor, id_torneo, ci, inicio, cantidad)
    cursor.execute('UPDATE sancion_jugador SET numero_fecha_inicio=%s,cantidad_fechas=%s WHERE id_sancion=%s', (inicio, cantidad, id_sancion))


def eliminar_sancion(cursor, usuario, id_torneo, id_sancion):
    buscar_disciplinaria(cursor, usuario, id_torneo, id_sancion)
    cursor.execute('DELETE FROM sancion_jugador WHERE id_sancion=%s', (id_sancion,))


def menu_sanciones(usuario):
    try:
        exigir_administrador(usuario)
    except ValueError as error:
        print(error)
        return
    while True:
        print('\nSANCIONES\n1. Listar sanciones\n2. Crear disciplinaria\n3. Modificar disciplinaria\n4. Eliminar disciplinaria\n0. Volver')
        opcion = input('Elegí una opción: ').strip()
        if opcion == '0':
            return
        if opcion not in ('1','2','3','4'):
            print('Opción inválida.')
            continue
        conexion = None
        cursor = None
        try:
            conexion = conectar('administrador')
            conexion.start_transaction(isolation_level='READ COMMITTED')
            cursor = conexion.cursor()
            cursor.execute('SELECT id_torneo,nombre FROM torneo ORDER BY id_torneo')
            for fila in cursor.fetchall():
                print(f'{fila[0]} | {fila[1]}')
            torneo = leer_entero('ID de la edición: ')
            if opcion == '1':
                listar_sanciones(cursor, torneo)
                continue
            if opcion == '2':
                cursor.execute("""SELECT j.ci,j.nombre,j.apellido FROM jugador j
                    JOIN equipo_jugador_torneo e ON e.ci_jugador=j.ci
                    WHERE e.id_torneo=%s ORDER BY j.ci""", (torneo,))
                for fila in cursor.fetchall():
                    print(' | '.join(str(v) for v in fila))
                ci = leer_entero('CI del jugador: ')
                inicio = leer_entero('Jornada inicial: ')
                cantidad = leer_entero('Cantidad de jornadas: ')
                identificador = crear_sancion(cursor, usuario, torneo, ci, inicio, cantidad)
                print(f'Sanción creada. ID: {identificador}')
            else:
                listar_sanciones(cursor, torneo)
                identificador = leer_entero('ID de la sanción: ')
                if opcion == '3':
                    inicio = leer_entero('Nueva jornada inicial: ')
                    cantidad = leer_entero('Nueva cantidad de jornadas: ')
                    modificar_sancion(cursor, usuario, torneo, identificador, inicio, cantidad)
                else:
                    if input('Escribí SI para eliminar la sanción: ').strip().upper() != 'SI':
                        print('Operación cancelada.')
                        continue
                    eliminar_sancion(cursor, usuario, torneo, identificador)
            conexion.commit()
            print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            print(f'No se pudo completar la operación (MySQL {error.errno}).')
        finally:
            if conexion is not None:
                conexion.rollback()
            if cursor is not None:
                cursor.close()
            if conexion is not None:
                conexion.close()
