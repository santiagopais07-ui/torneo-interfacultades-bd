import mysql.connector

from src.conexion import conectar
from src.jugadores import leer_entero, leer_texto
from src.reglas import validar_alta_plantel, validar_capitan_en_plantel
from src.reglas import validar_baja_jugador_plantel
from src.reglas import validar_torneo_en_inscripcion



def listar_equipos(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede gestionar equipos.")
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                e.id_equipo,
                e.nombre,
                f.nombre,
                t.nombre,
                t.estado,
                COUNT(p.ci_jugador)
            FROM equipo e
            JOIN facultad f
                ON f.id_facultad = e.id_facultad
            JOIN torneo t
                ON t.id_torneo = e.id_torneo
            LEFT JOIN equipo_jugador_torneo p
                ON p.id_equipo = e.id_equipo
                AND p.id_torneo = e.id_torneo
            GROUP BY
                e.id_equipo,
                e.nombre,
                f.nombre,
                t.nombre,
                t.estado
            ORDER BY e.id_equipo
        """)

        equipos = cursor.fetchall()

        if not equipos:
            print("No hay equipos registrados.")
            return

        print("\nID | Equipo | Facultad | Torneo | Estado | Jugadores")

        for equipo in equipos:
            print(" | ".join(str(dato) for dato in equipo))

    except mysql.connector.Error as error:
        print(
            f"No se pudieron consultar los equipos "
            f"(MySQL {error.errno})."
        )

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()

def crear_equipo(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede crear equipos.")
        return

    conexion = None
    cursor = None

    try:
        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_torneo, nombre
            FROM torneo
            WHERE estado = %s
            ORDER BY id_torneo
        """, ("inscripción",))

        torneos = cursor.fetchall()

        if not torneos:
            print("No hay torneos en inscripción.")
            print("Primero debemos crear una edición para inscribir equipos.")
            return

        print("\nTORNEOS EN INSCRIPCIÓN")

        for identificador, nombre in torneos:
            print(f"{identificador}. {nombre}")

        id_torneo = leer_entero("ID del torneo: ")

        # Bloqueamos el torneo para que su etapa no cambie durante el alta.
        cursor.execute("""
            SELECT estado
            FROM torneo
            WHERE id_torneo = %s
            FOR UPDATE
        """, (id_torneo,))

        torneo = cursor.fetchone()

        if torneo is None or torneo[0] != "inscripción":
            raise ValueError("Elegí un torneo que esté en inscripción.")

        nombre_equipo = leer_texto("Nombre del equipo: ")

        cursor.execute("""
            SELECT id_facultad, nombre
            FROM facultad
            ORDER BY id_facultad
        """)

        facultades = cursor.fetchall()

        for identificador, nombre in facultades:
            print(f"{identificador}. {nombre}")

        id_facultad = leer_entero("ID de facultad: ")

        if id_facultad not in [fila[0] for fila in facultades]:
            raise ValueError("La facultad no existe.")

        cursor.execute("""
            SELECT j.ci, j.nombre, j.apellido
            FROM jugador j
            WHERE j.id_facultad = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM equipo_jugador_torneo p
                  WHERE p.ci_jugador = j.ci
                    AND p.id_torneo = %s
              )
            ORDER BY j.apellido, j.nombre, j.ci
        """, (id_facultad, id_torneo))

        candidatos = cursor.fetchall()

        if not candidatos:
            raise ValueError(
                "No hay jugadores disponibles de esa facultad. "
                "Registrá primero un jugador."
            )

        print("\nJUGADORES DISPONIBLES PARA SER CAPITÁN")

        for ci, nombre, apellido in candidatos:
            print(f"{ci} | {nombre or ''} {apellido}")

        ci_capitan = leer_entero("CI del capitán: ")

        # Volvemos a comprobar los datos antes de guardar.
        cursor.execute("""
            SELECT id_facultad
            FROM jugador
            WHERE ci = %s
            FOR UPDATE
        """, (ci_capitan,))

        jugador = cursor.fetchone()

        if jugador is None or jugador[0] != id_facultad:
            raise ValueError("El capitán debe pertenecer a esa facultad.")

        cursor.execute("""
            SELECT id_equipo
            FROM equipo_jugador_torneo
            WHERE ci_jugador = %s AND id_torneo = %s
            FOR UPDATE
        """, (ci_capitan, id_torneo))

        if cursor.fetchone() is not None:
            raise ValueError(
                "El jugador ya integra un equipo de esta edición."
            )

        cursor.execute("""
            INSERT INTO equipo
                (nombre, id_torneo, id_facultad, ci_capitan)
            VALUES (%s, %s, %s, %s)
        """, (nombre_equipo, id_torneo, id_facultad, ci_capitan))

        id_equipo = cursor.lastrowid

        validar_alta_plantel(cursor, id_equipo, ci_capitan)

        cursor.execute("""
            INSERT INTO equipo_jugador_torneo
                (id_equipo, ci_jugador, id_torneo)
            VALUES (%s, %s, %s)
        """, (id_equipo, ci_capitan, id_torneo))

        validar_capitan_en_plantel(cursor, id_equipo)

        conexion.commit()

        print(f"Equipo creado correctamente. ID: {id_equipo}")
        print("El capitán quedó incluido como primer integrante.")
        print("Faltan al menos cuatro jugadores para completar el mínimo.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        print(f"No se pudo crear el equipo (MySQL {error.errno}).")

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()
def ver_plantel(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede gestionar planteles.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT nombre, ci_capitan
            FROM equipo
            WHERE id_equipo = %s
        """, (id_equipo,))

        equipo = cursor.fetchone()

        if equipo is None:
            raise ValueError("El equipo no existe.")

        nombre_equipo, ci_capitan = equipo

        cursor.execute("""
            SELECT
                j.ci,
                j.nombre,
                j.apellido,
                j.tipo,
                p.numero_camiseta
            FROM equipo_jugador_torneo p
            JOIN jugador j ON j.ci = p.ci_jugador
            WHERE p.id_equipo = %s
            ORDER BY j.apellido, j.nombre, j.ci
        """, (id_equipo,))

        jugadores = cursor.fetchall()

        print(f"\nPLANTEL DE {nombre_equipo}")
        print("CI | Nombre | Tipo | Camiseta | Capitán")

        for ci, nombre, apellido, tipo, camiseta in jugadores:
            es_capitan = "Sí" if ci == ci_capitan else "-"
            numero = camiseta if camiseta is not None else "-"
            nombre_completo = f"{nombre or ''} {apellido}".strip()

            print(
                f"{ci} | {nombre_completo} | "
                f"{tipo} | {numero} | {es_capitan}"
            )

        print(f"Total de integrantes: {len(jugadores)}")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        print(f"No se pudo consultar el plantel (MySQL {error.errno}).")

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()
def incorporar_jugador(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede incorporar jugadores.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo: ")
        ci_jugador = leer_entero("CI del jugador: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        # Estas reglas controlan inscripción, facultad y cupos.
        validar_alta_plantel(cursor, id_equipo, ci_jugador)

        cursor.execute("""
            SELECT id_torneo
            FROM equipo
            WHERE id_equipo = %s
        """, (id_equipo,))

        id_torneo = cursor.fetchone()[0]

        cursor.execute("""
            SELECT id_equipo
            FROM equipo_jugador_torneo
            WHERE ci_jugador = %s AND id_torneo = %s
        """, (ci_jugador, id_torneo))

        if cursor.fetchone() is not None:
            raise ValueError(
                "El jugador ya integra un equipo de esta edición."
            )

        cursor.execute("""
            INSERT INTO equipo_jugador_torneo
                (id_equipo, ci_jugador, id_torneo)
            VALUES (%s, %s, %s)
        """, (id_equipo, ci_jugador, id_torneo))

        conexion.commit()
        print("Jugador incorporado correctamente.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        if error.errno == 1062:
            print("El jugador ya está inscripto en esta edición.")
        else:
            print(
                f"No se pudo incorporar al jugador "
                f"(MySQL {error.errno})."
            )

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


def quitar_jugador(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede quitar jugadores.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo: ")
        ci_jugador = leer_entero("CI del jugador a quitar: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_equipo
            FROM equipo
            WHERE id_equipo = %s
            FOR UPDATE
        """, (id_equipo,))

        if cursor.fetchone() is None:
            raise ValueError("El equipo no existe.")

        # Controla que esté en inscripción y que no sea el capitán.
        validar_baja_jugador_plantel(cursor, id_equipo, ci_jugador)

        cursor.execute("""
            SELECT ci_jugador
            FROM equipo_jugador_torneo
            WHERE id_equipo = %s AND ci_jugador = %s
        """, (id_equipo, ci_jugador))

        if cursor.fetchone() is None:
            raise ValueError("El jugador no integra este equipo.")

        confirmacion = input(
            "¿Quitar al jugador del plantel? Escribí SI: "
        ).strip()

        if confirmacion != "SI":
            print("Operación cancelada.")
            return

        cursor.execute("""
            DELETE FROM equipo_jugador_torneo
            WHERE id_equipo = %s AND ci_jugador = %s
        """, (id_equipo, ci_jugador))

        conexion.commit()
        print("Jugador quitado del plantel. Su ficha se conserva.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        if error.errno == 1451:
            print(
                "No se puede quitar: tiene registros relacionados "
                "que deben conservarse."
            )
        else:
            print(
                f"No se pudo quitar al jugador "
                f"(MySQL {error.errno})."
            )

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


def modificar_equipo(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede modificar equipos.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT nombre, ci_capitan, id_torneo
            FROM equipo
            WHERE id_equipo = %s
            FOR UPDATE
        """, (id_equipo,))

        equipo = cursor.fetchone()

        if equipo is None:
            raise ValueError("El equipo no existe.")

        nombre_actual, capitan_actual, id_torneo = equipo

        cursor.execute("""
            SELECT estado
            FROM torneo
            WHERE id_torneo = %s
            FOR UPDATE
        """, (id_torneo,))

        estado = cursor.fetchone()[0]

        print(f"Nombre actual: {nombre_actual}")
        print(f"Estado del torneo: {estado}")

        nombre_nuevo = input(
            "Nuevo nombre (Enter para mantener): "
        ).strip()

        if not nombre_nuevo:
            nombre_nuevo = nombre_actual

        if len(nombre_nuevo) > 50:
            raise ValueError("El nombre admite hasta 50 caracteres.")

        ci_capitan = capitan_actual

        if estado == "inscripción":
            cursor.execute("""
                SELECT j.ci, j.nombre, j.apellido
                FROM equipo_jugador_torneo p
                JOIN jugador j ON j.ci = p.ci_jugador
                WHERE p.id_equipo = %s
                ORDER BY j.apellido, j.nombre, j.ci
            """, (id_equipo,))

            integrantes = cursor.fetchall()

            print("\nINTEGRANTES DEL PLANTEL")

            for ci, nombre, apellido in integrantes:
                marca = (
                    " (capitán actual)"
                    if ci == capitan_actual
                    else ""
                )
                print(f"{ci} | {nombre or ''} {apellido}{marca}")

            texto_capitan = input(
                "CI del nuevo capitán (Enter para mantener): "
            ).strip()

            if texto_capitan:
                if (
                    not texto_capitan.isascii()
                    or not texto_capitan.isdecimal()
                ):
                    raise ValueError("La CI debe contener solo números.")

                ci_capitan = int(texto_capitan)

            if ci_capitan not in [fila[0] for fila in integrantes]:
                raise ValueError("El capitán debe integrar el plantel.")

            validar_capitan_en_plantel(cursor, id_equipo)

            cursor.execute("""
                UPDATE equipo
                SET nombre = %s, ci_capitan = %s
                WHERE id_equipo = %s
            """, (nombre_nuevo, ci_capitan, id_equipo))

            validar_capitan_en_plantel(cursor, id_equipo)

        else:
            print(
                "Solo se modifica el nombre. "
                "El capitán se mantiene porque el torneo "
                "no está en inscripción."
            )

            cursor.execute("""
                UPDATE equipo
                SET nombre = %s
                WHERE id_equipo = %s
            """, (nombre_nuevo, id_equipo))

        conexion.commit()
        print("Equipo actualizado correctamente.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        print(f"No se pudo modificar el equipo (MySQL {error.errno}).")

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()

def cambiar_camiseta(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede cambiar camisetas.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo: ")
        ci_jugador = leer_entero("CI del jugador: ")
        numero = leer_entero("Número de camiseta: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id_equipo
            FROM equipo
            WHERE id_equipo = %s
            FOR UPDATE
        """, (id_equipo,))

        if cursor.fetchone() is None:
            raise ValueError("El equipo no existe.")

        validar_torneo_en_inscripcion(cursor, id_equipo)

        cursor.execute("""
            SELECT numero_camiseta
            FROM equipo_jugador_torneo
            WHERE id_equipo = %s AND ci_jugador = %s
        """, (id_equipo, ci_jugador))

        if cursor.fetchone() is None:
            raise ValueError("El jugador no integra este equipo.")

        cursor.execute("""
            UPDATE equipo_jugador_torneo
            SET numero_camiseta = %s
            WHERE id_equipo = %s AND ci_jugador = %s
        """, (numero, id_equipo, ci_jugador))

        conexion.commit()
        print("Número de camiseta actualizado correctamente.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        print(f"No se pudo cambiar la camiseta (MySQL {error.errno}).")

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


def eliminar_equipo(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede dar de baja equipos.")
        return

    conexion = None
    cursor = None

    try:
        id_equipo = leer_entero("ID del equipo a eliminar: ")

        conexion = conectar(usuario["rol"])
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT nombre, id_torneo
            FROM equipo
            WHERE id_equipo = %s
            FOR UPDATE
        """, (id_equipo,))

        equipo = cursor.fetchone()

        if equipo is None:
            raise ValueError("El equipo no existe.")

        nombre_equipo, id_torneo = equipo

        # Bloqueamos también el torneo durante la operación.
        cursor.execute("""
            SELECT estado
            FROM torneo
            WHERE id_torneo = %s
            FOR UPDATE
        """, (id_torneo,))

        torneo = cursor.fetchone()

        if torneo is None:
            raise ValueError("El torneo no existe.")

        validar_torneo_en_inscripcion(cursor, id_equipo)

        cursor.execute("""
            SELECT id_partido
            FROM partido
            WHERE id_equipo_local = %s
               OR id_equipo_visitante = %s
        """, (id_equipo, id_equipo))

        partidos = cursor.fetchall()

        if partidos:
            raise ValueError(
                "No se puede eliminar: el equipo tiene partidos "
                "registrados, incluso si están cancelados."
            )

        print(f"Equipo: {nombre_equipo}")
        print("Se eliminarán el equipo y sus inscripciones al plantel.")
        print("Las fichas de los jugadores se conservarán.")

        confirmacion = input(
            "Escribí SI para confirmar la baja: "
        ).strip()

        if confirmacion != "SI":
            print("Operación cancelada.")
            return

        cursor.execute("""
            DELETE FROM equipo_jugador_torneo
            WHERE id_equipo = %s AND id_torneo = %s
        """, (id_equipo, id_torneo))

        cursor.execute("""
            DELETE FROM equipo
            WHERE id_equipo = %s
        """, (id_equipo,))

        conexion.commit()
        print("Equipo eliminado correctamente.")

    except ValueError as error:
        print(error)

    except mysql.connector.Error as error:
        if error.errno == 1451:
            print(
                "No se puede eliminar: hay registros relacionados. "
                "Se conservaron el equipo y su plantel."
            )
        else:
            print(
                f"No se pudo eliminar el equipo "
                f"(MySQL {error.errno})."
            )

    finally:
        if conexion is not None:
            conexion.rollback()

        if cursor is not None:
            cursor.close()

        if conexion is not None:
            conexion.close()


def menu_equipos(usuario):
    if usuario.get("rol") != "administrador":
        print("Solo el administrador puede gestionar equipos.")
        return

    while True:
        print("\nEQUIPOS Y PLANTELES")
        print("1. Listar equipos")
        print("2. Crear equipo")
        print("3. Ver plantel")
        print("4. Incorporar jugador")
        print("5. Quitar jugador")
        print("6. Modificar equipo y capitán")
        print("7. Asignar o cambiar camiseta")
        print("8. Dar de baja equipo")
        print("0. Volver")

        opcion = input("Elegí una opción: ").strip()

        if opcion == "0":
            return
        elif opcion == "1":
            listar_equipos(usuario)
        elif opcion == "2":
            crear_equipo(usuario)
        elif opcion == "3":
            ver_plantel(usuario)
        elif opcion == "4":
            incorporar_jugador(usuario)
        elif opcion == "5":
            quitar_jugador(usuario)
        elif opcion == "6":
            modificar_equipo(usuario)
        elif opcion == "7":
            cambiar_camiseta(usuario)
        elif opcion == "8":
            eliminar_equipo(usuario)
        else:
            print("Opción inválida.")