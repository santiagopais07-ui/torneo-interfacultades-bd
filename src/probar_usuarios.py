"""Verifica la preparación inicial sin modificar las cuentas reales."""
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from werkzeug.security import check_password_hash

from src.conexion import conectar
from src.crear_usuarios import crear_usuarios_faltantes, registro, USUARIOS_INICIALES
from src.main import main


def ejecutar_pruebas():
    conexion=conectar('administrador'); cursor=conexion.cursor()
    identificador=uuid4().hex[:12]
    temporales=((f'prueba.admin.{identificador}@example.com','administrador'),
                (f'prueba.plan.{identificador}@example.com','planillero'))
    try:
        cursor.execute('SELECT correo,password_hash,rol FROM login ORDER BY correo')
        cuentas_antes=cursor.fetchall()
        conexion.rollback()
        conexion.start_transaction()
        with patch('src.crear_usuarios.USUARIOS_INICIALES',temporales):
            respuestas=['corta','corta','ClaveTemporal123','NoCoincide456',
                        'ClaveTemporal123','ClaveTemporal123','ClaveSegunda456','ClaveSegunda456']
            with patch('src.crear_usuarios.getpass',side_effect=respuestas),redirect_stdout(StringIO()):
                creados=crear_usuarios_faltantes(cursor)
            assert creados==[fila[0] for fila in temporales]
            print('OK: crea administrador y planillero cuando faltan, valida longitud y confirmación')
            cursor.execute('SELECT password_hash,rol FROM login WHERE correo=%s',(temporales[0][0],))
            hash_admin,rol=cursor.fetchone()
            assert rol=='administrador' and hash_admin!='ClaveTemporal123'
            assert check_password_hash(hash_admin,'ClaveTemporal123')
            cursor.execute('SELECT password_hash,rol FROM login WHERE correo=%s',(temporales[1][0],))
            hash_plan,rol=cursor.fetchone()
            assert rol=='planillero' and check_password_hash(hash_plan,'ClaveSegunda456')
            print('OK: guarda hashes válidos y asigna el rol correcto')
            with patch('src.crear_usuarios.getpass') as pedir:
                assert crear_usuarios_faltantes(cursor)==[]
                pedir.assert_not_called()
            cursor.execute('SELECT password_hash FROM login WHERE correo=%s',(temporales[0][0],))
            assert cursor.fetchone()[0]==hash_admin
            print('OK: no pide contraseñas ni cambia el hash de las cuentas existentes')
            cursor.execute('UPDATE login SET correo=%s WHERE correo=%s',(f'otro.{identificador}@example.com',temporales[1][0]))
            with patch('src.crear_usuarios.getpass',side_effect=['NuevaTemporal456','NuevaTemporal456']),redirect_stdout(StringIO()):
                assert crear_usuarios_faltantes(cursor)==[temporales[1][0]]
            cursor.execute('SELECT password_hash FROM login WHERE correo=%s',(temporales[0][0],))
            assert cursor.fetchone()[0]==hash_admin
            print('OK: si falta solo una cuenta, crea únicamente esa cuenta')
            cursor.execute('UPDATE login SET rol=%s WHERE correo=%s',('planillero',temporales[0][0]))
            with patch('src.crear_usuarios.getpass') as pedir:
                try:
                    crear_usuarios_faltantes(cursor)
                    raise AssertionError('Debía rechazar un rol distinto para la cuenta inicial')
                except ValueError as error:
                    assert 'rol distinto' in str(error)
                pedir.assert_not_called()
            print('OK: informa un rol incompatible sin sobrescribir el registro')
    finally:
        conexion.rollback();cursor.close();conexion.close()
    conexion=conectar('administrador');cursor=conexion.cursor()
    try:
        cursor.execute('SELECT correo,password_hash,rol FROM login ORDER BY correo')
        assert cursor.fetchall()==cuentas_antes
        assert all(any(fila[0]==correo for fila in cuentas_antes) for correo,_ in USUARIOS_INICIALES), 'Faltan cuentas reales: probá la creación interactiva desde la consola.'
    finally:
        cursor.close();conexion.close()
    with patch('src.crear_usuarios.getpass') as pedir,redirect_stdout(StringIO()):
        assert registro(mostrar_resumen=False)==[]
        pedir.assert_not_called()
    print('OK: arranque con las cuentas reales existentes no requiere claves nuevas')
    salida=StringIO()
    with patch('builtins.input',side_effect=['0']),redirect_stdout(salida):
        main()
    assert 'TORNEO INTERFACULTADES' in salida.getvalue() and 'Programa finalizado.' in salida.getvalue()
    print('OK: la consola prepara usuarios antes de mostrar el menú')
    print('Cuentas reales conservadas. Datos temporales revertidos.')


if __name__=='__main__':
    ejecutar_pruebas()
