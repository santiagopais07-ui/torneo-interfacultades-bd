import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))


def conectar(rol):
    if rol == "administrador":
        prefijo = "DB_ADMIN"
    elif rol == "planillero":
        prefijo = "DB_PLANILLERO"
    else:
        raise ValueError("Rol no válido")

    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
        user=os.environ[f"{prefijo}_USER"],
        password=os.environ[f"{prefijo}_PASSWORD"],
        charset="utf8mb4",
        connection_timeout=5
    )


if __name__ == "__main__":
    for rol in ("administrador", "planillero"):
        conexion = conectar(rol)

        try:
            cursor = conexion.cursor()

            try:
                cursor.execute("SELECT DATABASE(), CURRENT_USER()")
                base, usuario = cursor.fetchone()

                print(f"{rol}: conexión correcta")
                print(f"Base: {base} | Usuario MySQL: {usuario}")
            finally:
                cursor.close()
        finally:
            conexion.close()