from datetime import datetime

from conexion import conectar
from reglas import (
    validar_alta_plantel,
    validar_alta_partido,
    validar_alta_planilla,
    validar_baja_partido,
    validar_baja_jugador_plantel,
    validar_cambio_etapa,
    validar_capitan_en_plantel,
    validar_equipo_del_partido,
    validar_max_docentes_funcionarios,
    validar_max_plantel,
    validar_min_jugadores,
    validar_misma_facultad,
    validar_jugador_no_suspendido,
    validar_partido_disputado,
    validar_partido_registrable,
    validar_rival_no_repetido,
    validar_sancion_disciplinaria,
    validar_torneo_en_inscripcion,
    validar_un_partido_por_fecha,
    validar_ventana_correccion,
    registrar_cambio,
    recalcular_sanciones_automaticas,
)


def probar_pasa(descripcion, funcion, *argumentos):
    funcion(*argumentos)
    print(f"OK: {descripcion}")


def probar_falla(descripcion, mensaje_esperado, funcion, *argumentos):
    try:
        funcion(*argumentos)
    except ValueError as error:
        if mensaje_esperado not in str(error):
            raise AssertionError(
                f"{descripcion}: mensaje inesperado: {error}"
            ) from error
        print(f"OK: {descripcion}")
    else:
        raise AssertionError(f"{descripcion}: se esperaba un ValueError")


def leer_sanciones(cursor, ci_jugador, id_torneo, motivo):
    cursor.execute(
        """
        SELECT sancion_jugador.motivo,
               sancion_jugador.numero_fecha_inicio,
               sancion_jugador.cantidad_fechas
        FROM sancion_jugador
        WHERE sancion_jugador.ci_jugador = %s
          AND sancion_jugador.id_torneo = %s
          AND sancion_jugador.motivo = %s
        ORDER BY sancion_jugador.numero_fecha_inicio
        """,
        (ci_jugador, id_torneo, motivo),
    )
    sanciones = []
    sancion = cursor.fetchone()
    while sancion is not None:
        sanciones.append(sancion)
        sancion = cursor.fetchone()
    return sanciones


def ejecutar_pruebas(cursor):
    cursor.execute(
        "SELECT id_equipo FROM equipo WHERE nombre = %s",
        ("Empresariales FC",),
    )
    equipo = cursor.fetchone()
    if equipo is None:
        raise RuntimeError("No se encontró el equipo de prueba Empresariales FC")
    id_equipo = equipo[0]

    cursor.execute(
        "SELECT id_torneo FROM equipo WHERE id_equipo = %s",
        (id_equipo,),
    )
    torneo = cursor.fetchone()
    if torneo is None:
        raise RuntimeError(f"No se encontró el torneo del equipo {id_equipo}")
    id_torneo = torneo[0]

    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("inscripción", id_torneo),
    )
    probar_pasa(
        "transición de inscripción a en curso",
        validar_cambio_etapa,
        cursor,
        id_torneo,
        "en curso",
    )
    probar_falla(
        "no se puede saltar a finalizado",
        "No se puede cambiar",
        validar_cambio_etapa,
        cursor,
        id_torneo,
        "finalizado",
    )
    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("en curso", id_torneo),
    )
    probar_pasa(
        "transición de en curso a finalizado",
        validar_cambio_etapa,
        cursor,
        id_torneo,
        "finalizado",
    )
    probar_falla(
        "no se puede volver a inscripción",
        "No se puede cambiar",
        validar_cambio_etapa,
        cursor,
        id_torneo,
        "inscripción",
    )
    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("inscripción", id_torneo),
    )

    probar_pasa(
        "administrador registra sanción disciplinaria",
        validar_sancion_disciplinaria,
        cursor,
        "disciplinaria",
        "administrador",
    )
    probar_falla(
        "planillero no registra sanción disciplinaria",
        "Solo un administrador",
        validar_sancion_disciplinaria,
        cursor,
        "disciplinaria",
        "planillero",
    )
    probar_pasa(
        "planillero registra sanción automática",
        validar_sancion_disciplinaria,
        cursor,
        "roja",
        "planillero",
    )

    ahora_despues_del_partido = datetime(2026, 10, 7, 19, 0)
    probar_pasa(
        "partido cuya hora de fin ya pasó",
        validar_partido_disputado,
        cursor,
        1,
        ahora_despues_del_partido,
    )
    probar_falla(
        "partido cuya hora de fin todavía no pasó",
        "todavía no se ha disputado",
        validar_partido_disputado,
        cursor,
        10,
        datetime(2026, 10, 27, 18, 30),
    )
    probar_falla(
        "partido inexistente",
        "No existe un partido",
        validar_partido_disputado,
        cursor,
        999999,
        ahora_despues_del_partido,
    )

    probar_pasa(
        "corrección dentro de las 48 horas",
        validar_ventana_correccion,
        cursor,
        1,
        datetime(2026, 10, 8, 18, 59),
    )
    probar_falla(
        "corrección después de las 48 horas",
        "más de 48 horas",
        validar_ventana_correccion,
        cursor,
        1,
        datetime(2026, 10, 8, 19, 1),
    )
    probar_pasa(
        "partido no jugado sin ventana de corrección",
        validar_ventana_correccion,
        cursor,
        10,
        datetime(2027, 1, 1, 0, 0),
    )

    probar_pasa(
        "partido jugado registrable dentro de la ventana",
        validar_partido_registrable,
        cursor,
        1,
        ahora_despues_del_partido,
    )
    probar_falla(
        "partido cancelado no registrable",
        "no es registrable",
        validar_partido_registrable,
        cursor,
        12,
        datetime(2026, 10, 30, 12, 0),
    )
    probar_falla(
        "partido postergado no registrable",
        "no es registrable",
        validar_partido_registrable,
        cursor,
        11,
        datetime(2026, 10, 30, 12, 0),
    )
    probar_falla(
        "partido jugado fuera de la ventana no registrable",
        "más de 48 horas",
        validar_partido_registrable,
        cursor,
        1,
        datetime(2026, 10, 8, 19, 1),
    )

    probar_pasa(
        "equipo local participante",
        validar_equipo_del_partido,
        cursor,
        1,
        1,
    )
    probar_falla(
        "equipo que no participa",
        "no participa",
        validar_equipo_del_partido,
        cursor,
        1,
        2,
    )

    probar_pasa(
        "jugador no suspendido en la fecha",
        validar_jugador_no_suspendido,
        cursor,
        7,
        50000001,
    )
    probar_falla(
        "jugador suspendido por sanción automática",
        "está suspendido",
        validar_jugador_no_suspendido,
        cursor,
        7,
        50000014,
    )
    probar_falla(
        "jugador suspendido por sanción disciplinaria",
        "está suspendido",
        validar_jugador_no_suspendido,
        cursor,
        10,
        50000021,
    )

    probar_pasa(
        "alta de planilla válida",
        validar_alta_planilla,
        cursor,
        1,
        50000001,
        1,
        ahora_despues_del_partido,
    )
    probar_falla(
        "alta de planilla con equipo ajeno",
        "no participa",
        validar_alta_planilla,
        cursor,
        1,
        50000001,
        2,
        ahora_despues_del_partido,
    )
    probar_falla(
        "alta de planilla con jugador suspendido",
        "está suspendido",
        validar_alta_planilla,
        cursor,
        7,
        50000014,
        1,
        datetime(2026, 10, 21, 12, 0),
    )

    probar_pasa(
        "partido no jugado que se puede cancelar",
        validar_baja_partido,
        cursor,
        10,
    )
    probar_falla(
        "partido jugado que no se puede cancelar",
        "No se puede cancelar",
        validar_baja_partido,
        cursor,
        1,
    )

    correo = "prueba.reglas@correo.ucu.edu.uy"
    cursor.execute(
        "INSERT INTO login (correo, password_hash, rol) VALUES (%s, %s, %s)",
        (correo, "hash-de-prueba", "planillero"),
    )
    registrar_cambio(cursor, 1, correo, "x" * 120)
    cursor.execute(
        """
        SELECT cambios.descripcion_cambio
        FROM cambios
        WHERE cambios.id_partido = %s
          AND cambios.correo_cambiante = %s
        ORDER BY cambios.id_cambio DESC
        LIMIT 1
        """,
        (1, correo),
    )
    cambio = cursor.fetchone()
    if cambio is None or len(cambio[0]) != 100:
        raise AssertionError("El cambio no se registró con 100 caracteres")
    print("OK: descripción de cambio limitada a 100 caracteres")

    recalcular_sanciones_automaticas(cursor, 50000014, id_torneo)
    sanciones_roja = leer_sanciones(cursor, 50000014, id_torneo, "roja")
    if sanciones_roja != [("roja", 3, 1)]:
        raise AssertionError(
            f"Sanciones rojas inesperadas para 50000014: {sanciones_roja}"
        )
    print("OK: recálculo de roja para 50000014")

    recalcular_sanciones_automaticas(cursor, 50000031, id_torneo)
    sanciones_amarillas = leer_sanciones(
        cursor,
        50000031,
        id_torneo,
        "acumulación de amarillas",
    )
    if sanciones_amarillas != [("acumulación de amarillas", 4, 1)]:
        raise AssertionError(
            "Sanciones por amarillas inesperadas para 50000031: "
            f"{sanciones_amarillas}"
        )
    print("OK: recálculo de amarillas para 50000031")

    recalcular_sanciones_automaticas(cursor, 50000021, id_torneo)
    sanciones_disciplinarias = leer_sanciones(
        cursor,
        50000021,
        id_torneo,
        "disciplinaria",
    )
    if sanciones_disciplinarias != [("disciplinaria", 3, 2)]:
        raise AssertionError(
            "La sanción disciplinaria de 50000021 no se preservó: "
            f"{sanciones_disciplinarias}"
        )
    print("OK: sanción disciplinaria preservada")

    cursor.execute(
        """
        SELECT tarjeta.id_tarjeta
        FROM tarjeta
        WHERE tarjeta.id_partido = %s
          AND tarjeta.ci_jugador = %s
          AND tarjeta.color = %s
        """,
        (9, 50000031, "amarilla"),
    )
    tarjeta_amarilla = cursor.fetchone()
    if tarjeta_amarilla is None:
        raise RuntimeError("No se encontró la amarilla de 50000031 en partido 9")
    cursor.execute(
        "DELETE FROM tarjeta WHERE tarjeta.id_tarjeta = %s",
        (tarjeta_amarilla[0],),
    )
    recalcular_sanciones_automaticas(cursor, 50000031, id_torneo)
    sanciones_amarillas = leer_sanciones(
        cursor,
        50000031,
        id_torneo,
        "acumulación de amarillas",
    )
    if sanciones_amarillas:
        raise AssertionError(
            "La sanción por amarillas de 50000031 debería desaparecer: "
            f"{sanciones_amarillas}"
        )
    print("OK: sanción por amarillas eliminada tras borrar tarjeta")

    probar_pasa(
        "rival que todavía no se enfrentó",
        validar_rival_no_repetido,
        cursor,
        id_torneo,
        1,
        2,
    )
    probar_falla(
        "rival repetido aunque cambie localía",
        "ya se enfrentaron",
        validar_rival_no_repetido,
        cursor,
        id_torneo,
        6,
        1,
    )
    probar_pasa(
        "partido excluido al modificarlo",
        validar_rival_no_repetido,
        cursor,
        id_torneo,
        6,
        1,
        1,
    )

    probar_pasa(
        "equipo sin partido en la fecha",
        validar_un_partido_por_fecha,
        cursor,
        id_torneo,
        5,
        1,
    )
    probar_falla(
        "partido cancelado también ocupa fecha",
        "ya tiene un partido",
        validar_un_partido_por_fecha,
        cursor,
        id_torneo,
        4,
        5,
    )
    probar_pasa(
        "partido excluido de la fecha al modificarlo",
        validar_un_partido_por_fecha,
        cursor,
        id_torneo,
        4,
        1,
        10,
    )
    probar_pasa(
        "alta de partido válida",
        validar_alta_partido,
        cursor,
        id_torneo,
        5,
        1,
        2,
    )
    probar_falla(
        "alta de partido en fecha ocupada",
        "ya tiene un partido",
        validar_alta_partido,
        cursor,
        id_torneo,
        4,
        1,
        2,
    )

    cursor.execute("SELECT COALESCE(MAX(ci), 0) + 1 FROM jugador")
    siguiente_ci_chico = cursor.fetchone()[0]
    cis_equipo_chico = []
    for numero in range(4):
        ci = siguiente_ci_chico + numero
        cis_equipo_chico.append(ci)
        cursor.execute(
            """
            INSERT INTO jugador
                (ci, nombre, apellido, email, id_facultad, tipo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                ci,
                "Prueba",
                f"Plantel {numero + 1}",
                f"prueba.plantel.{ci}@correo.ucu.edu.uy",
                1,
                "grado",
            ),
        )

    cursor.execute(
        """
        INSERT INTO equipo (nombre, id_torneo, id_facultad, ci_capitan)
        VALUES (%s, %s, %s, %s)
        """,
        ("Equipo prueba plantel mínimo", id_torneo, 1, cis_equipo_chico[0]),
    )
    id_equipo_chico = cursor.lastrowid
    for numero, ci in enumerate(cis_equipo_chico):
        cursor.execute(
            """
            INSERT INTO equipo_jugador_torneo
                (id_equipo, ci_jugador, id_torneo, numero_camiseta)
            VALUES (%s, %s, %s, %s)
            """,
            (id_equipo_chico, ci, id_torneo, numero + 1),
        )

    probar_pasa(
        "plantel con al menos cinco jugadores",
        validar_min_jugadores,
        cursor,
        id_equipo,
    )
    probar_falla(
        "plantel con menos de cinco jugadores",
        "al menos 5 jugadores",
        validar_min_jugadores,
        cursor,
        id_equipo_chico,
    )
    probar_pasa(
        "capitán incluido en el plantel",
        validar_capitan_en_plantel,
        cursor,
        id_equipo_chico,
    )
    cursor.execute(
        """
        DELETE FROM equipo_jugador_torneo
        WHERE id_equipo = %s AND ci_jugador = %s
        """,
        (id_equipo_chico, cis_equipo_chico[0]),
    )
    probar_falla(
        "capitán ausente del plantel",
        "no está en el plantel",
        validar_capitan_en_plantel,
        cursor,
        id_equipo_chico,
    )
    cursor.execute(
        """
        INSERT INTO equipo_jugador_torneo
            (id_equipo, ci_jugador, id_torneo, numero_camiseta)
        VALUES (%s, %s, %s, %s)
        """,
        (id_equipo_chico, cis_equipo_chico[0], id_torneo, 1),
    )
    probar_falla(
        "no se puede iniciar torneo con plantel menor a cinco",
        "al menos 5 jugadores",
        validar_cambio_etapa,
        cursor,
        id_torneo,
        "en curso",
    )
    probar_falla(
        "alta de partido con equipo de menos de cinco jugadores",
        "al menos 5 jugadores",
        validar_alta_partido,
        cursor,
        id_torneo,
        5,
        id_equipo_chico,
        2,
    )

    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("inscripción", id_torneo),
    )
    probar_pasa(
        "torneo en inscripción",
        validar_torneo_en_inscripcion,
        cursor,
        id_equipo,
    )

    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("en curso", id_torneo),
    )
    probar_falla(
        "torneo fuera de inscripción",
        "no está en inscripción",
        validar_torneo_en_inscripcion,
        cursor,
        id_equipo,
    )
    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("inscripción", id_torneo),
    )

    probar_pasa(
        "baja de jugador no capitán durante inscripción",
        validar_baja_jugador_plantel,
        cursor,
        id_equipo,
        50000002,
    )
    probar_falla(
        "no se puede dar de baja al capitán",
        "No se puede dar de baja al capitán",
        validar_baja_jugador_plantel,
        cursor,
        id_equipo,
        50000001,
    )
    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("en curso", id_torneo),
    )
    probar_falla(
        "no se puede dar de baja fuera de inscripción",
        "no está en inscripción",
        validar_baja_jugador_plantel,
        cursor,
        id_equipo,
        50000002,
    )
    cursor.execute(
        "UPDATE torneo SET estado = %s WHERE id_torneo = %s",
        ("inscripción", id_torneo),
    )

    probar_pasa(
        "jugador de la misma facultad",
        validar_misma_facultad,
        cursor,
        id_equipo,
        50000002,
    )
    probar_falla(
        "jugador de otra facultad",
        "facultades distintas",
        validar_misma_facultad,
        cursor,
        id_equipo,
        50000008,
    )

    probar_pasa(
        "alta de jugador válida",
        validar_alta_plantel,
        cursor,
        id_equipo,
        50000003,
    )
    probar_falla(
        "alta de jugador de otra facultad",
        "facultades distintas",
        validar_alta_plantel,
        cursor,
        id_equipo,
        50000008,
    )

    probar_pasa(
        "menos de dos docentes o funcionarios",
        validar_max_docentes_funcionarios,
        cursor,
        id_equipo,
        10000001,
    )
    cursor.execute(
        "UPDATE jugador SET tipo = %s WHERE ci = %s",
        ("docente", 50000002),
    )
    probar_falla(
        "dos docentes o funcionarios",
        "máximo de 2 docentes o funcionarios",
        validar_max_docentes_funcionarios,
        cursor,
        id_equipo,
        10000001,
    )

    probar_pasa(
        "plantel con menos de diez jugadores",
        validar_max_plantel,
        cursor,
        id_equipo,
    )
    cursor.execute("SELECT COALESCE(MAX(ci), 0) + 1 FROM jugador")
    siguiente_ci = cursor.fetchone()[0]
    for numero in range(3):
        ci = siguiente_ci + numero
        cursor.execute(
            """
            INSERT INTO jugador
                (ci, nombre, apellido, email, id_facultad, tipo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                ci,
                "Prueba",
                f"Regla {numero + 1}",
                f"prueba.reglas.{ci}@correo.ucu.edu.uy",
                1,
                "grado",
            ),
        )
        cursor.execute(
            """
            INSERT INTO equipo_jugador_torneo
                (id_equipo, ci_jugador, id_torneo, numero_camiseta)
            VALUES (%s, %s, %s, %s)
            """,
            (id_equipo, ci, id_torneo, 20 + numero),
        )

    probar_falla(
        "plantel con diez jugadores",
        "máximo de 10 jugadores",
        validar_max_plantel,
        cursor,
        id_equipo,
    )
    probar_falla(
        "alta con plantel completo",
        "máximo de 10 jugadores",
        validar_alta_plantel,
        cursor,
        id_equipo,
        50000003,
    )


def main():
    conexion = conectar("administrador")
    cursor = conexion.cursor()

    try:
        conexion.start_transaction()
        ejecutar_pruebas(cursor)
    finally:
        conexion.rollback()
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    main()
