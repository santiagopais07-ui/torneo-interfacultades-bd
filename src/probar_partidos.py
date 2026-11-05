"""Pruebas de partidos con datos temporales: siempre se ejecuta rollback."""
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from unittest.mock import patch

from src.conexion import conectar
from src.partidos import (
    guardar_programacion, cambiar_estado_partido, obtener_partido,
    cancelar_partido, crear_partido, modificar_partido, menu_partidos,
)


def esperar_error(descripcion, mensaje, funcion, *args):
    try:
        funcion(*args)
    except ValueError as error:
        assert mensaje in str(error), f'{descripcion}: {error}'
    else:
        raise AssertionError(f'{descripcion}: debía rechazar la operación')
    print('OK: ' + descripcion)


def contar_registros(cursor):
    cantidades = []
    for tabla in ('torneo', 'equipo', 'equipo_jugador_torneo', 'partido', 'planilla_partido'):
        cursor.execute('SELECT COUNT(*) FROM ' + tabla)
        cantidades.append(cursor.fetchone()[0])
    return cantidades


def ejecutar(cursor):
    cursor.execute('''
        SELECT e.id_equipo, e.id_facultad, e.ci_capitan, e.id_torneo
        FROM equipo e WHERE (
            SELECT COUNT(*) FROM equipo_jugador_torneo p
            WHERE p.id_equipo=e.id_equipo
        ) >= 5 ORDER BY e.id_equipo LIMIT 5
    ''')
    originales = cursor.fetchall()
    assert len(originales) == 5, 'Se requieren cinco equipos de datos de prueba.'
    cursor.execute('SELECT anio FROM torneo WHERE semestre=%s', ('Primero',))
    usados = {fila[0] for fila in cursor.fetchall()}
    anio = next(valor for valor in range(2050, 9999) if valor not in usados)
    cursor.execute('INSERT INTO torneo (nombre,anio,semestre,estado) VALUES (%s,%s,%s,%s)',
                   ('Pruebas temporales de partidos', anio, 'Primero', 'inscripción'))
    torneo = cursor.lastrowid
    equipos = []
    capitanes = []
    for numero, (origen, facultad, capitan, _) in enumerate(originales):
        cursor.execute('INSERT INTO equipo (nombre,id_torneo,id_facultad,ci_capitan) VALUES (%s,%s,%s,%s)',
                       (f'Prueba temporal {numero}', torneo, facultad, capitan))
        equipo = cursor.lastrowid
        equipos.append(equipo)
        capitanes.append(capitan)
        cursor.execute('''
            INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo,numero_camiseta)
            SELECT %s,ci_jugador,%s,numero_camiseta FROM equipo_jugador_torneo
            WHERE id_equipo=%s ORDER BY ci_jugador LIMIT %s
        ''', (equipo, torneo, origen, 2 if numero == 4 else 5))
    a,b,c,d,incompleto = equipos
    cursor.execute('SELECT id_turno FROM turno ORDER BY id_turno LIMIT 1')
    turno = cursor.fetchone()[0]
    cursor.execute('SELECT id_complejo,nombre_cancha FROM cancha ORDER BY id_complejo,nombre_cancha LIMIT 2')
    canchas = cursor.fetchall()
    assert len(canchas) == 2
    cursor.execute('SELECT ci_arbitro FROM arbitro ORDER BY ci_arbitro LIMIT 2')
    arbitros = [fila[0] for fila in cursor.fetchall()]
    assert len(arbitros) == 2
    datos = dict(id_torneo=torneo, numero_fecha=1, id_equipo_local=a, id_equipo_visitante=b,
                 dia=date(2070,1,1), id_turno=turno, id_complejo=canchas[0][0],
                 nombre_cancha=canchas[0][1], ci_arbitro=arbitros[0])
    identificador = guardar_programacion(cursor, datos)
    assert obtener_partido(cursor, identificador)['estado'] == 'programado'
    print('OK: alta de partido válido')
    guardar_programacion(cursor, datos, identificador)
    print('OK: modificar excluye el propio partido de las validaciones')
    esperar_error('equipo contra sí mismo','sí mismo',guardar_programacion,cursor,dict(datos,id_equipo_visitante=a))
    esperar_error('equipo de otra edición','edición elegida',guardar_programacion,cursor,dict(datos,id_equipo_visitante=originales[0][0]))
    esperar_error('plantel con menos de cinco','al menos 5',guardar_programacion,cursor,dict(datos,id_equipo_visitante=incompleto))
    esperar_error('rival repetido con localía invertida','ya se enfrentaron',guardar_programacion,cursor,
                  dict(datos,numero_fecha=2,id_equipo_local=b,id_equipo_visitante=a))
    esperar_error('equipo con otro partido en la jornada','ya tiene un partido',guardar_programacion,cursor,
                  dict(datos,id_equipo_local=a,id_equipo_visitante=c))
    otros = dict(datos,id_equipo_local=c,id_equipo_visitante=d)
    esperar_error('cancha ocupada','cancha ya está ocupada',guardar_programacion,cursor,otros)
    otra_cancha = dict(otros,id_complejo=canchas[1][0],nombre_cancha=canchas[1][1])
    esperar_error('árbitro ocupado','árbitro ya tiene',guardar_programacion,cursor,otra_cancha)
    segundo = guardar_programacion(cursor,dict(otra_cancha,ci_arbitro=arbitros[1]))
    print('OK: dos partidos simultáneos con equipos, canchas y árbitros distintos')
    esperar_error('cancha inexistente','cancha no existe',guardar_programacion,cursor,
                  dict(datos,numero_fecha=2,dia=date(2070,1,2),id_equipo_visitante=c,nombre_cancha='No existe cancha temporal'))
    esperar_error('árbitro inexistente','árbitro no existe',guardar_programacion,cursor,
                  dict(otros,numero_fecha=2,dia=date(2070,1,2),id_equipo_local=a,id_equipo_visitante=c,ci_arbitro=-1))
    esperar_error('turno inexistente','turno no existe',guardar_programacion,cursor,
                  dict(datos,numero_fecha=2,id_equipo_visitante=c,id_turno=-1))
    esperar_error('número de jornada inválido','entero positivo',guardar_programacion,cursor,dict(datos,numero_fecha=0))
    cambiar_estado_partido(cursor,identificador,'postergado')
    assert obtener_partido(cursor,identificador)['estado']=='postergado'
    print('OK: postergar partido')
    nuevos=dict(datos,dia=date(2070,1,2))
    guardar_programacion(cursor,nuevos,identificador)
    assert obtener_partido(cursor,identificador)['estado']=='programado'
    print('OK: reprogramar partido postergado')
    cambiar_estado_partido(cursor,identificador,'cancelado')
    assert obtener_partido(cursor,identificador)['estado']=='cancelado'
    print('OK: baja lógica conserva el partido')
    esperar_error('no reactivar cancelado','jugado o cancelado',guardar_programacion,cursor,nuevos,identificador)
    esperar_error('cancelado ocupa jornada','ya tiene un partido',guardar_programacion,cursor,
                  dict(nuevos,id_equipo_visitante=c))
    repeticion=guardar_programacion(cursor,dict(datos,numero_fecha=2,dia=date(2070,1,3)))
    print('OK: repetir rival si el anterior está cancelado, en otra jornada')
    esperar_error('cancelado conserva la cancha','cancha ya está ocupada',guardar_programacion,cursor,
                  dict(nuevos,numero_fecha=2,id_equipo_local=c,id_equipo_visitante=d),segundo)
    con_planilla=guardar_programacion(cursor,dict(datos,numero_fecha=3,dia=date(2070,1,4),id_equipo_visitante=c))
    cursor.execute('INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)',
                   (con_planilla,capitanes[0],a))
    esperar_error('no reprogramar con planilla','ya tiene planilla',guardar_programacion,cursor,
                  dict(datos,numero_fecha=3,dia=date(2070,1,5),id_equipo_visitante=c),con_planilla)
    esperar_error('no cancelar con planilla','ya tiene planilla',cambiar_estado_partido,cursor,con_planilla,'cancelado')
    cursor.execute('UPDATE partido SET estado=%s WHERE id_partido=%s',('jugado',segundo))
    esperar_error('no cancelar jugado','ya fue jugado',cambiar_estado_partido,cursor,segundo,'cancelado')
    esperar_error('no postergar jugado','ya fue jugado',cambiar_estado_partido,cursor,segundo,'postergado')
    esperar_error('no reprogramar jugado','jugado o cancelado',guardar_programacion,cursor,
                  dict(otra_cancha,ci_arbitro=arbitros[1]),segundo)
    with patch('builtins.input',side_effect=[str(repeticion),'NO']):
        assert cancelar_partido(cursor) is False
    assert obtener_partido(cursor,repeticion)['estado']=='programado'
    print('OK: cancelar confirmación conserva el estado')
    # Recorremos también las funciones que reciben datos desde la consola.
    entradas = [str(torneo), '4', str(b), str(d), '2070-02-01', str(turno),
                str(canchas[0][0]), canchas[0][1], str(arbitros[0])]
    with patch('builtins.input', side_effect=entradas), redirect_stdout(StringIO()):
        crear_partido(cursor)
    partido_ui = cursor.lastrowid
    assert obtener_partido(cursor, partido_ui)['numero_fecha'] == 4
    entradas = [str(partido_ui), '5', str(b), str(d), '2070-02-02', str(turno),
                str(canchas[0][0]), canchas[0][1], str(arbitros[0])]
    with patch('builtins.input', side_effect=entradas), redirect_stdout(StringIO()):
        modificar_partido(cursor)
    assert obtener_partido(cursor, partido_ui)['numero_fecha'] == 5
    print('OK: alta y modificación mediante las preguntas de consola')
    cursor.execute('UPDATE torneo SET estado=%s WHERE id_torneo=%s',('finalizado',torneo))
    esperar_error('torneo finalizado','torneo finalizado',guardar_programacion,cursor,datos)
    with patch('src.partidos.conectar') as conectar_mock, redirect_stdout(StringIO()):
        menu_partidos({'rol':'planillero'})
        conectar_mock.assert_not_called()
    print('OK: planillero no puede gestionar programación')


def main():
    conexion=conectar('administrador')
    cursor=conexion.cursor()
    antes=contar_registros(cursor)
    conexion.rollback()
    try:
        conexion.start_transaction(isolation_level='READ COMMITTED')
        ejecutar(cursor)
    finally:
        conexion.rollback()
        cursor.close()
        conexion.close()
    conexion=conectar('administrador')
    cursor=conexion.cursor()
    try:
        assert contar_registros(cursor)==antes, 'Cambió la cantidad de registros originales.'
    finally:
        cursor.close()
        conexion.close()
    print('Pruebas terminadas. Los datos temporales fueron revertidos.')


if __name__=='__main__':
    main()
