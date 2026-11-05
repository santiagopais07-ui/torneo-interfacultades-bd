from getpass import getpass
from src.equipos import menu_equipos
import mysql.connector
from werkzeug.security import check_password_hash

from src.conexion import conectar
from src.jugadores import menu_jugadores
from src.reportes import menu_reportes
from src.infraestructura import menu_infraestructura
from src.personas_partido import menu_personas_partido
from src.partidos import menu_partidos
from src.planillas import menu_planillas
from src.crear_usuarios import registro
from src.sanciones import menu_sanciones
from src.torneos import menu_torneos


def autenticar(correo, clave):
    conexion = conectar("administrador")

    try:
        cursor = conexion.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT correo, password_hash, rol
                FROM login
                WHERE correo = %s
                """,
                (correo,)
            )
            usuario = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conexion.close()

    if usuario is None:
        return None

    if usuario["rol"] not in ("administrador", "planillero"):
        return None

    if not check_password_hash(usuario["password_hash"], clave):
        return None

    return {
        "correo": usuario["correo"],
        "rol": usuario["rol"]
    }


def main():
    try:
        registro(mostrar_resumen=False)
    except mysql.connector.Error as error:
        print(f'No se pudieron preparar las cuentas iniciales (MySQL {error.errno}).')
        print('Revisá que MySQL esté disponible, el SQL inicial esté cargado y el .env sea correcto.')
        return
    except ValueError as error:
        print(error)
        return
    except KeyError:
        print('Falta completar la configuración de conexión en el archivo .env.')
        return

    while True:
        print("\nTORNEO INTERFACULTADES")
        print("1. Iniciar sesión")
        print("0. Salir")

        opcion = input("Elegí una opción: ").strip()

        if opcion == "0":
            print("Programa finalizado.")
            break

        if opcion != "1":
            print("Opción inválida. Elegí 1 o 0.")
            continue

        correo = input("Correo: ").strip()
        clave = getpass("Contraseña: ")

        if not correo or not clave:
            print("Tenés que completar el correo y la contraseña.")
            continue

        try:
            usuario = autenticar(correo, clave)
        except mysql.connector.Error:
            print("No se pudo consultar MySQL. Revisá la conexión.")
            continue

        if usuario is None:
            print("Correo o contraseña incorrectos.")
            continue

        print("\nInicio de sesión correcto.")
        print(f"Usuario: {usuario['correo']}")
        print(f"Rol: {usuario['rol']}")
        if usuario['rol'] == 'administrador':
            while True:
                print(
                    '\nADMINISTRADOR\n'
                    '1. Gestionar jugadores\n'
                    '2. Reportes\n'
                    '3. Gestionar equipos y planteles\n'
                    '4. Gestionar complejos y canchas\n'
                    '5. Gestionar arbitros y espectadores\n'
                    '6. Gestionar partidos\n'
                    '7. Registrar planillas, goles y tarjetas\n'
                    '8. Gestionar sanciones\n'
                    '9. Gestionar torneos\n'
                    '0. Cerrar sesión'
                )

                opcion_admin = input('Elegí una opción: ').strip()

                if opcion_admin == '0':
                    break
                elif opcion_admin == '1':
                    menu_jugadores(usuario)
                elif opcion_admin == '2':
                    menu_reportes()
                elif opcion_admin == '3':
                    menu_equipos(usuario)
                elif opcion_admin == '4':
                    menu_infraestructura(usuario)
                elif opcion_admin == '5':
                    menu_personas_partido(usuario)
                elif opcion_admin == '6':
                    menu_partidos(usuario)
                elif opcion_admin == '7':
                    menu_planillas(usuario)
                elif opcion_admin == '8':
                    menu_sanciones(usuario)
                elif opcion_admin == '9':
                    menu_torneos(usuario)
                else:
                    print('Opción inválida.')
        else:
            menu_planillas(usuario)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma finalizado.")
