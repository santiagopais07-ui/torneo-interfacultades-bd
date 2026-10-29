from getpass import getpass

from werkzeug.security import generate_password_hash

from conexion import conectar


def main():
    usuarios = [
        ("admin@correo.ucu.edu.uy", "administrador"),
        ("planillero@correo.ucu.edu.uy", "planillero")
    ]

    conexion = conectar("administrador")
    cursor = conexion.cursor()

    try:
        for correo, rol in usuarios:
            cursor.execute(
                "SELECT correo FROM login WHERE correo = %s",
                (correo,)
            )

            if cursor.fetchone() is not None:
                print(f"El usuario {correo} ya existe. No se modificó.")
                continue

            print(f"\nCrear usuario: {correo} ({rol})")

            while True:
                clave = getpass(
                    "Elegí una contraseña de al menos 8 caracteres: "
                )
                confirmacion = getpass("Repetí la contraseña: ")

                if len(clave) < 8:
                    print("La contraseña debe tener al menos 8 caracteres.")
                elif clave != confirmacion:
                    print("Las contraseñas no coinciden.")
                else:
                    break

            hash_clave = generate_password_hash(clave)

            cursor.execute(
                """
                INSERT INTO login (correo, password_hash, rol)
                VALUES (%s, %s, %s)
                """,
                (correo, hash_clave, rol)
            )

        conexion.commit()
        print("\nPreparación de usuarios finalizada.")

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    main()