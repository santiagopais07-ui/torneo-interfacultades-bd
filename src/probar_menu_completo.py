"""Prueba de navegación, permisos SQL y guardado real de un jugador temporal."""
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from uuid import uuid4
import mysql.connector
from src.conexion import conectar
from src.probar_integracion import huella
from src import jugadores, reportes
import src.main as app


def snapshot():
    c=conectar('administrador'); q=c.cursor()
    try: return huella(q)
    finally: q.close(); c.close()


def main():
    antes=snapshot()
    u={'rol':'administrador','correo':'admin@correo.ucu.edu.uy'}
    # La contraseña real no se conoce ni se cambia: el login se probó aparte con un hash temporal.
    respuestas=['1',u['correo']]
    for opcion in range(1,10): respuestas += [str(opcion),'0']
    respuestas += ['0','0']
    with patch.object(app,'autenticar',return_value=u),patch.object(app,'getpass',return_value='prueba'),patch('builtins.input',side_effect=respuestas),redirect_stdout(StringIO()) as salida:
        app.main()
    assert 'No se pudo' not in salida.getvalue(),salida.getvalue()
    assert '9. Gestionar torneos' in salida.getvalue()
    print('OK: inicio, los nueve submenús, regreso, cierre de sesión y salida')
    with patch('builtins.input',side_effect=['1',*[str(i) for i in range(1,13)],'0']),redirect_stdout(StringIO()) as salida:
        reportes.menu_reportes()
    assert 'No se pudieron' not in salida.getvalue(),salida.getvalue()
    print('OK: los doce reportes desde el menú de consola')
    c=conectar('planillero'); q=c.cursor()
    try:
        for sql in ('SELECT correo FROM login LIMIT 1','UPDATE jugador SET nombre=nombre WHERE 1=0','UPDATE equipo SET nombre=nombre WHERE 1=0','UPDATE torneo SET estado=estado WHERE 1=0','UPDATE cancha SET techada=techada WHERE 1=0','UPDATE arbitro SET nombre=nombre WHERE 1=0','UPDATE partido SET dia=dia WHERE 1=0','DELETE FROM partido WHERE 1=0'):
            try:
                q.execute(sql)
                if q.with_rows: q.fetchall()
            except mysql.connector.Error as error:
                assert error.errno in (1142,1143),error
            else: raise AssertionError('Permiso inesperado: '+sql)
    finally: c.rollback();q.close();c.close()
    print('OK: ocho operaciones administrativas rechazadas por MySQL al planillero')
    c=conectar('administrador');q=c.cursor()
    q.execute('SELECT ci FROM jugador'); existentes={r[0] for r in q.fetchall()}; q.close();c.close()
    ci=next(i for i in range(2099000000,2099001000) if i not in existentes)
    correo=uuid4().hex[:15]+'@example.com'
    try:
        with patch('builtins.input',side_effect=['2',str(ci),'Temporal','Prueba',correo,'2000-01-01','1','grado','0']),redirect_stdout(StringIO()) as salida:
            jugadores.menu_jugadores(u)
        assert 'Operación guardada correctamente' in salida.getvalue(),salida.getvalue()
        c=conectar('administrador');q=c.cursor()
        q.execute('SELECT email FROM jugador WHERE ci=%s',(ci,)); assert q.fetchone()[0]==correo
        q.close();c.close()
        print('OK: alta desde menú con commit real, visible desde una segunda conexión')
    finally:
        with patch('builtins.input',side_effect=['4',str(ci),'SI','0']),redirect_stdout(StringIO()):
            jugadores.menu_jugadores(u)
    assert snapshot()==antes,'Cambió alguna fila original.'
    print('OK: baja desde menú con commit real; todas las filas originales conservadas')


if __name__=='__main__': main()
