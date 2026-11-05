"""Pruebas del registro deportivo. Siempre revierte sus registros temporales."""
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import patch

from src.conexion import conectar
import src.planillas as p
from src.partidos import guardar_programacion, obtener_partido


def esperar_error(cursor, descripcion, mensaje, funcion, *args):
    cursor.execute('SAVEPOINT prueba_rechazo')
    try:
        try:
            funcion(*args)
        except ValueError as error:
            assert mensaje in str(error), f'{descripcion}: {error}'
        else:
            raise AssertionError(f'{descripcion}: debía rechazar la operación')
    finally:
        cursor.execute('ROLLBACK TO SAVEPOINT prueba_rechazo')
        cursor.execute('RELEASE SAVEPOINT prueba_rechazo')
    print('OK: '+descripcion)


def totales(cursor):
    resultado=[]
    for tabla in ('torneo','equipo','equipo_jugador_torneo','partido','planilla_partido','gol','tarjeta','sancion_jugador','cambios'):
        cursor.execute('SELECT COUNT(*) FROM '+tabla)
        resultado.append(cursor.fetchone()[0])
    return resultado


def ejecutar(cursor):
    cursor.execute('SELECT correo FROM login WHERE rol=%s ORDER BY correo LIMIT 1',('planillero',))
    correo=cursor.fetchone()
    assert correo, 'Creá primero el usuario planillero de la aplicación.'
    usuario={'rol':'planillero','correo':correo[0]}
    cursor.execute('SELECT anio FROM torneo WHERE semestre=%s',('Primero',))
    usados={f[0] for f in cursor.fetchall()}
    anio=next(n for n in range(2060,9999) if n not in usados)
    cursor.execute('INSERT INTO torneo (nombre,anio,semestre,estado) VALUES (%s,%s,%s,%s)',
                   ('Pruebas temporales planillas',anio,'Primero','inscripción'))
    torneo=cursor.lastrowid
    cursor.execute('''
        SELECT e.id_equipo,e.id_facultad,e.ci_capitan FROM equipo e
        WHERE e.id_torneo <> %s AND
          (SELECT COUNT(*) FROM equipo_jugador_torneo ej WHERE ej.id_equipo=e.id_equipo)>=5
        ORDER BY e.id_equipo LIMIT 5
    ''',(torneo,))
    fuentes=cursor.fetchall()
    assert len(fuentes)==5
    equipos=[]
    planteles=[]
    for numero,(origen,facultad,capitan) in enumerate(fuentes):
        cursor.execute('INSERT INTO equipo (nombre,id_torneo,id_facultad,ci_capitan) VALUES (%s,%s,%s,%s)',
                       (f'Planillas prueba {numero}',torneo,facultad,capitan))
        equipo=cursor.lastrowid
        equipos.append(equipo)
        cursor.execute('''
            INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo)
            SELECT %s,ci_jugador,%s FROM equipo_jugador_torneo
            WHERE id_equipo=%s ORDER BY ci_jugador LIMIT 5
        ''',(equipo,torneo,origen))
        cursor.execute('SELECT ci_jugador FROM equipo_jugador_torneo WHERE id_equipo=%s ORDER BY ci_jugador',(equipo,))
        planteles.append([f[0] for f in cursor.fetchall()])
    cursor.execute('SELECT id_turno,hora_fin FROM turno ORDER BY id_turno LIMIT 1')
    turno,hora_fin=cursor.fetchone()
    cursor.execute('SELECT id_complejo,nombre_cancha FROM cancha ORDER BY id_complejo,nombre_cancha LIMIT 1')
    complejo,cancha=cursor.fetchone()
    cursor.execute('SELECT ci_arbitro FROM arbitro ORDER BY ci_arbitro LIMIT 1')
    arbitro=cursor.fetchone()[0]
    partidos=[]
    for jornada,rival in enumerate(equipos[1:],1):
        datos=dict(id_torneo=torneo,numero_fecha=jornada,id_equipo_local=equipos[0],id_equipo_visitante=rival,
                   dia=date(2030,1,jornada),id_turno=turno,id_complejo=complejo,nombre_cancha=cancha,ci_arbitro=arbitro)
        partidos.append(guardar_programacion(cursor,datos))
    primero,segundo,tercero,cuarto=partidos
    fin=datetime(2030,1,1)+hora_fin
    ahora=fin+timedelta(hours=1)
    ci=planteles[0][0]; compañero=planteles[0][1]; rival=planteles[1][0]; ajeno=planteles[2][0]
    esperar_error(cursor,'registro antes del fin','todavía no',p.agregar_participante,cursor,primero,ci,usuario,fin-timedelta(seconds=1))
    esperar_error(cursor,'rol no autorizado','autenticado',p.agregar_participante,cursor,primero,ci,{'rol':'otro','correo':correo[0]},ahora)
    esperar_error(cursor,'participante de otro equipo','ninguno de los dos',p.agregar_participante,cursor,primero,ajeno,usuario,ahora)
    p.agregar_participante(cursor,primero,ci,usuario,ahora)
    print('OK: agregar participante del plantel')
    esperar_error(cursor,'participante duplicado','ya figura',p.agregar_participante,cursor,primero,ci,usuario,ahora)
    esperar_error(cursor,'gol de jugador sin planilla','figurar primero',p.agregar_gol,cursor,primero,rival,10,False,usuario,ahora)
    esperar_error(cursor,'tarjeta de jugador sin planilla','figurar primero',p.agregar_tarjeta,cursor,primero,rival,10,'roja',usuario,ahora)
    esperar_error(cursor,'jugado sin participantes visitantes','ambos equipos',p.marcar_jugado,cursor,primero,usuario,ahora)
    p.agregar_participante(cursor,primero,rival,usuario,ahora)
    p.agregar_participante(cursor,primero,compañero,usuario,ahora)
    p.quitar_participante(cursor,primero,compañero,usuario,ahora)
    print('OK: agregar y quitar participante sin eventos')
    esperar_error(cursor,'minuto negativo','mayor o igual',p.agregar_gol,cursor,primero,ci,-1,False,usuario,ahora)
    gol=p.agregar_gol(cursor,primero,ci,0,False,usuario,ahora)
    assert p.calcular_resultado(cursor,primero)==(1,0)
    autogol=p.agregar_gol(cursor,primero,ci,5,True,usuario,ahora)
    assert p.calcular_resultado(cursor,primero)==(1,1)
    print('OK: gol normal y autogol sumado al rival')
    esperar_error(cursor,'quitar participante con gol','goles y tarjetas',p.quitar_participante,cursor,primero,ci,usuario,ahora)
    p.modificar_gol(cursor,primero,gol,rival,8,False,usuario,ahora)
    assert p.calcular_resultado(cursor,primero)==(0,2)
    print('OK: corregir goleador y recalcular resultado')
    esperar_error(cursor,'gol de otro partido','no pertenece',p.eliminar_gol,cursor,segundo,gol,usuario,ahora+timedelta(days=1))
    p.eliminar_gol(cursor,primero,autogol,usuario,ahora)
    assert p.calcular_resultado(cursor,primero)==(0,1)
    print('OK: eliminar gol actualiza resultado')
    esperar_error(cursor,'color inválido','amarilla o roja',p.agregar_tarjeta,cursor,primero,ci,10,'azul',usuario,ahora)
    tarjeta=p.agregar_tarjeta(cursor,primero,ci,10,'roja',usuario,ahora)
    cursor.execute('SELECT numero_fecha_inicio,cantidad_fechas FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s AND motivo=%s',(ci,torneo,'roja'))
    assert cursor.fetchall()==[(2,1)]
    print('OK: roja genera suspensión para la jornada siguiente')
    esperar_error(cursor,'suspendido en siguiente jornada','suspendido',p.agregar_participante,cursor,segundo,ci,usuario,ahora+timedelta(days=1))
    p.modificar_tarjeta(cursor,primero,tarjeta,ci,11,'amarilla',usuario,ahora)
    cursor.execute('SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s',(ci,torneo)); assert cursor.fetchone()[0]==0
    print('OK: corregir roja a amarilla retira sanción automática')
    p.agregar_participante(cursor,segundo,ci,usuario,ahora+timedelta(days=1))
    p.agregar_participante(cursor,tercero,ci,usuario,ahora+timedelta(days=2))
    p.agregar_tarjeta(cursor,segundo,ci,15,'amarilla',usuario,ahora+timedelta(days=1))
    tercera=p.agregar_tarjeta(cursor,tercero,ci,20,'amarilla',usuario,ahora+timedelta(days=2))
    cursor.execute('SELECT numero_fecha_inicio,cantidad_fechas FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s',(ci,torneo))
    assert cursor.fetchall()==[(4,1)]
    print('OK: tres amarillas generan suspensión en jornada cuatro')
    esperar_error(cursor,'suspendido por tres amarillas','suspendido',p.agregar_participante,cursor,cuarto,ci,usuario,ahora+timedelta(days=3))
    p.eliminar_tarjeta(cursor,tercero,tercera,usuario,ahora+timedelta(days=2))
    cursor.execute('SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s',(ci,torneo)); assert cursor.fetchone()[0]==0
    print('OK: eliminar tarjeta recalcula la sanción')
    esperar_error(cursor,'roja retroactiva incompatible con otra planilla','Corregí primero',p.modificar_tarjeta,cursor,primero,tarjeta,ci,11,'roja',usuario,ahora)
    cursor.execute('INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas) VALUES (%s,%s,%s,%s,%s)',(ci,torneo,'disciplinaria',10,2))
    p.modificar_tarjeta(cursor,primero,tarjeta,ci,12,'amarilla',usuario,ahora)
    cursor.execute("SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s AND motivo='disciplinaria'",(ci,torneo)); assert cursor.fetchone()[0]==1
    print('OK: sanciones disciplinarias preservadas')
    p.marcar_jugado(cursor,primero,usuario,ahora)
    assert obtener_partido(cursor,primero)['estado']=='jugado'
    print('OK: marcar jugado después del horario con participantes de ambos equipos')
    cursor.execute('SELECT COUNT(*) FROM cambios WHERE id_partido=%s',(primero,)); auditorias=cursor.fetchone()[0]
    p.modificar_gol(cursor,primero,gol,ci,15,False,usuario,fin+timedelta(hours=48))
    assert p.calcular_resultado(cursor,primero)==(1,0)
    cursor.execute('SELECT correo_cambiante FROM cambios WHERE id_partido=%s ORDER BY id_cambio DESC LIMIT 1',(primero,)); assert cursor.fetchone()[0]==correo[0]
    print('OK: corrección a las 48 horas y auditoría del usuario')
    esperar_error(cursor,'corrección después de 48 horas','48 horas',p.modificar_gol,cursor,primero,gol,ci,16,False,usuario,fin+timedelta(hours=48,seconds=1))
    esperar_error(cursor,'alta participante fuera de ventana','48 horas',p.agregar_participante,cursor,primero,compañero,usuario,fin+timedelta(hours=49))
    esperar_error(cursor,'baja tarjeta fuera de ventana','48 horas',p.eliminar_tarjeta,cursor,primero,tarjeta,usuario,fin+timedelta(hours=49))
    esperar_error(cursor,'marcar jugado dos veces','ya está marcado',p.marcar_jugado,cursor,primero,usuario,ahora)
    esperar_error(cursor,'quitar último participante de equipo','ambos equipos',p.quitar_participante,cursor,primero,rival,usuario,ahora)
    for estado in ('cancelado','postergado'):
        cursor.execute('UPDATE partido SET estado=%s WHERE id_partido=%s',(estado,cuarto))
        esperar_error(cursor,'no registrar partido '+estado,'no es registrable',p.agregar_participante,cursor,cuarto,compañero,usuario,ahora+timedelta(days=3))
    with patch('builtins.input',side_effect=['-1']):
        try:
            p.leer_minuto()
            raise AssertionError('Minuto negativo aceptado')
        except ValueError:
            pass
    with patch('builtins.input',side_effect=['0']):
        assert p.leer_minuto()==0
    print('OK: validación de minuto desde consola')



def probar_permisos_planillero():
    conexion=conectar('administrador'); cursor=conexion.cursor()
    try:
        cursor.execute("SELECT correo FROM login WHERE rol='planillero' ORDER BY correo LIMIT 1")
        usuario={'rol':'planillero','correo':cursor.fetchone()[0]}
    finally:
        cursor.close(); conexion.close()
    conexion=conectar('planillero'); cursor=conexion.cursor()
    conexion.start_transaction(isolation_level='READ COMMITTED')
    try:
        cursor.execute("""
            SELECT p.id_partido,p.id_torneo,p.numero_fecha,p.id_equipo_local,p.id_equipo_visitante,
                   TIMESTAMP(p.dia,t.hora_fin)
            FROM partido p JOIN turno t ON t.id_turno=p.id_turno
            WHERE p.estado='programado'
              AND NOT EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido=p.id_partido)
            ORDER BY p.id_partido LIMIT 1
        """)
        fila=cursor.fetchone()
        assert fila is not None, 'Se necesita un partido programado sin planilla para probar los permisos.'
        id_partido,torneo,jornada,local,visitante,fin=fila
        ahora=fin+timedelta(hours=1)
        participantes=[]
        for equipo in (local,visitante):
            cursor.execute("""
                SELECT ej.ci_jugador FROM equipo_jugador_torneo ej
                WHERE ej.id_equipo=%s AND ej.id_torneo=%s
                  AND NOT EXISTS (SELECT 1 FROM sancion_jugador s
                      WHERE s.ci_jugador=ej.ci_jugador AND s.id_torneo=ej.id_torneo
                        AND %s BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio+s.cantidad_fechas-1)
                ORDER BY ej.ci_jugador LIMIT 1
            """,(equipo,torneo,jornada))
            ci=cursor.fetchone()[0]
            participantes.append(ci)
            p.agregar_participante(cursor,id_partido,ci,usuario,ahora)
        print('OK: cuenta MySQL planillero agrega participantes de ambos equipos')
        gol=p.agregar_gol(cursor,id_partido,participantes[0],1,False,usuario,ahora)
        p.modificar_gol(cursor,id_partido,gol,participantes[1],2,True,usuario,ahora)
        p.eliminar_gol(cursor,id_partido,gol,usuario,ahora)
        print('OK: cuenta MySQL planillero crea, corrige y elimina goles')
        tarjeta=p.agregar_tarjeta(cursor,id_partido,participantes[0],3,'amarilla',usuario,ahora)
        p.modificar_tarjeta(cursor,id_partido,tarjeta,participantes[0],4,'amarilla',usuario,ahora)
        p.eliminar_tarjeta(cursor,id_partido,tarjeta,usuario,ahora)
        print('OK: cuenta MySQL planillero crea, corrige y elimina tarjetas y recalcula sanciones')
        p.marcar_jugado(cursor,id_partido,usuario,ahora)
        assert obtener_partido(cursor,id_partido)['estado']=='jugado'
        gol=p.agregar_gol(cursor,id_partido,participantes[0],5,False,usuario,ahora)
        cursor.execute('SELECT correo_cambiante FROM cambios WHERE id_partido=%s ORDER BY id_cambio DESC LIMIT 1',(id_partido,))
        assert cursor.fetchone()[0]==usuario['correo']
        print('OK: cuenta MySQL planillero marca jugado y registra auditoría')
    finally:
        conexion.rollback();cursor.close();conexion.close()
    for rol in ('administrador','planillero'):
        salida=StringIO()
        with patch('builtins.input',side_effect=[str(id_partido),'1','4','11','13','0']),redirect_stdout(salida):
            p.menu_planillas(dict(usuario,rol=rol))
        assert 'MySQL' not in salida.getvalue()
        assert 'Resultado local' in salida.getvalue()
        print('OK: consultas y selección de partido en menú de '+rol)


def main():
    conexion=conectar('administrador'); cursor=conexion.cursor()
    antes=totales(cursor); conexion.rollback()
    try:
        conexion.start_transaction(isolation_level='READ COMMITTED')
        ejecutar(cursor)
    finally:
        conexion.rollback(); cursor.close(); conexion.close()
    conexion=conectar('administrador'); cursor=conexion.cursor()
    try:
        assert totales(cursor)==antes, 'Cambió la cantidad de registros originales.'
    finally:
        cursor.close(); conexion.close()
    probar_permisos_planillero()
    print('Pruebas de planillas terminadas. Datos temporales revertidos.')


if __name__=='__main__':
    main()
