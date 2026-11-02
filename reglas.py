from datetime import datetime, timedelta


def validar_max_docentes_funcionarios(cursor, id_equipo, ci_jugador):
    cursor.execute(
        "SELECT id_equipo FROM equipo WHERE id_equipo = %s FOR UPDATE",
        (id_equipo,),
    )
    equipo = cursor.fetchone()
    if equipo is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")

    cursor.execute(
        "SELECT tipo FROM jugador WHERE ci = %s",
        (ci_jugador,),
    )
    jugador = cursor.fetchone()
    if jugador is None:
        raise ValueError(f"No existe un jugador con CI {ci_jugador}")

    if jugador[0] in ("grado", "posgrado"):
        return

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM equipo_jugador_torneo
        JOIN jugador ON jugador.ci = equipo_jugador_torneo.ci_jugador
        WHERE equipo_jugador_torneo.id_equipo = %s
          AND jugador.tipo IN ('docente', 'funcionario')
        """,
        (id_equipo,),
    )
    cantidad = cursor.fetchone()[0]

    if cantidad >= 2:
        raise ValueError(
            "El equipo ya tiene el máximo de 2 docentes o funcionarios"
        )


def validar_torneo_en_inscripcion(cursor, id_equipo):
    cursor.execute(
        """
        SELECT torneo.estado
        FROM equipo
        JOIN torneo ON torneo.id_torneo = equipo.id_torneo
        WHERE equipo.id_equipo = %s
        """,
        (id_equipo,),
    )
    torneo = cursor.fetchone()

    if torneo is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")

    if torneo[0] != "inscripción":
        raise ValueError("El torneo del equipo no está en inscripción")


def validar_misma_facultad(cursor, id_equipo, ci_jugador):
    cursor.execute(
        "SELECT id_facultad FROM equipo WHERE id_equipo = %s",
        (id_equipo,),
    )
    equipo = cursor.fetchone()
    if equipo is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")

    cursor.execute(
        "SELECT id_facultad FROM jugador WHERE ci = %s",
        (ci_jugador,),
    )
    jugador = cursor.fetchone()
    if jugador is None:
        raise ValueError(f"No existe un jugador con CI {ci_jugador}")

    if equipo[0] != jugador[0]:
        raise ValueError("El jugador y el equipo pertenecen a facultades distintas")


def validar_max_plantel(cursor, id_equipo):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM equipo_jugador_torneo
        WHERE equipo_jugador_torneo.id_equipo = %s
        """,
        (id_equipo,),
    )
    cantidad = cursor.fetchone()[0]

    if cantidad >= 10:
        raise ValueError("El plantel ya tiene el máximo de 10 jugadores")


def validar_alta_plantel(cursor, id_equipo, ci_jugador):
    cursor.execute(
        "SELECT id_equipo FROM equipo WHERE id_equipo = %s FOR UPDATE",
        (id_equipo,),
    )
    if cursor.fetchone() is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")
    validar_torneo_en_inscripcion(cursor, id_equipo)
    validar_misma_facultad(cursor, id_equipo, ci_jugador)
    validar_max_plantel(cursor, id_equipo)
    validar_max_docentes_funcionarios(cursor, id_equipo, ci_jugador)


def validar_min_jugadores(cursor, id_equipo):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM equipo_jugador_torneo
        WHERE equipo_jugador_torneo.id_equipo = %s
        """,
        (id_equipo,),
    )
    cantidad = cursor.fetchone()[0]

    if cantidad < 5:
        raise ValueError("El plantel debe tener al menos 5 jugadores")


def validar_rival_no_repetido(
    cursor,
    id_torneo,
    id_equipo_local,
    id_equipo_visitante,
    id_partido_excluir=None,
):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM partido
        WHERE partido.id_torneo = %s
          AND (
              (
                  partido.id_equipo_local = %s
                  AND partido.id_equipo_visitante = %s
              )
              OR (
                  partido.id_equipo_local = %s
                  AND partido.id_equipo_visitante = %s
              )
          )
          AND partido.estado <> 'cancelado'
          AND (%s IS NULL OR partido.id_partido <> %s)
        """,
        (
            id_torneo,
            id_equipo_local,
            id_equipo_visitante,
            id_equipo_visitante,
            id_equipo_local,
            id_partido_excluir,
            id_partido_excluir,
        ),
    )
    cantidad = cursor.fetchone()[0]

    if cantidad > 0:
        raise ValueError(
            "Estos equipos ya se enfrentaron en el torneo"
        )


def validar_un_partido_por_fecha(
    cursor,
    id_torneo,
    numero_fecha,
    id_equipo,
    id_partido_excluir=None,
):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM partido
        WHERE partido.id_torneo = %s
          AND partido.numero_fecha = %s
          AND (
              partido.id_equipo_local = %s
              OR partido.id_equipo_visitante = %s
          )
          AND (%s IS NULL OR partido.id_partido <> %s)
        """,
        (
            id_torneo,
            numero_fecha,
            id_equipo,
            id_equipo,
            id_partido_excluir,
            id_partido_excluir,
        ),
    )
    cantidad = cursor.fetchone()[0]

    if cantidad > 0:
        raise ValueError(
            f"El equipo {id_equipo} ya tiene un partido en la fecha {numero_fecha}"
        )


def validar_alta_partido(
    cursor,
    id_torneo,
    numero_fecha,
    id_equipo_local,
    id_equipo_visitante,
    id_partido_excluir=None,
):
    validar_min_jugadores(cursor, id_equipo_local)
    validar_min_jugadores(cursor, id_equipo_visitante)
    validar_rival_no_repetido(
        cursor,
        id_torneo,
        id_equipo_local,
        id_equipo_visitante,
        id_partido_excluir,
    )
    validar_un_partido_por_fecha(
        cursor,
        id_torneo,
        numero_fecha,
        id_equipo_local,
        id_partido_excluir,
    )
    validar_un_partido_por_fecha(
        cursor,
        id_torneo,
        numero_fecha,
        id_equipo_visitante,
        id_partido_excluir,
    )


def validar_partido_disputado(cursor, id_partido, ahora=None):
    if ahora is None:
        ahora = datetime.now()

    cursor.execute(
        """
        SELECT TIMESTAMP(partido.dia, turno.hora_fin)
        FROM partido
        JOIN turno ON turno.id_turno = partido.id_turno
        WHERE partido.id_partido = %s
        """,
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    if partido[0] > ahora:
        raise ValueError("El partido todavía no se ha disputado")


def validar_ventana_correccion(cursor, id_partido, ahora=None):
    if ahora is None:
        ahora = datetime.now()

    cursor.execute(
        """
        SELECT partido.estado, TIMESTAMP(partido.dia, turno.hora_fin)
        FROM partido
        JOIN turno ON turno.id_turno = partido.id_turno
        WHERE partido.id_partido = %s
        """,
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    if (
        partido[0] == "jugado"
        and ahora > partido[1] + timedelta(hours=48)
    ):
        raise ValueError("Pasaron más de 48 horas para corregir el partido")


def validar_partido_registrable(cursor, id_partido, ahora=None):
    if ahora is None:
        ahora = datetime.now()

    cursor.execute(
        "SELECT estado FROM partido WHERE id_partido = %s",
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    if partido[0] in ("cancelado", "postergado"):
        raise ValueError("El partido cancelado o postergado no es registrable")

    validar_partido_disputado(cursor, id_partido, ahora)
    validar_ventana_correccion(cursor, id_partido, ahora)


def validar_equipo_del_partido(cursor, id_partido, id_equipo):
    cursor.execute(
        """
        SELECT partido.id_equipo_local, partido.id_equipo_visitante
        FROM partido
        WHERE partido.id_partido = %s
        """,
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    if id_equipo not in partido:
        raise ValueError(
            f"El equipo {id_equipo} no participa en el partido {id_partido}"
        )


def validar_jugador_no_suspendido(cursor, id_partido, ci_jugador):
    cursor.execute(
        """
        SELECT partido.id_torneo, partido.numero_fecha
        FROM partido
        WHERE partido.id_partido = %s
        """,
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM sancion_jugador
        WHERE sancion_jugador.ci_jugador = %s
          AND sancion_jugador.id_torneo = %s
          AND %s BETWEEN sancion_jugador.numero_fecha_inicio
              AND sancion_jugador.numero_fecha_inicio
                  + sancion_jugador.cantidad_fechas - 1
        """,
        (ci_jugador, partido[0], partido[1]),
    )
    sanciones = cursor.fetchone()[0]

    if sanciones > 0:
        raise ValueError(
            f"El jugador {ci_jugador} está suspendido en la fecha {partido[1]}"
        )


def validar_alta_planilla(
    cursor,
    id_partido,
    ci_jugador,
    id_equipo,
    ahora=None,
):
    if ahora is None:
        ahora = datetime.now()

    validar_partido_registrable(cursor, id_partido, ahora)
    validar_equipo_del_partido(cursor, id_partido, id_equipo)
    validar_jugador_no_suspendido(cursor, id_partido, ci_jugador)


def validar_baja_partido(cursor, id_partido):
    cursor.execute(
        "SELECT estado FROM partido WHERE id_partido = %s",
        (id_partido,),
    )
    partido = cursor.fetchone()

    if partido is None:
        raise ValueError(f"No existe un partido con id {id_partido}")

    if partido[0] == "jugado":
        raise ValueError("No se puede cancelar un partido que ya fue jugado")


def registrar_cambio(cursor, id_partido, correo, descripcion):
    cursor.execute(
        """
        INSERT INTO cambios
            (id_partido, correo_cambiante, descripcion_cambio)
        VALUES (%s, %s, %s)
        """,
        (id_partido, correo, descripcion[:100]),
    )


def recalcular_sanciones_automaticas(cursor, ci_jugador, id_torneo):
    cursor.execute(
        """
        DELETE FROM sancion_jugador
        WHERE sancion_jugador.ci_jugador = %s
          AND sancion_jugador.id_torneo = %s
          AND sancion_jugador.motivo IN ('roja', 'acumulación de amarillas')
        """,
        (ci_jugador, id_torneo),
    )

    cursor.execute(
        """
        SELECT tarjeta.color, partido.numero_fecha
        FROM tarjeta
        JOIN partido ON partido.id_partido = tarjeta.id_partido
        WHERE tarjeta.ci_jugador = %s
          AND partido.id_torneo = %s
        ORDER BY
            partido.numero_fecha,
            partido.dia,
            tarjeta.minuto,
            tarjeta.id_tarjeta
        """,
        (ci_jugador, id_torneo),
    )
    tarjeta = cursor.fetchone()
    tarjetas = []
    while tarjeta is not None:
        tarjetas.append(tarjeta)
        tarjeta = cursor.fetchone()

    amarillas = 0

    for tarjeta in tarjetas:
        color, numero_fecha = tarjeta
        motivo = None

        if color == "roja":
            motivo = "roja"
        elif color == "amarilla":
            amarillas += 1
            if amarillas % 3 == 0:
                motivo = "acumulación de amarillas"

        if motivo is not None:
            cursor.execute(
                """
                INSERT INTO sancion_jugador
                    (
                        ci_jugador,
                        id_torneo,
                        motivo,
                        numero_fecha_inicio,
                        cantidad_fechas
                    )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ci_jugador, id_torneo, motivo, numero_fecha + 1, 1),
            )


def validar_cambio_etapa(cursor, id_torneo, nuevo_estado):
    cursor.execute(
        "SELECT estado FROM torneo WHERE id_torneo = %s",
        (id_torneo,),
    )
    torneo = cursor.fetchone()

    if torneo is None:
        raise ValueError(f"No existe un torneo con id {id_torneo}")

    transiciones = {
        "inscripción": "en curso",
        "en curso": "finalizado",
    }
    estado_actual = torneo[0]
    if transiciones.get(estado_actual) != nuevo_estado:
        raise ValueError(
            f"No se puede cambiar el torneo de '{estado_actual}' "
            f"a '{nuevo_estado}'"
        )

    if nuevo_estado == "en curso":
        cursor.execute(
            "SELECT id_equipo FROM equipo WHERE id_torneo = %s",
            (id_torneo,),
        )
        equipos = []
        equipo = cursor.fetchone()
        while equipo is not None:
            equipos.append(equipo[0])
            equipo = cursor.fetchone()

        for id_equipo in equipos:
            validar_min_jugadores(cursor, id_equipo)


def validar_capitan_en_plantel(cursor, id_equipo):
    cursor.execute(
        "SELECT ci_capitan FROM equipo WHERE id_equipo = %s",
        (id_equipo,),
    )
    equipo = cursor.fetchone()

    if equipo is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")

    cursor.execute(
        """
        SELECT ci_jugador
        FROM equipo_jugador_torneo
        WHERE id_equipo = %s AND ci_jugador = %s
        """,
        (id_equipo, equipo[0]),
    )
    capitan = cursor.fetchone()

    if capitan is None:
        raise ValueError("El capitán del equipo no está en el plantel")


def validar_baja_jugador_plantel(cursor, id_equipo, ci_jugador):
    validar_torneo_en_inscripcion(cursor, id_equipo)

    cursor.execute(
        "SELECT ci_capitan FROM equipo WHERE id_equipo = %s",
        (id_equipo,),
    )
    equipo = cursor.fetchone()

    if equipo is None:
        raise ValueError(f"No existe un equipo con id {id_equipo}")

    if equipo[0] == ci_jugador:
        raise ValueError("No se puede dar de baja al capitán del equipo")


def validar_sancion_disciplinaria(cursor, motivo, rol):
    if motivo == "disciplinaria" and rol != "administrador":
        raise ValueError(
            "Solo un administrador puede registrar una sanción disciplinaria"
        )
