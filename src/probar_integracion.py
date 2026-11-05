"""Recorridos de gestión contra MySQL; todas las escrituras se revierten."""
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from datetime import date
from uuid import uuid4
from hashlib import sha256
import importlib
import mysql.connector
from werkzeug.security import generate_password_hash
from src.conexion import conectar
from src import jugadores as j, infraestructura as infra, personas_partido as personas
from src import equipos, sanciones, torneos
import src.main as app


class ConexionPrueba:
    """El menú ejecuta SQL real, pero la prueba conserva una única transacción."""
    def __init__(self, conexion):
        self.conexion = conexion
    def cursor(self, *args, **kwargs):
        return self.conexion.cursor(*args, **kwargs)
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass
    def start_transaction(self, **kwargs):
        pass


def huella(cursor):
    cursor.execute('SHOW TABLES')
    tablas = [r[0] for r in cursor.fetchall()]
    resultado = {}
    for tabla in tablas:
        cursor.execute('SELECT * FROM `'+tabla+'`')
        # Compara todas las filas; no muestra contraseñas ni datos personales.
        filas = sorted(repr(r) for r in cursor.fetchall())
        resultado[tabla] = sha256(repr(filas).encode()).hexdigest()
    return resultado


def main():
    conexion = conectar('administrador')
    cursor = conexion.cursor()
    antes = huella(cursor)
    proxy = ConexionPrueba(conexion)
    usuario = {'rol':'administrador','correo':'prueba@example.com'}
    comprobaciones = []
    def ok(nombre):
        comprobaciones.append(nombre)
        print('OK: '+nombre)
    def entrada(funcion, respuestas, *args):
        with patch('builtins.input', side_effect=[str(v) for v in respuestas]), redirect_stdout(StringIO()) as salida:
            resultado = funcion(*args)
        return resultado, salida.getvalue()
    def falla(funcion, *args):
        try:
            funcion(*args)
        except (ValueError, mysql.connector.Error):
            return
        raise AssertionError('Se esperaba rechazo: '+funcion.__name__)
    def valor(sql, parametros=()):
        cursor.execute(sql,parametros)
        return cursor.fetchone()[0]
    try:
        ci = next(i for i in range(2100000000,2100001000) if not valor('SELECT COUNT(*) FROM jugador WHERE ci=%s',(i,)))
        correo = uuid4().hex[:15]+'@example.com'
        entrada(j.agregar,[ci,'José','Prueba',correo,'2000-01-01',1,'grado'],cursor)
        assert valor('SELECT nombre FROM jugador WHERE ci=%s',(ci,)) == 'José'
        ok('alta de jugador, tildes y consulta')
        entrada(j.modificar,[ci,'Josefina','Prueba',correo,'2000-01-02',1,'grado'],cursor)
        assert valor('SELECT nombre FROM jugador WHERE ci=%s',(ci,))=='Josefina'
        ok('modificación de jugador')
        with patch('builtins.input',side_effect=[str(ci),'NO']):
            assert j.eliminar(cursor) is False
        assert valor('SELECT COUNT(*) FROM jugador WHERE ci=%s',(ci,))==1
        entrada(j.eliminar,[ci,'SI'],cursor)
        assert valor('SELECT COUNT(*) FROM jugador WHERE ci=%s',(ci,))==0
        ok('baja cancelada y baja confirmada de jugador')
        with patch('builtins.input',side_effect=['Nombre','Apellido','email-invalido']):
            falla(j.leer_datos,cursor)
        with patch('builtins.input',return_value='-1'):
            falla(j.leer_entero,'Número: ')
        with patch('builtins.input',side_effect=['Nombre','Apellido',correo,'9999-01-01']):
            falla(j.leer_datos,cursor)
        ok('rechazo de email inválido, entero negativo y nacimiento futuro')
        with patch('builtins.input',side_effect=['50000001','SI']):
            falla(j.eliminar,cursor)
        ok('protección de jugador relacionado por claves foráneas')

        entrada(infra.crear_complejo,['Complejo temporal','Dirección 123','Montevideo'],cursor)
        complejo=cursor.lastrowid
        entrada(infra.modificar_complejo,[complejo,'Complejo cambiado','',''],cursor)
        assert valor('SELECT nombre FROM complejo WHERE id_complejo=%s',(complejo,))=='Complejo cambiado'
        entrada(infra.crear_cancha,[complejo,'Cancha temporal',1,'S'],cursor)
        entrada(infra.modificar_cancha,[complejo,'Cancha temporal',2,'N'],cursor)
        assert valor('SELECT superficie FROM cancha WHERE id_complejo=%s',(complejo,))=='parquet'
        with patch('builtins.input',side_effect=[str(complejo)]):
            falla(infra.eliminar_complejo,cursor)
        entrada(infra.eliminar_cancha,[complejo,'Cancha temporal','NO'],cursor)
        assert valor('SELECT COUNT(*) FROM cancha WHERE id_complejo=%s',(complejo,))==1
        entrada(infra.eliminar_cancha,[complejo,'Cancha temporal','SI'],cursor)
        entrada(infra.eliminar_complejo,[complejo,'SI'],cursor)
        assert valor('SELECT COUNT(*) FROM complejo WHERE id_complejo=%s',(complejo,))==0
        with patch('builtins.input',side_effect=['1','Cancha 001']):
            falla(infra.eliminar_cancha,cursor)
        ok('ABM de complejos y canchas, cancelación y protección de relaciones')

        entrada(personas.crear_arbitro,[ci,'Árbitro','Temporal',correo],cursor)
        entrada(personas.modificar_arbitro,[ci,'Árbitro nuevo','Temporal',correo],cursor)
        assert valor('SELECT nombre FROM arbitro WHERE ci_arbitro=%s',(ci,))=='Árbitro nuevo'
        entrada(personas.eliminar_arbitro,[ci,'NO'],cursor)
        assert valor('SELECT COUNT(*) FROM arbitro WHERE ci_arbitro=%s',(ci,))==1
        entrada(personas.eliminar_arbitro,[ci,'SI'],cursor)
        with patch('builtins.input',side_effect=['40000001']):
            falla(personas.eliminar_arbitro,cursor)
        entrada(personas.crear_espectador,['Ana','Temporal','','2000-01-01','externo',1],cursor)
        asistencia=cursor.lastrowid
        entrada(personas.modificar_espectador,[asistencia,'Ana nueva','Temporal',ci,'2000-01-01','facultad',2],cursor)
        assert valor('SELECT id_partido FROM espectador WHERE id_espectador=%s',(asistencia,))==2
        entrada(personas.eliminar_espectador,[asistencia,'NO'],cursor)
        assert valor('SELECT COUNT(*) FROM espectador WHERE id_espectador=%s',(asistencia,))==1
        entrada(personas.eliminar_espectador,[asistencia,'SI'],cursor)
        assert valor('SELECT COUNT(*) FROM espectador WHERE id_espectador=%s',(asistencia,))==0
        ok('ABM de árbitros y asistencias con confirmaciones')

        cursor.execute("SELECT anio FROM torneo WHERE semestre='Primero'")
        usados={r[0] for r in cursor.fetchall()}
        anio=next(a for a in range(8000,8999) if a not in usados)
        torneo=torneos.crear_torneo(cursor,usuario,'Edición temporal',anio,'Primero',date(anio,1,1),date(anio,6,1))
        with patch.object(equipos,'conectar',return_value=proxy):
            _,salida=entrada(equipos.crear_equipo,[torneo,'Equipo temporal',1,50000001],usuario)
            assert 'Equipo creado correctamente' in salida,salida
            equipo=valor('SELECT id_equipo FROM equipo WHERE id_torneo=%s',(torneo,))
            _,salida=entrada(equipos.incorporar_jugador,[equipo,50000002],usuario)
            assert 'correctamente' in salida,salida
            _,salida=entrada(equipos.incorporar_jugador,[equipo,50000002],usuario)
            assert valor('SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=%s',(equipo,))==2
            _,salida=entrada(equipos.incorporar_jugador,[equipo,50000008],usuario)
            assert valor('SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=%s',(equipo,))==2
            entrada(equipos.cambiar_camiseta,[equipo,50000002,29],usuario)
            assert valor('SELECT numero_camiseta FROM equipo_jugador_torneo WHERE id_equipo=%s AND ci_jugador=50000002',(equipo,))==29
            entrada(equipos.modificar_equipo,[equipo,'Equipo cambiado',50000002],usuario)
            assert valor('SELECT ci_capitan FROM equipo WHERE id_equipo=%s',(equipo,))==50000002
            entrada(equipos.quitar_jugador,[equipo,50000002],usuario)
            assert valor('SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=%s',(equipo,))==2
            entrada(equipos.quitar_jugador,[equipo,50000001,'SI'],usuario)
            assert valor('SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=%s',(equipo,))==1
            _,salida=entrada(equipos.ver_plantel,[equipo],usuario)
            assert 'Equipo cambiado' in salida and '29' in salida,salida
            entrada(equipos.eliminar_equipo,[equipo,'NO'],usuario)
            assert valor('SELECT COUNT(*) FROM equipo WHERE id_equipo=%s',(equipo,))==1
            entrada(equipos.eliminar_equipo,[equipo,'SI'],usuario)
            assert valor('SELECT COUNT(*) FROM equipo WHERE id_equipo=%s',(equipo,))==0
            assert valor('SELECT COUNT(*) FROM jugador WHERE ci=50000002')==1
        ok('equipo completo: creación, plantel, duplicado, facultad, camiseta, capitán y baja')

        sancion=sanciones.crear_sancion(cursor,usuario,1,50000001,10000,2)
        sanciones.modificar_sancion(cursor,usuario,1,sancion,10001,3)
        assert valor('SELECT cantidad_fechas FROM sancion_jugador WHERE id_sancion=%s',(sancion,))==3
        falla(sanciones.crear_sancion,cursor,usuario,1,50000001,0,1)
        falla(sanciones.crear_sancion,cursor,usuario,1,50000001,1,1)
        automatico=valor("SELECT id_sancion FROM sancion_jugador WHERE motivo='roja' LIMIT 1")
        falla(sanciones.eliminar_sancion,cursor,usuario,1,automatico)
        sanciones.eliminar_sancion(cursor,usuario,1,sancion)
        assert valor('SELECT COUNT(*) FROM sancion_jugador WHERE id_sancion=%s',(sancion,))==0
        ok('ABM disciplinario y protección de sanciones automáticas y planillas existentes')

        clave='Temporal-'+uuid4().hex
        cursor.execute('INSERT INTO login (correo,password_hash,rol) VALUES (%s,%s,%s)',(correo,generate_password_hash(clave),'administrador'))
        with patch.object(app,'conectar',return_value=proxy):
            assert app.autenticar(correo,clave)['rol']=='administrador'
            assert app.autenticar(correo,'incorrecta') is None
            assert app.autenticar("' OR 1=1 --",clave) is None
        ok('autenticación real, contraseña incorrecta e intento de inyección SQL')

        for nombre,funcion in [('jugadores','menu_jugadores'),('equipos','menu_equipos'),('infraestructura','menu_infraestructura'),('personas_partido','menu_personas_partido'),('partidos','menu_partidos'),('sanciones','menu_sanciones'),('torneos','menu_torneos')]:
            modulo=importlib.import_module('src.'+nombre)
            with patch.object(modulo,'conectar') as conectar_mock,redirect_stdout(StringIO()):
                getattr(modulo,funcion)({'rol':'planillero'})
                conectar_mock.assert_not_called()
            with patch('builtins.input',side_effect=['invalida','0']),redirect_stdout(StringIO()):
                getattr(modulo,funcion)(usuario)
        ok('siete menús: rechazo de planillero, opción inválida y regreso')
        with patch.object(app,'registro'),patch.object(app,'autenticar',return_value={'rol':'planillero','correo':correo}),patch.object(app,'getpass',return_value=clave),patch.object(app,'menu_planillas') as menu,patch('builtins.input',side_effect=['1',correo,'0']),redirect_stdout(StringIO()):
            app.main()
            menu.assert_called_once()
        ok('login de planillero dirige al menú de planillas')
    finally:
        conexion.rollback()
        assert huella(cursor)==antes,'Los datos originales cambiaron.'
        cursor.close()
        conexion.close()
    print('INTEGRACIÓN OK:',len(comprobaciones),'grupos de recorridos. Todas las filas originales conservadas.')


if __name__ == '__main__':
    main()
