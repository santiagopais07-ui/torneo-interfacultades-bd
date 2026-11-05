from decimal import Decimal

from src.conexion import conectar
from src.reportes import (
    reporte_canchas_mas_usadas,
    reporte_espectadores_por_partido,
    reporte_fair_play_por_equipo,
    reporte_goleadores,
    reporte_inscriptos_sin_planilla,
    reporte_jugadores_por_facultad,
    reporte_partidos_por_arbitro,
    reporte_porcentaje_estados,
    reporte_posiciones,
    reporte_promedio_goles,
    reporte_sanciones_por_equipo,
    reporte_tarjetas_por_arbitro,
    reporte_turnos_mas_usados,
)


NOMBRE_EDICION = "Torneo Interfacultades 2026-2"


def comprobar(nombre, funcion, cursor, id_torneo, esperado):
    obtenido = funcion(cursor, id_torneo)[1]
    if obtenido != esperado:
        raise AssertionError(
            f"{nombre}: esperado {esperado!r}; obtenido {obtenido!r}"
        )
    print(f"OK: {nombre}")


def ejecutar_pruebas(cursor, id_torneo):
    comprobar(
        "Posiciones",
        reporte_posiciones,
        cursor,
        id_torneo,
        [
            (1, "Ingeniería United", 3, 2, 1, 0, 9, 5, 4, 7),
            (2, "Empresariales FC", 3, 2, 0, 1, 6, 4, 2, 6),
            (3, "Salud Deportivo", 3, 1, 1, 1, 5, 4, 1, 4),
            (4, "Arquitectura FC", 3, 1, 1, 1, 3, 3, 0, 4),
            (5, "Derecho Atlético", 3, 1, 0, 2, 3, 6, -3, 3),
            (6, "Humanas Lovers", 3, 0, 1, 2, 3, 7, -4, 1),
        ],
    )
    comprobar(
        "Goleadores",
        reporte_goleadores,
        cursor,
        id_torneo,
        [
            (1, "Facundo Barrios", "Ingeniería United", 5, 0),
            (2, "Martín Roso", "Empresariales FC", 3, 0),
            (3, "Gabriel Cardozo", "Salud Deportivo", 2, 0),
            (4, "Florencia Núñez", "Ingeniería United", 2, 1),
            (5, "Lucía Aguirre", "Empresariales FC", 1, 0),
            (6, "Rocío Alonso", "Salud Deportivo", 1, 0),
            (7, "Ramiro Bentancor", "Humanas Lovers", 1, 0),
            (8, "Federico Castro", "Derecho Atlético", 1, 0),
            (9, "Sebastián Lemos", "Humanas Lovers", 1, 0),
            (10, "Agustina López", "Ingeniería United", 1, 0),
        ],
    )
    comprobar(
        "Fair play por equipo",
        reporte_fair_play_por_equipo,
        cursor,
        id_torneo,
        [
            (1, "Ingeniería United", 2, 0, 2),
            (2, "Arquitectura FC", 3, 0, 3),
            (2, "Humanas Lovers", 3, 0, 3),
            (2, "Salud Deportivo", 3, 0, 3),
            (5, "Derecho Atlético", 1, 1, 4),
            (5, "Empresariales FC", 1, 1, 4),
        ],
    )
    comprobar(
        "Promedio de goles",
        reporte_promedio_goles,
        cursor,
        id_torneo,
        [
            ("Fecha 1", 9, 3, Decimal("3.00")),
            ("Fecha 2", 11, 3, Decimal("3.67")),
            ("Fecha 3", 9, 3, Decimal("3.00")),
            ("Edición", 29, 9, Decimal("3.22")),
        ],
    )

    canchas = reporte_canchas_mas_usadas(cursor, id_torneo)[1]
    turnos = reporte_turnos_mas_usados(cursor, id_torneo)[1]
    canchas_esperadas = [
        ("Cancha 001", "Complejo Pocitos", 4),
        ("Cancha 001", "Complejo Los Aromos", 2),
        ("Cancha 001", "Complejo Costa Azul", 1),
        ("Cancha 002", "Complejo Los Aromos", 1),
        ("Cancha 002", "Complejo Pocitos", 1),
    ]
    turnos_esperados = [
        ("18:00-19:00", 4),
        ("19:00-20:00", 2),
        ("20:00-21:00", 1),
        ("21:00-22:00", 1),
        ("22:00-23:00", 1),
    ]
    if canchas != canchas_esperadas or turnos != turnos_esperados:
        raise AssertionError(
            "Canchas y turnos más usados: "
            f"esperado {(canchas_esperadas, turnos_esperados)!r}; "
            f"obtenido {(canchas, turnos)!r}"
        )
    print("OK: Canchas y turnos más usados")

    comprobar(
        "Jugadores por facultad y tipo",
        reporte_jugadores_por_facultad,
        cursor,
        id_torneo,
        [
            ("Artes y Arquitectura", 5, 1, 0, 1, 7),
            ("Ciencias Empresariales", 5, 1, 0, 1, 7),
            ("Derecho", 6, 0, 1, 0, 7),
            ("Educación y Humanidades", 5, 1, 0, 1, 7),
            ("Ingeniería y Tecnologías", 5, 1, 1, 0, 7),
            ("Salud", 5, 1, 1, 0, 7),
        ],
    )
    comprobar(
        "Inscriptos sin planilla",
        reporte_inscriptos_sin_planilla,
        cursor,
        id_torneo,
        [
            ("Micaela Ferreira", "Arquitectura FC"),
            ("Leandro Correa", "Derecho Atlético"),
            ("Tomas Lopez", "Empresariales FC"),
            ("Delfina Sánchez", "Humanas Lovers"),
            ("Tomás Ibarra", "Ingeniería United"),
            ("Franco Maidana", "Salud Deportivo"),
        ],
    )
    comprobar(
        "Sanciones por equipo y motivo",
        reporte_sanciones_por_equipo,
        cursor,
        id_torneo,
        [
            ("Arquitectura FC", "disciplinaria", 1),
            ("Derecho Atlético", "roja", 1),
            ("Empresariales FC", "roja", 1),
            ("Humanas Lovers", "acumulación de amarillas", 1),
        ],
    )
    comprobar(
        "Porcentaje de partidos por estado",
        reporte_porcentaje_estados,
        cursor,
        id_torneo,
        [
            ("jugado", 9, Decimal("75.00")),
            ("programado", 1, Decimal("8.33")),
            ("postergado", 1, Decimal("8.33")),
            ("cancelado", 1, Decimal("8.33")),
            ("postergado + cancelado", 2, Decimal("16.67")),
        ],
    )
    comprobar(
        "Partidos por árbitro y estado",
        reporte_partidos_por_arbitro,
        cursor,
        id_torneo,
        [
            ("Marcelo Duarte", 3, 0, 0, 1),
            ("Hernán Ledesma", 3, 1, 0, 0),
            ("Carolina Viera", 3, 0, 1, 0),
        ],
    )
    comprobar(
        "Tarjetas por árbitro",
        reporte_tarjetas_por_arbitro,
        cursor,
        id_torneo,
        [
            ("Marcelo Duarte", 5, 1),
            ("Hernán Ledesma", 4, 1),
            ("Carolina Viera", 4, 0),
        ],
    )
    comprobar(
        "Espectadores por partido y tipo",
        reporte_espectadores_por_partido,
        cursor,
        id_torneo,
        [
            ("Fecha 1", "Empresariales FC vs Humanas Lovers", 2, 0, 2),
            ("Fecha 1", "Ingeniería United vs Salud Deportivo", 0, 1, 1),
            ("Fecha 2", "Ingeniería United vs Derecho Atlético", 1, 1, 2),
            ("Fecha 3", "Humanas Lovers vs Ingeniería United", 0, 1, 1),
        ],
    )


def main():
    conexion = None
    cursor = None
    try:
        conexion = conectar("administrador")
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id_torneo FROM torneo WHERE nombre = %s",
            (NOMBRE_EDICION,),
        )
        edicion = cursor.fetchone()
        if edicion is None:
            raise RuntimeError(
                f"No se encontró la edición de prueba {NOMBRE_EDICION!r}"
            )
        ejecutar_pruebas(cursor, edicion[0])
    finally:
        if cursor is not None:
            try:
                cursor.close()
            finally:
                if conexion is not None:
                    conexion.close()
        elif conexion is not None:
            conexion.close()


if __name__ == "__main__":
    main()
