"""Registro de participantes, goles y tarjetas con SQL directo."""
import mysql.connector

from src.conexion import conectar
from src.jugadores import leer_entero
from src.partidos import listar_partidos, mostrar_filas, obtener_partido
from src.reglas import (
    validar_alta_planilla, validar_jugador_no_suspendido,
    validar_partido_registrable, validar_min_jugadores,
    recalcular_sanciones_automaticas, registrar_cambio,
)


def preparar_registro(cursor, id_partido, usuario, ahora=None):
    if usuario.get('rol') not in ('administrador', 'planillero') or not usuario.get('correo'):
        raise ValueError('Se necesita un usuario autenticado para registrar el partido.')
    actual = obtener_partido(cursor, id_partido)
    # Coordina registros de una edición sin dar al planillero permisos de UPDATE sobre torneo.
    # Este bloqueo pertenece a la conexión y se libera al cerrarla en el menú.
    cursor.execute('SELECT GET_LOCK(CONCAT(DATABASE(), %s, %s), 5)', (':registro:', actual['id_torneo']))
    if cursor.fetchone()[0] != 1:
        raise ValueError('Otra carga está usando la edición. Volvé a intentarlo.')
    # Bloquea la fila sin alterar el estado; usa su permiso UPDATE(estado).
    cursor.execute('UPDATE partido SET estado=estado WHERE id_partido=%s', (id_partido,))
    actual = obtener_partido(cursor, id_partido)
    validar_partido_registrable(cursor, id_partido, ahora)
    return actual


def auditar_correccion(cursor, partido, id_partido, usuario, descripcion):
    if partido['estado'] == 'jugado':
        registrar_cambio(cursor, id_partido, usuario['correo'], descripcion)


def comprobar_participante(cursor, id_partido, ci_jugador, controlar_suspension=True):
    cursor.execute('SELECT id_equipo FROM planilla_partido WHERE id_partido=%s AND ci_jugador=%s', (id_partido, ci_jugador))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El jugador debe figurar primero en la planilla de este partido.')
    if controlar_suspension:
        validar_jugador_no_suspendido(cursor, id_partido, ci_jugador)
    return fila[0]


def agregar_participante(cursor, id_partido, ci_jugador, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    cursor.execute('''
        SELECT id_equipo FROM equipo_jugador_torneo
        WHERE ci_jugador=%s AND id_torneo=%s AND id_equipo IN (%s,%s)
    ''', (ci_jugador, partido['id_torneo'], partido['id_equipo_local'], partido['id_equipo_visitante']))
    fila = cursor.fetchone()
    if fila is None:
        raise ValueError('El jugador no pertenece al plantel de ninguno de los dos equipos.')
    equipo = fila[0]
    validar_alta_planilla(cursor, id_partido, ci_jugador, equipo, ahora)
    cursor.execute('SELECT ci_jugador FROM planilla_partido WHERE id_partido=%s AND ci_jugador=%s', (id_partido, ci_jugador))
    if cursor.fetchone() is not None:
        raise ValueError('El jugador ya figura en esta planilla.')
    cursor.execute('INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)', (id_partido, ci_jugador, equipo))
    auditar_correccion(cursor, partido, id_partido, usuario, f'Agrega participante {ci_jugador}')


def quitar_participante(cursor, id_partido, ci_jugador, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    comprobar_participante(cursor, id_partido, ci_jugador, controlar_suspension=False)
    cursor.execute('''
        SELECT (SELECT COUNT(*) FROM gol WHERE id_partido=%s AND ci_jugador=%s)
             + (SELECT COUNT(*) FROM tarjeta WHERE id_partido=%s AND ci_jugador=%s)
    ''', (id_partido, ci_jugador, id_partido, ci_jugador))
    if cursor.fetchone()[0]:
        raise ValueError('Primero corregí o eliminá sus goles y tarjetas de este partido.')
    if partido['estado'] == 'jugado':
        cursor.execute('''
            SELECT COUNT(*) FROM planilla_partido
            WHERE id_partido=%s AND id_equipo=(
                SELECT id_equipo FROM equipo_jugador_torneo WHERE ci_jugador=%s AND id_torneo=%s
            )
        ''', (id_partido, ci_jugador, partido['id_torneo']))
        if cursor.fetchone()[0] <= 1:
            raise ValueError('Un partido jugado debe conservar participantes de ambos equipos.')
    cursor.execute('DELETE FROM planilla_partido WHERE id_partido=%s AND ci_jugador=%s', (id_partido, ci_jugador))
    auditar_correccion(cursor, partido, id_partido, usuario, f'Quita participante {ci_jugador}')


def validar_minuto(minuto):
    if type(minuto) is not int or not 0 <= minuto <= 2147483647:
        raise ValueError('El minuto debe ser un entero mayor o igual a cero.')


def agregar_gol(cursor, id_partido, ci, minuto, autogol, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    comprobar_participante(cursor, id_partido, ci)
    validar_minuto(minuto)
    if type(autogol) is not bool:
        raise ValueError('Indicá si es autogol con S o N.')
    cursor.execute('INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (%s,%s,%s,%s)', (id_partido, ci, minuto, autogol))
    identificador = cursor.lastrowid
    auditar_correccion(cursor, partido, id_partido, usuario, f'Agrega gol {identificador} de {ci}')
    return identificador


def modificar_gol(cursor, id_partido, id_gol, ci, minuto, autogol, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    cursor.execute('SELECT id_gol FROM gol WHERE id_gol=%s AND id_partido=%s', (id_gol, id_partido))
    if cursor.fetchone() is None:
        raise ValueError('Ese gol no pertenece al partido elegido.')
    comprobar_participante(cursor, id_partido, ci)
    validar_minuto(minuto)
    if type(autogol) is not bool:
        raise ValueError('Indicá si es autogol con S o N.')
    cursor.execute('UPDATE gol SET ci_jugador=%s,minuto=%s,autogol=%s WHERE id_gol=%s AND id_partido=%s', (ci, minuto, autogol, id_gol, id_partido))
    auditar_correccion(cursor, partido, id_partido, usuario, f'Modifica gol {id_gol}')


def eliminar_gol(cursor, id_partido, id_gol, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    cursor.execute('SELECT id_gol FROM gol WHERE id_gol=%s AND id_partido=%s', (id_gol, id_partido))
    if cursor.fetchone() is None:
        raise ValueError('Ese gol no pertenece al partido elegido.')
    cursor.execute('DELETE FROM gol WHERE id_gol=%s AND id_partido=%s', (id_gol, id_partido))
    auditar_correccion(cursor, partido, id_partido, usuario, f'Elimina gol {id_gol}')


def verificar_sanciones(cursor, ci, id_torneo):
    # Una corrección retroactiva de tarjetas no puede dejar participantes suspendidos.
    cursor.execute('''
        SELECT p.id_partido FROM planilla_partido pp
        JOIN partido p ON p.id_partido=pp.id_partido
        JOIN sancion_jugador s ON s.ci_jugador=pp.ci_jugador AND s.id_torneo=p.id_torneo
        WHERE pp.ci_jugador=%s AND p.id_torneo=%s
          AND p.numero_fecha BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio+s.cantidad_fechas-1
        LIMIT 1
    ''', (ci, id_torneo))
    fila = cursor.fetchone()
    if fila is not None:
        raise ValueError(f'La sanción dejaría al jugador {ci} suspendido en la planilla del partido {fila[0]}. Corregí primero esa participación.')


def recalcular_jugadores(cursor, jugadores, id_torneo):
    for ci in sorted(set(jugadores)):
        recalcular_sanciones_automaticas(cursor, ci, id_torneo)
        verificar_sanciones(cursor, ci, id_torneo)


def agregar_tarjeta(cursor, id_partido, ci, minuto, color, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    comprobar_participante(cursor, id_partido, ci)
    validar_minuto(minuto)
    if color not in ('amarilla', 'roja'):
        raise ValueError('El color debe ser amarilla o roja.')
    cursor.execute('INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,%s,%s)', (id_partido, ci, minuto, color))
    identificador = cursor.lastrowid
    recalcular_jugadores(cursor, [ci], partido['id_torneo'])
    auditar_correccion(cursor, partido, id_partido, usuario, f'Agrega tarjeta {identificador} de {ci}')
    return identificador


def modificar_tarjeta(cursor, id_partido, id_tarjeta, ci, minuto, color, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    cursor.execute('SELECT ci_jugador FROM tarjeta WHERE id_tarjeta=%s AND id_partido=%s', (id_tarjeta, id_partido))
    anterior = cursor.fetchone()
    if anterior is None:
        raise ValueError('Esa tarjeta no pertenece al partido elegido.')
    comprobar_participante(cursor, id_partido, ci)
    validar_minuto(minuto)
    if color not in ('amarilla', 'roja'):
        raise ValueError('El color debe ser amarilla o roja.')
    cursor.execute('UPDATE tarjeta SET ci_jugador=%s,minuto=%s,color=%s WHERE id_tarjeta=%s AND id_partido=%s', (ci, minuto, color, id_tarjeta, id_partido))
    recalcular_jugadores(cursor, [anterior[0], ci], partido['id_torneo'])
    auditar_correccion(cursor, partido, id_partido, usuario, f'Modifica tarjeta {id_tarjeta}')


def eliminar_tarjeta(cursor, id_partido, id_tarjeta, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    cursor.execute('SELECT ci_jugador FROM tarjeta WHERE id_tarjeta=%s AND id_partido=%s', (id_tarjeta, id_partido))
    anterior = cursor.fetchone()
    if anterior is None:
        raise ValueError('Esa tarjeta no pertenece al partido elegido.')
    cursor.execute('DELETE FROM tarjeta WHERE id_tarjeta=%s AND id_partido=%s', (id_tarjeta, id_partido))
    recalcular_jugadores(cursor, [anterior[0]], partido['id_torneo'])
    auditar_correccion(cursor, partido, id_partido, usuario, f'Elimina tarjeta {id_tarjeta}')


def marcar_jugado(cursor, id_partido, usuario, ahora=None):
    partido = preparar_registro(cursor, id_partido, usuario, ahora)
    if partido['estado'] == 'jugado':
        raise ValueError('El partido ya está marcado como jugado.')
    for equipo in (partido['id_equipo_local'], partido['id_equipo_visitante']):
        validar_min_jugadores(cursor, equipo)
        cursor.execute('SELECT ci_jugador FROM planilla_partido WHERE id_partido=%s AND id_equipo=%s', (id_partido, equipo))
        participantes = cursor.fetchall()
        if not participantes:
            raise ValueError('Cargá los participantes de ambos equipos antes de marcarlo como jugado.')
        for (ci,) in participantes:
            validar_jugador_no_suspendido(cursor, id_partido, ci)
    cursor.execute("UPDATE partido SET estado='jugado' WHERE id_partido=%s", (id_partido,))
    registrar_cambio(cursor, id_partido, usuario['correo'], 'Partido marcado como jugado')


def calcular_resultado(cursor, id_partido):
    partido = obtener_partido(cursor, id_partido)
    local = partido['id_equipo_local']
    visitante = partido['id_equipo_visitante']
    cursor.execute('''
        SELECT COALESCE(SUM(CASE
            WHEN (pp.id_equipo=%s AND COALESCE(g.autogol,0)=0)
              OR (pp.id_equipo=%s AND g.autogol=1) THEN 1 ELSE 0 END),0),
               COALESCE(SUM(CASE
            WHEN (pp.id_equipo=%s AND COALESCE(g.autogol,0)=0)
              OR (pp.id_equipo=%s AND g.autogol=1) THEN 1 ELSE 0 END),0)
        FROM gol g JOIN planilla_partido pp
          ON pp.id_partido=g.id_partido AND pp.ci_jugador=g.ci_jugador
        WHERE g.id_partido=%s
    ''', (local, visitante, visitante, local, id_partido))
    return tuple(int(valor) for valor in cursor.fetchone())


def ver_planilla(cursor, id_partido):
    cursor.execute('''
        SELECT pp.ci_jugador, j.nombre, j.apellido, e.nombre, p.numero_camiseta
        FROM planilla_partido pp
        JOIN jugador j ON j.ci=pp.ci_jugador
        JOIN equipo e ON e.id_equipo=pp.id_equipo
        JOIN equipo_jugador_torneo p ON p.id_equipo=pp.id_equipo AND p.ci_jugador=pp.ci_jugador
        WHERE pp.id_partido=%s ORDER BY pp.id_equipo,j.apellido,j.nombre
    ''', (id_partido,))
    mostrar_filas(cursor, 'CI | Nombre | Apellido | Equipo | Camiseta')


def ver_eventos(cursor, id_partido):
    cursor.execute('SELECT id_gol,ci_jugador,minuto,autogol FROM gol WHERE id_partido=%s ORDER BY minuto,id_gol', (id_partido,))
    mostrar_filas(cursor, 'ID gol | CI jugador | Minuto | Autogol (1=sí, 0=no)')
    cursor.execute('SELECT id_tarjeta,ci_jugador,minuto,color FROM tarjeta WHERE id_partido=%s ORDER BY minuto,id_tarjeta', (id_partido,))
    mostrar_filas(cursor, 'ID tarjeta | CI jugador | Minuto | Color')


def mostrar_candidatos(cursor, id_partido):
    partido = obtener_partido(cursor, id_partido)
    cursor.execute('''
        SELECT p.ci_jugador,j.nombre,j.apellido,e.nombre,
               CASE WHEN EXISTS (
                   SELECT 1 FROM sancion_jugador s WHERE s.ci_jugador=p.ci_jugador
                     AND s.id_torneo=p.id_torneo AND %s BETWEEN s.numero_fecha_inicio
                         AND s.numero_fecha_inicio+s.cantidad_fechas-1
               ) THEN 'SUSPENDIDO' ELSE 'Disponible' END
        FROM equipo_jugador_torneo p
        JOIN jugador j ON j.ci=p.ci_jugador JOIN equipo e ON e.id_equipo=p.id_equipo
        WHERE p.id_torneo=%s AND p.id_equipo IN (%s,%s)
          AND NOT EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido=%s AND pp.ci_jugador=p.ci_jugador)
        ORDER BY p.id_equipo,j.apellido,j.nombre
    ''', (partido['numero_fecha'],partido['id_torneo'],partido['id_equipo_local'],partido['id_equipo_visitante'],id_partido))
    mostrar_filas(cursor, 'CI | Nombre | Apellido | Equipo | Situación')


def leer_minuto():
    texto = input('Minuto de juego (0 o mayor): ').strip()
    if not texto.isascii() or not texto.isdecimal():
        raise ValueError('Ingresá un minuto entero mayor o igual a cero.')
    minuto = int(texto)
    validar_minuto(minuto)
    return minuto


def leer_autogol():
    opcion = input('¿Autogol? S/N: ').strip().upper()
    if opcion not in ('S','N'):
        raise ValueError('Respondé S o N.')
    return opcion == 'S'


def ejecutar_opcion(cursor, opcion, id_partido, usuario):
    if opcion == '1':
        ver_planilla(cursor,id_partido)
    elif opcion == '2':
        mostrar_candidatos(cursor,id_partido)
        agregar_participante(cursor,id_partido,leer_entero('CI del participante: '),usuario)
    elif opcion == '3':
        ver_planilla(cursor,id_partido)
        ci = leer_entero('CI del participante a quitar: ')
        if input('¿Quitar participante? Escribí SI: ').strip() != 'SI':
            return False
        quitar_participante(cursor,id_partido,ci,usuario)
    elif opcion == '4':
        ver_eventos(cursor,id_partido)
    elif opcion in ('5','6'):
        ver_planilla(cursor,id_partido)
        id_gol = None
        if opcion == '6':
            ver_eventos(cursor,id_partido)
            id_gol = leer_entero('ID del gol a corregir: ')
        ci = leer_entero('CI del jugador: ')
        minuto = leer_minuto()
        autogol = leer_autogol()
        if opcion == '5':
            agregar_gol(cursor,id_partido,ci,minuto,autogol,usuario)
        else:
            modificar_gol(cursor,id_partido,id_gol,ci,minuto,autogol,usuario)
    elif opcion == '7':
        ver_eventos(cursor,id_partido)
        identificador = leer_entero('ID del gol a eliminar: ')
        if input('¿Eliminar gol? Escribí SI: ').strip() != 'SI':
            return False
        eliminar_gol(cursor,id_partido,identificador,usuario)
    elif opcion in ('8','9'):
        ver_planilla(cursor,id_partido)
        identificador = None
        if opcion == '9':
            ver_eventos(cursor,id_partido)
            identificador = leer_entero('ID de tarjeta a corregir: ')
        ci = leer_entero('CI del jugador: ')
        minuto = leer_minuto()
        color = input('Color (amarilla/roja): ').strip().lower()
        if opcion == '8':
            agregar_tarjeta(cursor,id_partido,ci,minuto,color,usuario)
        else:
            modificar_tarjeta(cursor,id_partido,identificador,ci,minuto,color,usuario)
    elif opcion == '10':
        ver_eventos(cursor,id_partido)
        identificador = leer_entero('ID de tarjeta a eliminar: ')
        if input('¿Eliminar tarjeta? Escribí SI: ').strip() != 'SI':
            return False
        eliminar_tarjeta(cursor,id_partido,identificador,usuario)
    elif opcion == '11':
        local,visitante = calcular_resultado(cursor,id_partido)
        partido = obtener_partido(cursor,id_partido)
        print(f"Resultado local {local} - {visitante} visitante | Estado: {partido['estado']}")
        if partido['estado'] != 'jugado':
            print('Resultado provisional: todavía no cuenta para posiciones.')
    elif opcion == '12':
        if input('¿Confirmar la carga y marcar jugado? Escribí SI: ').strip() != 'SI':
            return False
        marcar_jugado(cursor,id_partido,usuario)


def menu_planillas(usuario):
    if usuario.get('rol') not in ('administrador','planillero') or not usuario.get('correo'):
        print('Necesitás iniciar sesión para registrar partidos.')
        return
    id_partido = None
    while True:
        conexion = None
        cursor = None
        try:
            conexion = conectar(usuario['rol'])
            conexion.start_transaction(isolation_level='READ COMMITTED')
            cursor = conexion.cursor()
            if id_partido is None:
                listar_partidos(cursor)
                texto = input('ID del partido a registrar (0 para volver): ').strip()
                if texto == '0':
                    return
                if not texto.isascii() or not texto.isdecimal() or not 1 <= int(texto) <= 2147483647:
                    raise ValueError('Ingresá un ID de partido positivo.')
                elegido = int(texto)
                obtener_partido(cursor,elegido)
                id_partido = elegido
            actual = obtener_partido(cursor,id_partido)
            print(f"\nREGISTRO DEL PARTIDO {id_partido} | Estado: {actual['estado']}")
            print('1. Ver planilla\n2. Agregar participante\n3. Quitar participante\n4. Ver goles y tarjetas\n5. Agregar gol\n6. Corregir gol\n7. Eliminar gol\n8. Agregar tarjeta\n9. Corregir tarjeta\n10. Eliminar tarjeta\n11. Ver resultado\n12. Marcar como jugado\n13. Elegir otro partido\n0. Volver')
            opcion = input('Elegí una opción: ').strip()
            if opcion == '0':
                return
            if opcion == '13':
                id_partido = None
                continue
            if opcion not in tuple(str(numero) for numero in range(1,13)):
                print('Opción inválida.')
                continue
            resultado = ejecutar_opcion(cursor,opcion,id_partido,usuario)
            if opcion not in ('1','4','11'):
                if resultado is False:
                    print('Operación cancelada.')
                else:
                    conexion.commit()
                    print('Operación guardada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('El participante ya figura en la planilla.')
            elif error.errno == 1452:
                print('Uno de los registros relacionados no existe.')
            elif error.errno == 1451:
                print('Hay registros relacionados que primero deben corregirse.')
            elif error.errno in (1142,1143):
                print('Faltan permisos de MySQL para esta operación.')
            elif error.errno in (1205,1213):
                print('Otra operación está usando estos datos. Volvé a intentarlo.')
            else:
                print(f'No se pudo registrar el partido (MySQL {error.errno}).')
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
