from getpass import getpass

import mysql.connector
from werkzeug.security import check_password_hash

from conexion import conectar
from jugadores import menu_jugadores
from reportes import menu_reportes


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
                    '0. Cerrar sesión'
                )
                opcion_admin = input('Elegí una opción: ').strip()
                if opcion_admin == '0':
                    break
                if opcion_admin == '1':
                    menu_jugadores(usuario)
                elif opcion_admin == '2':
                    menu_reportes()
                else:
                    print('Opción inválida.')
        else:
            print('El menú de planillas todavía está pendiente de implementar.')
            input('Presioná Enter para cerrar sesión...')


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nPrograma finalizado.")
