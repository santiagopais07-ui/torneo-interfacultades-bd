"""Creación de ediciones y avance de etapas, sin ORM."""
from datetime import date
import mysql.connector
from src.conexion import conectar
from src.jugadores import leer_entero, leer_texto
from src.reglas import validar_cambio_etapa


def exigir_administrador(usuario):
    if usuario.get('rol') != 'administrador':
        raise ValueError('Solo el administrador puede gestionar torneos.')


def listar_torneos(cursor):
    cursor.execute("""SELECT id_torneo,nombre,anio,semestre,fecha_inicio,fecha_fin,estado
                      FROM torneo ORDER BY anio,semestre,id_torneo""")
    filas = cursor.fetchall()
    print('ID | Nombre | Año | Semestre | Inicio | Fin | Estado')
    for fila in filas:
        print(' | '.join('-' if v is None else str(v) for v in fila))
    if not filas:
        print('Todavía no hay ediciones.')


def crear_torneo(cursor, usuario, nombre, anio, semestre, inicio, fin):
    exigir_administrador(usuario)
    nombre = nombre.strip()
    if not nombre or len(nombre) > 50:
        raise ValueError('El nombre es obligatorio y admite hasta 50 caracteres.')
    if type(anio) is not int or not 1 <= anio <= 9999:
        raise ValueError('El año debe estar entre 1 y 9999.')
    if semestre not in ('Primero', 'Segundo'):
        raise ValueError('El semestre debe ser Primero o Segundo.')
    if type(inicio) is not date or type(fin) is not date or fin < inicio:
        raise ValueError('Las fechas deben ser válidas y el fin no puede ser anterior al inicio.')
    cursor.execute('SELECT id_torneo FROM torneo WHERE anio=%s AND semestre=%s', (anio, semestre))
    if cursor.fetchone() is not None:
        raise ValueError('Ya existe una edición para ese año y semestre.')
    cursor.execute("""INSERT INTO torneo
        (nombre,anio,semestre,fecha_inicio,fecha_fin,estado)
        VALUES (%s,%s,%s,%s,%s,%s)""", (nombre, anio, semestre, inicio, fin, 'inscripción'))
    return cursor.lastrowid


def cambiar_etapa(cursor, usuario, id_torneo, nuevo_estado):
    exigir_administrador(usuario)
    cursor.execute('SELECT GET_LOCK(CONCAT(DATABASE(), %s, %s), 5)', (':registro:', id_torneo))
    if cursor.fetchone()[0] != 1:
        raise ValueError('Otra carga está usando esta edición. Intentá nuevamente.')
    cursor.execute('SELECT estado FROM torneo WHERE id_torneo=%s FOR UPDATE', (id_torneo,))
    if cursor.fetchone() is None:
        raise ValueError('No existe esa edición.')
    # Reutiliza las transiciones y el mínimo de cinco jugadores de reglas.py.
    validar_cambio_etapa(cursor, id_torneo, nuevo_estado)
    if nuevo_estado == 'en curso':
        cursor.execute('SELECT COUNT(*) FROM equipo WHERE id_torneo=%s', (id_torneo,))
        if cursor.fetchone()[0] < 2:
            raise ValueError('Se necesitan al menos dos equipos para iniciar la edición.')
    if nuevo_estado == 'finalizado':
        cursor.execute("SELECT COUNT(*) FROM partido WHERE id_torneo=%s AND estado IN ('programado','postergado')", (id_torneo,))
        if cursor.fetchone()[0]:
            raise ValueError('Quedan partidos programados o postergados. Resolvelos antes de finalizar.')
    cursor.execute('UPDATE torneo SET estado=%s WHERE id_torneo=%s', (nuevo_estado, id_torneo))


def leer_fecha(mensaje):
    texto = input(mensaje).strip()
    try:
        valor = date.fromisoformat(texto)
    except ValueError:
        raise ValueError('Ingresá una fecha válida con formato AAAA-MM-DD.') from None
    if valor.isoformat() != texto:
        raise ValueError('Usá el formato AAAA-MM-DD.')
    return valor


def menu_torneos(usuario):
    try:
        exigir_administrador(usuario)
    except ValueError as error:
        print(error)
        return
    while True:
        print('\nTORNEOS\n1. Listar ediciones\n2. Crear edición\n3. Cambiar etapa\n0. Volver')
        opcion = input('Elegí una opción: ').strip()
        if opcion == '0':
            return
        if opcion not in ('1','2','3'):
            print('Opción inválida.')
            continue
        conexion = None
        cursor = None
        try:
            conexion = conectar('administrador')
            conexion.start_transaction(isolation_level='READ COMMITTED')
            cursor = conexion.cursor()
            if opcion == '1':
                listar_torneos(cursor)
                continue
            if opcion == '2':
                nombre = leer_texto('Nombre: ')
                anio = leer_entero('Año: ')
                semestre = input('Semestre (1: Primero, 2: Segundo): ').strip()
                if semestre not in ('1','2'):
                    raise ValueError('Elegí 1 o 2.')
                inicio = leer_fecha('Fecha de inicio (AAAA-MM-DD): ')
                fin = leer_fecha('Fecha de fin (AAAA-MM-DD): ')
                identificador = crear_torneo(cursor,usuario,nombre,anio,{'1':'Primero','2':'Segundo'}[semestre],inicio,fin)
                conexion.commit()
                print(f'Edición creada en inscripción. ID: {identificador}')
            else:
                listar_torneos(cursor)
                identificador = leer_entero('ID de la edición: ')
                cursor.execute('SELECT estado FROM torneo WHERE id_torneo=%s', (identificador,))
                fila = cursor.fetchone()
                if fila is None:
                    raise ValueError('No existe esa edición.')
                siguiente = {'inscripción':'en curso','en curso':'finalizado'}.get(fila[0])
                if siguiente is None:
                    raise ValueError('La edición ya está finalizada.')
                print(f'Etapa actual: {fila[0]}. Nueva etapa: {siguiente}.')
                if input('Escribí SI para confirmar: ').strip().upper() != 'SI':
                    print('Operación cancelada.')
                    continue
                cambiar_etapa(cursor,usuario,identificador,siguiente)
                conexion.commit()
                print('Etapa actualizada correctamente.')
        except ValueError as error:
            print(error)
        except mysql.connector.Error as error:
            if error.errno == 1062:
                print('Ya existe una edición para ese año y semestre.')
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
