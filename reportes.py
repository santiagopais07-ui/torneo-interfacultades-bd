from datetime import time, timedelta

import mysql.connector

from conexion import conectar


def reporte_posiciones(cursor, id_torneo):
    cursor.execute(
        """
        WITH torneo_seleccionado AS (
            SELECT %s AS id_torneo
        ),
        goles_por_equipo AS (
            SELECT gol.id_partido,
                   CASE
                       WHEN gol.autogol = 1 THEN
                           CASE
                               WHEN planilla_partido.id_equipo = partido.id_equipo_local
                                   THEN partido.id_equipo_visitante
                               ELSE partido.id_equipo_local
                           END
                       ELSE planilla_partido.id_equipo
                   END AS id_equipo_anotador,
                   COUNT(*) AS goles
            FROM gol
            JOIN planilla_partido
                ON planilla_partido.id_partido = gol.id_partido
               AND planilla_partido.ci_jugador = gol.ci_jugador
            JOIN partido ON partido.id_partido = gol.id_partido
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = partido.id_torneo
            WHERE partido.estado = 'jugado'
            GROUP BY gol.id_partido, id_equipo_anotador
        ),
        resultados_partido AS (
            SELECT partido.id_partido,
                   partido.id_equipo_local,
                   partido.id_equipo_visitante,
                   COALESCE(
                       SUM(CASE
                           WHEN goles_por_equipo.id_equipo_anotador =
                                partido.id_equipo_local
                               THEN goles_por_equipo.goles
                           ELSE 0
                       END),
                       0
                   ) AS goles_local,
                   COALESCE(
                       SUM(CASE
                           WHEN goles_por_equipo.id_equipo_anotador =
                                partido.id_equipo_visitante
                               THEN goles_por_equipo.goles
                           ELSE 0
                       END),
                       0
                   ) AS goles_visitante
            FROM partido
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = partido.id_torneo
            LEFT JOIN goles_por_equipo
                ON goles_por_equipo.id_partido = partido.id_partido
            WHERE partido.estado = 'jugado'
            GROUP BY partido.id_partido,
                     partido.id_equipo_local,
                     partido.id_equipo_visitante
        ),
        partidos_por_equipo AS (
            SELECT resultados_partido.id_equipo_local AS id_equipo,
                   resultados_partido.goles_local AS goles_favor,
                   resultados_partido.goles_visitante AS goles_contra
            FROM resultados_partido
            UNION ALL
            SELECT resultados_partido.id_equipo_visitante,
                   resultados_partido.goles_visitante,
                   resultados_partido.goles_local
            FROM resultados_partido
        ),
        estadisticas_equipo AS (
            SELECT partidos_por_equipo.id_equipo,
                   COUNT(*) AS partidos_jugados,
                   SUM(partidos_por_equipo.goles_favor >
                       partidos_por_equipo.goles_contra) AS ganados,
                   SUM(partidos_por_equipo.goles_favor =
                       partidos_por_equipo.goles_contra) AS empatados,
                   SUM(partidos_por_equipo.goles_favor <
                       partidos_por_equipo.goles_contra) AS perdidos,
                   SUM(partidos_por_equipo.goles_favor) AS goles_favor,
                   SUM(partidos_por_equipo.goles_contra) AS goles_contra,
                   SUM(
                       CASE
                           WHEN partidos_por_equipo.goles_favor >
                                partidos_por_equipo.goles_contra THEN 3
                           WHEN partidos_por_equipo.goles_favor =
                                partidos_por_equipo.goles_contra THEN 1
                           ELSE 0
                       END
                   ) AS puntos
            FROM partidos_por_equipo
            GROUP BY partidos_por_equipo.id_equipo
        ),
        tabla_posiciones AS (
            SELECT equipo.nombre AS nombre_equipo,
                   COALESCE(estadisticas_equipo.partidos_jugados, 0)
                       AS partidos_jugados,
                   COALESCE(estadisticas_equipo.ganados, 0) AS ganados,
                   COALESCE(estadisticas_equipo.empatados, 0) AS empatados,
                   COALESCE(estadisticas_equipo.perdidos, 0) AS perdidos,
                   COALESCE(estadisticas_equipo.goles_favor, 0) AS goles_favor,
                   COALESCE(estadisticas_equipo.goles_contra, 0) AS goles_contra,
                   COALESCE(estadisticas_equipo.goles_favor, 0) -
                       COALESCE(estadisticas_equipo.goles_contra, 0)
                       AS diferencia_goles,
                   COALESCE(estadisticas_equipo.puntos, 0) AS puntos
            FROM equipo
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = equipo.id_torneo
            LEFT JOIN estadisticas_equipo
                ON estadisticas_equipo.id_equipo = equipo.id_equipo
        )
        SELECT RANK() OVER (
                   ORDER BY puntos DESC,
                            diferencia_goles DESC,
                            goles_favor DESC
               ) AS posicion,
               nombre_equipo,
               partidos_jugados,
               ganados,
               empatados,
               perdidos,
               goles_favor,
               goles_contra,
               diferencia_goles,
               puntos
        FROM tabla_posiciones
        ORDER BY posicion, nombre_equipo
        """,
        (id_torneo,),
    )
    return (
        ("Posición", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "DG", "Pts"),
        cursor.fetchall(),
    )


def reporte_goleadores(cursor, id_torneo):
    cursor.execute(
        """
        WITH torneo_seleccionado AS (
            SELECT %s AS id_torneo
        ),
        goles_jugador AS (
            SELECT gol.ci_jugador, COUNT(*) AS goles
            FROM gol
            JOIN partido ON partido.id_partido = gol.id_partido
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = partido.id_torneo
            WHERE partido.estado = 'jugado'
              AND gol.autogol = 0
            GROUP BY gol.ci_jugador
        ),
        fair_play_jugador AS (
            SELECT planilla_partido.ci_jugador,
                   SUM(
                       CASE tarjeta.color
                           WHEN 'amarilla' THEN 1
                           WHEN 'roja' THEN 3
                           ELSE 0
                       END
                   ) AS puntos_fair_play
            FROM tarjeta
            JOIN planilla_partido
                ON planilla_partido.id_partido = tarjeta.id_partido
               AND planilla_partido.ci_jugador = tarjeta.ci_jugador
            JOIN partido ON partido.id_partido = tarjeta.id_partido
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = partido.id_torneo
            WHERE partido.estado = 'jugado'
            GROUP BY planilla_partido.ci_jugador
        ),
        goleadores_ordenados AS (
            SELECT jugador.nombre,
                   jugador.apellido,
                   equipo.nombre AS nombre_equipo,
                   goles_jugador.goles,
                   COALESCE(fair_play_jugador.puntos_fair_play, 0)
                       AS puntos_fair_play,
                   ROW_NUMBER() OVER (
                       ORDER BY goles_jugador.goles DESC,
                                COALESCE(
                                    fair_play_jugador.puntos_fair_play,
                                    0
                                ),
                                jugador.apellido,
                                jugador.nombre,
                                jugador.ci
                   ) AS posicion
            FROM goles_jugador
            JOIN jugador ON jugador.ci = goles_jugador.ci_jugador
            JOIN equipo_jugador_torneo
                ON equipo_jugador_torneo.ci_jugador = jugador.ci
            JOIN equipo
                ON equipo.id_equipo = equipo_jugador_torneo.id_equipo
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo =
                   equipo_jugador_torneo.id_torneo
            LEFT JOIN fair_play_jugador
                ON fair_play_jugador.ci_jugador = jugador.ci
        )
        SELECT posicion, nombre, apellido, nombre_equipo, goles,
               puntos_fair_play
        FROM goleadores_ordenados
        WHERE posicion <= 10
        ORDER BY posicion
        """,
        (id_torneo,),
    )
    filas = [
        (posicion, f"{nombre} {apellido}", equipo, goles, puntos_fair_play)
        for posicion, nombre, apellido, equipo, goles, puntos_fair_play
        in cursor.fetchall()
    ]
    return ("Posición", "Jugador", "Equipo", "Goles", "Fair play"), filas


def reporte_fair_play_por_equipo(cursor, id_torneo):
    cursor.execute(
        """
        WITH torneo_seleccionado AS (
            SELECT %s AS id_torneo
        ),
        tarjetas_por_equipo AS (
            SELECT planilla_partido.id_equipo,
                   COUNT(CASE WHEN tarjeta.color = 'amarilla' THEN 1 END)
                       AS amarillas,
                   COUNT(CASE WHEN tarjeta.color = 'roja' THEN 1 END) AS rojas
            FROM tarjeta
            JOIN planilla_partido
                ON planilla_partido.id_partido = tarjeta.id_partido
               AND planilla_partido.ci_jugador = tarjeta.ci_jugador
            JOIN partido ON partido.id_partido = tarjeta.id_partido
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = partido.id_torneo
            WHERE partido.estado = 'jugado'
            GROUP BY planilla_partido.id_equipo
        ),
        equipos_fair_play AS (
            SELECT equipo.nombre AS nombre_equipo,
                   COALESCE(tarjetas_por_equipo.amarillas, 0) AS amarillas,
                   COALESCE(tarjetas_por_equipo.rojas, 0) AS rojas,
                   COALESCE(tarjetas_por_equipo.amarillas, 0) +
                       3 * COALESCE(tarjetas_por_equipo.rojas, 0) AS puntos
            FROM equipo
            JOIN torneo_seleccionado
                ON torneo_seleccionado.id_torneo = equipo.id_torneo
            LEFT JOIN tarjetas_por_equipo
                ON tarjetas_por_equipo.id_equipo = equipo.id_equipo
        )
        SELECT RANK() OVER (ORDER BY puntos) AS posicion,
               nombre_equipo, amarillas, rojas, puntos
        FROM equipos_fair_play
        ORDER BY posicion, nombre_equipo
        """,
        (id_torneo,),
    )
    return (
        ("Posición", "Equipo", "Amarillas", "Rojas", "Puntos"),
        cursor.fetchall(),
    )


def reporte_promedio_goles(cursor, id_torneo):
    cursor.execute(
        """
        WITH partidos_jugados AS (
            SELECT partido.id_partido, partido.numero_fecha
            FROM partido
            WHERE partido.id_torneo = %s
              AND partido.estado = 'jugado'
        ),
        estadisticas_fecha AS (
            SELECT partidos_jugados.numero_fecha,
                   COUNT(gol.id_gol) AS goles,
                   COUNT(DISTINCT partidos_jugados.id_partido) AS partidos
            FROM partidos_jugados
            LEFT JOIN gol
                ON gol.id_partido = partidos_jugados.id_partido
            GROUP BY partidos_jugados.numero_fecha
        ),
        estadistica_edicion AS (
            SELECT COALESCE(SUM(estadisticas_fecha.goles), 0) AS goles,
                   COALESCE(SUM(estadisticas_fecha.partidos), 0) AS partidos
            FROM estadisticas_fecha
        )
        SELECT CAST(estadisticas_fecha.numero_fecha AS CHAR) AS fecha,
               estadisticas_fecha.goles,
               estadisticas_fecha.partidos,
               ROUND(
                   estadisticas_fecha.goles /
                   NULLIF(estadisticas_fecha.partidos, 0),
                   2
               ) AS promedio,
               estadisticas_fecha.numero_fecha AS orden
        FROM estadisticas_fecha
        UNION ALL
        SELECT 'Edición',
               estadistica_edicion.goles,
               estadistica_edicion.partidos,
               ROUND(
                   estadistica_edicion.goles /
                   NULLIF(estadistica_edicion.partidos, 0),
                   2
               ),
               2147483647
        FROM estadistica_edicion
        ORDER BY orden
        """,
        (id_torneo,),
    )
    filas = [
        (
            "Edición" if fecha == "Edición" else f"Fecha {fecha}",
            goles,
            partidos,
            promedio,
        )
        for fecha, goles, partidos, promedio, _ in cursor.fetchall()
    ]
    return ("Fecha", "Goles", "Partidos jugados", "Promedio"), filas


def reporte_canchas_mas_usadas(cursor, id_torneo):
    cursor.execute(
        """
        SELECT cancha.nombre_cancha,
               complejo.nombre,
               COUNT(partido.id_partido) AS partidos_jugados
        FROM partido
        JOIN cancha
            ON cancha.nombre_cancha = partido.nombre_cancha
           AND cancha.id_complejo = partido.id_complejo
        JOIN complejo ON complejo.id_complejo = cancha.id_complejo
        WHERE partido.id_torneo = %s
          AND partido.estado = 'jugado'
        GROUP BY cancha.nombre_cancha, complejo.nombre, cancha.id_complejo
        ORDER BY partidos_jugados DESC, complejo.nombre, cancha.nombre_cancha
        """,
        (id_torneo,),
    )
    return ("Cancha", "Complejo", "Partidos jugados"), cursor.fetchall()


def _formatear_hora(valor):
    if isinstance(valor, timedelta):
        segundos = int(valor.total_seconds())
        horas, resto = divmod(segundos, 3600)
        minutos = resto // 60
        return f"{horas:02d}:{minutos:02d}"
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    return str(valor)[:5]


def reporte_turnos_mas_usados(cursor, id_torneo):
    cursor.execute(
        """
        SELECT turno.hora_inicio,
               turno.hora_fin,
               COUNT(partido.id_partido) AS partidos_jugados
        FROM partido
        JOIN turno ON turno.id_turno = partido.id_turno
        WHERE partido.id_torneo = %s
          AND partido.estado = 'jugado'
        GROUP BY turno.id_turno, turno.hora_inicio, turno.hora_fin
        ORDER BY partidos_jugados DESC, turno.hora_inicio, turno.hora_fin
        """,
        (id_torneo,),
    )
    filas = [
        (
            f"{_formatear_hora(hora_inicio)}-{_formatear_hora(hora_fin)}",
            partidos_jugados,
        )
        for hora_inicio, hora_fin, partidos_jugados in cursor.fetchall()
    ]
    return ("Turno", "Partidos jugados"), filas


def reporte_jugadores_por_facultad(cursor, id_torneo):
    cursor.execute(
        """
        SELECT facultad.nombre,
               COUNT(CASE WHEN jugador.tipo = 'grado' THEN 1 END) AS grado,
               COUNT(CASE WHEN jugador.tipo = 'posgrado' THEN 1 END) AS posgrado,
               COUNT(CASE WHEN jugador.tipo = 'docente' THEN 1 END) AS docente,
               COUNT(CASE WHEN jugador.tipo = 'funcionario' THEN 1 END)
                   AS funcionario,
               COUNT(*) AS total
        FROM equipo_jugador_torneo
        JOIN jugador ON jugador.ci = equipo_jugador_torneo.ci_jugador
        JOIN equipo
            ON equipo.id_equipo = equipo_jugador_torneo.id_equipo
           AND equipo.id_torneo = equipo_jugador_torneo.id_torneo
        JOIN facultad ON facultad.id_facultad = jugador.id_facultad
        WHERE equipo_jugador_torneo.id_torneo = %s
        GROUP BY facultad.id_facultad, facultad.nombre
        ORDER BY facultad.nombre
        """,
        (id_torneo,),
    )
    return (
        ("Facultad", "Grado", "Posgrado", "Docente", "Funcionario", "Total"),
        cursor.fetchall(),
    )


def reporte_inscriptos_sin_planilla(cursor, id_torneo):
    cursor.execute(
        """
        SELECT jugador.nombre,
               jugador.apellido,
               equipo.nombre AS nombre_equipo
        FROM equipo_jugador_torneo
        JOIN jugador ON jugador.ci = equipo_jugador_torneo.ci_jugador
        JOIN equipo
            ON equipo.id_equipo = equipo_jugador_torneo.id_equipo
           AND equipo.id_torneo = equipo_jugador_torneo.id_torneo
        WHERE equipo_jugador_torneo.id_torneo = %s
          AND NOT EXISTS (
              SELECT 1
              FROM planilla_partido
              JOIN partido
                  ON partido.id_partido = planilla_partido.id_partido
              WHERE partido.id_torneo = equipo_jugador_torneo.id_torneo
                AND planilla_partido.ci_jugador =
                    equipo_jugador_torneo.ci_jugador
          )
        ORDER BY equipo.nombre, jugador.apellido, jugador.nombre
        """,
        (id_torneo,),
    )
    filas = [
        (f"{nombre} {apellido}", equipo)
        for nombre, apellido, equipo in cursor.fetchall()
    ]
    return ("Jugador", "Equipo"), filas


def reporte_sanciones_por_equipo(cursor, id_torneo):
    cursor.execute(
        """
        SELECT equipo.nombre,
               sancion_jugador.motivo,
               COUNT(*) AS cantidad
        FROM sancion_jugador
        JOIN equipo_jugador_torneo
            ON equipo_jugador_torneo.ci_jugador = sancion_jugador.ci_jugador
           AND equipo_jugador_torneo.id_torneo = sancion_jugador.id_torneo
        JOIN equipo
            ON equipo.id_equipo = equipo_jugador_torneo.id_equipo
           AND equipo.id_torneo = equipo_jugador_torneo.id_torneo
        WHERE sancion_jugador.id_torneo = %s
        GROUP BY equipo.id_equipo, equipo.nombre, sancion_jugador.motivo
        ORDER BY equipo.nombre, sancion_jugador.motivo
        """,
        (id_torneo,),
    )
    return ("Equipo", "Motivo", "Cantidad"), cursor.fetchall()


def reporte_porcentaje_estados(cursor, id_torneo):
    cursor.execute(
        """
        WITH resumen AS (
            SELECT COUNT(*) AS total,
                   COUNT(CASE WHEN partido.estado = 'jugado' THEN 1 END)
                       AS jugado,
                   COUNT(CASE WHEN partido.estado = 'programado' THEN 1 END)
                       AS programado,
                   COUNT(CASE WHEN partido.estado = 'postergado' THEN 1 END)
                       AS postergado,
                   COUNT(CASE WHEN partido.estado = 'cancelado' THEN 1 END)
                       AS cancelado
            FROM partido
            WHERE partido.id_torneo = %s
        ),
        estados AS (
            SELECT 'jugado' AS estado, 1 AS orden
            UNION ALL
            SELECT 'programado', 2
            UNION ALL
            SELECT 'postergado', 3
            UNION ALL
            SELECT 'cancelado', 4
        ),
        cantidades AS (
            SELECT estados.estado,
                   estados.orden,
                   CASE estados.estado
                       WHEN 'jugado' THEN resumen.jugado
                       WHEN 'programado' THEN resumen.programado
                       WHEN 'postergado' THEN resumen.postergado
                       WHEN 'cancelado' THEN resumen.cancelado
                   END AS cantidad,
                   resumen.total
            FROM estados
            CROSS JOIN resumen
        )
        SELECT estado,
               cantidad,
               COALESCE(
                   ROUND(100 * cantidad / NULLIF(total, 0), 2),
                   0.00
               ) AS porcentaje
        FROM cantidades
        UNION ALL
        SELECT 'postergado + cancelado',
               resumen.postergado + resumen.cancelado,
               COALESCE(
                   ROUND(
                       100 * (resumen.postergado + resumen.cancelado) /
                       NULLIF(resumen.total, 0),
                       2
                   ),
                   0.00
               )
        FROM resumen
        ORDER BY CASE estado
                     WHEN 'jugado' THEN 1
                     WHEN 'programado' THEN 2
                     WHEN 'postergado' THEN 3
                     WHEN 'cancelado' THEN 4
                     ELSE 5
                 END
        """,
        (id_torneo,),
    )
    return ("Estado", "Partidos", "Porcentaje"), cursor.fetchall()


def reporte_partidos_por_arbitro(cursor, id_torneo):
    cursor.execute(
        """
        SELECT arbitro.nombre,
               arbitro.apellido,
               COUNT(CASE WHEN partido.estado = 'jugado' THEN 1 END)
                   AS jugados,
               COUNT(CASE WHEN partido.estado = 'programado' THEN 1 END)
                   AS programados,
               COUNT(CASE WHEN partido.estado = 'postergado' THEN 1 END)
                   AS postergados,
               COUNT(CASE WHEN partido.estado = 'cancelado' THEN 1 END)
                   AS cancelados
        FROM arbitro
        LEFT JOIN partido
            ON partido.ci_arbitro = arbitro.ci_arbitro
           AND partido.id_torneo = %s
        GROUP BY arbitro.ci_arbitro, arbitro.apellido, arbitro.nombre
        ORDER BY arbitro.apellido, arbitro.nombre
        """,
        (id_torneo,),
    )
    filas = [
        (f"{nombre} {apellido}", jugados, programados, postergados, cancelados)
        for nombre, apellido, jugados, programados, postergados, cancelados
        in cursor.fetchall()
    ]
    return (
        ("Árbitro", "Jugados", "Programados", "Postergados", "Cancelados"),
        filas,
    )


def reporte_tarjetas_por_arbitro(cursor, id_torneo):
    cursor.execute(
        """
        SELECT arbitro.nombre,
               arbitro.apellido,
               COUNT(CASE WHEN tarjeta.color = 'amarilla' THEN 1 END)
                   AS amarillas,
               COUNT(CASE WHEN tarjeta.color = 'roja' THEN 1 END) AS rojas
        FROM arbitro
        LEFT JOIN partido
            ON partido.ci_arbitro = arbitro.ci_arbitro
           AND partido.id_torneo = %s
        LEFT JOIN tarjeta ON tarjeta.id_partido = partido.id_partido
        GROUP BY arbitro.ci_arbitro, arbitro.apellido, arbitro.nombre
        ORDER BY arbitro.apellido, arbitro.nombre
        """,
        (id_torneo,),
    )
    filas = [
        (f"{nombre} {apellido}", amarillas, rojas)
        for nombre, apellido, amarillas, rojas in cursor.fetchall()
    ]
    return ("Árbitro", "Amarillas", "Rojas"), filas


def reporte_espectadores_por_partido(cursor, id_torneo):
    cursor.execute(
        """
        SELECT partido.numero_fecha,
               equipo_local.nombre,
               equipo_visitante.nombre,
               COUNT(CASE WHEN espectador.tipo = 'facultad' THEN 1 END)
                   AS facultad,
               COUNT(CASE WHEN espectador.tipo = 'externo' THEN 1 END)
                   AS externo,
               COUNT(*) AS total
        FROM espectador
        JOIN partido ON partido.id_partido = espectador.id_partido
        JOIN equipo AS equipo_local
            ON equipo_local.id_equipo = partido.id_equipo_local
           AND equipo_local.id_torneo = partido.id_torneo
        JOIN equipo AS equipo_visitante
            ON equipo_visitante.id_equipo = partido.id_equipo_visitante
           AND equipo_visitante.id_torneo = partido.id_torneo
        WHERE partido.id_torneo = %s
        GROUP BY partido.id_partido,
                 partido.numero_fecha,
                 partido.dia,
                 equipo_local.nombre,
                 equipo_visitante.nombre
        ORDER BY partido.dia, partido.id_partido
        """,
        (id_torneo,),
    )
    filas = [
        (
            f"Fecha {fecha}",
            f"{equipo_local} vs {equipo_visitante}",
            facultad,
            externo,
            total,
        )
        for fecha, equipo_local, equipo_visitante, facultad, externo, total
        in cursor.fetchall()
    ]
    return ("Fecha", "Partido", "Facultad", "Externo", "Total"), filas


def imprimir_tabla(titulo, encabezados, filas):
    print(f"\n{titulo}")
    if not filas:
        print("No hay datos para mostrar.")
        return

    filas_texto = [
        tuple("-" if valor is None else str(valor) for valor in fila)
        for fila in filas
    ]
    anchos = [
        max(
            len(str(encabezado)),
            *(len(fila[indice]) for fila in filas_texto),
        )
        for indice, encabezado in enumerate(encabezados)
    ]

    def linea(fila):
        return " | ".join(
            valor.ljust(anchos[indice])
            for indice, valor in enumerate(fila)
        )

    print(linea(tuple(str(encabezado) for encabezado in encabezados)))
    print("-+-".join("-" * ancho for ancho in anchos))
    for fila in filas_texto:
        print(linea(fila))


def _imprimir_reporte(titulo, funcion, cursor, id_torneo):
    encabezados, filas = funcion(cursor, id_torneo)
    imprimir_tabla(titulo, encabezados, filas)


def menu_reportes():
    conexion = None
    cursor = None
    try:
        conexion = conectar("administrador")
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT torneo.id_torneo, torneo.nombre, torneo.anio, torneo.semestre
            FROM torneo
            ORDER BY torneo.anio DESC, torneo.semestre, torneo.nombre
            """
        )
        ediciones = cursor.fetchall()
        if not ediciones:
            print("No hay ediciones registradas.")
            return

        imprimir_tabla(
            "Ediciones",
            ("ID", "Nombre", "Año", "Semestre"),
            ediciones,
        )
        ids_ediciones = {edicion[0] for edicion in ediciones}
        while True:
            texto_id = input("ID de la edición (0 para volver): ").strip()
            if texto_id == "0":
                return
            if not texto_id.isdecimal():
                print("Ingresá un ID numérico de edición.")
                continue
            id_torneo = int(texto_id)
            if id_torneo not in ids_ediciones:
                print("Ese ID no corresponde a una edición existente.")
                continue
            break

        reportes = {
            "1": ("Posiciones", reporte_posiciones),
            "2": ("Goleadores", reporte_goleadores),
            "3": ("Fair play por equipo", reporte_fair_play_por_equipo),
            "4": ("Promedio de goles", reporte_promedio_goles),
            "6": ("Jugadores por facultad y tipo", reporte_jugadores_por_facultad),
            "7": (
                "Inscriptos que nunca figuraron en una planilla",
                reporte_inscriptos_sin_planilla,
            ),
            "8": ("Sanciones por equipo y motivo", reporte_sanciones_por_equipo),
            "9": ("Porcentaje de partidos por estado", reporte_porcentaje_estados),
            "10": ("Partidos por árbitro y estado", reporte_partidos_por_arbitro),
            "11": ("Tarjetas por árbitro", reporte_tarjetas_por_arbitro),
            "12": (
                "Espectadores por partido y tipo",
                reporte_espectadores_por_partido,
            ),
        }

        while True:
            print(
                "\nREPORTES\n"
                "1. Posiciones\n"
                "2. Goleadores\n"
                "3. Fair play por equipo\n"
                "4. Promedio de goles por fecha y edición\n"
                "5. Canchas y turnos más usados\n"
                "6. Jugadores por facultad y tipo\n"
                "7. Inscriptos sin planilla\n"
                "8. Sanciones por equipo y motivo\n"
                "9. Porcentaje de partidos por estado\n"
                "10. Partidos por árbitro y estado\n"
                "11. Tarjetas por árbitro\n"
                "12. Espectadores por partido y tipo\n"
                "0. Volver"
            )
            opcion = input("Elegí una opción: ").strip()
            if opcion == "0":
                return
            if opcion not in reportes and opcion != "5":
                print("Opción inválida. Elegí un reporte del 1 al 12 o 0.")
                continue
            if opcion == "5":
                _imprimir_reporte(
                    "Canchas más usadas",
                    reporte_canchas_mas_usadas,
                    cursor,
                    id_torneo,
                )
                _imprimir_reporte(
                    "Turnos más usados",
                    reporte_turnos_mas_usados,
                    cursor,
                    id_torneo,
                )
            else:
                titulo, funcion = reportes[opcion]
                _imprimir_reporte(titulo, funcion, cursor, id_torneo)
    except mysql.connector.Error as error:
        print(f"No se pudieron consultar los reportes (MySQL {error.errno}).")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            finally:
                if conexion is not None:
                    conexion.close()
        elif conexion is not None:
            conexion.close()
