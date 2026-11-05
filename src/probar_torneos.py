"""Pruebas transaccionales: no conserva las ediciones de prueba."""
from datetime import date
from unittest.mock import patch, MagicMock
from src.conexion import conectar
from src.torneos import crear_torneo, cambiar_etapa, menu_torneos


def main():
    conexion = conectar('administrador')
    cursor = conexion.cursor()
    usuario = {'rol': 'administrador'}
    cantidad = 0
    def rechaza(operacion):
        nonlocal cantidad
        try:
            operacion()
        except ValueError:
            cantidad += 1
        else:
            raise AssertionError('La operación debía rechazarse.')
    try:
        cursor.execute('SELECT COUNT(*) FROM torneo')
        antes = cursor.fetchone()[0]
        cursor.execute("SELECT anio FROM torneo WHERE semestre='Primero'")
        usados = {f[0] for f in cursor.fetchall()}
        anio = next(a for a in range(9000, 9999) if a not in usados)
        inicio, fin = date(anio,1,1), date(anio,6,30)
        identificador = crear_torneo(cursor,usuario,'Prueba temporal',anio,'Primero',inicio,fin)
        cursor.execute('SELECT estado FROM torneo WHERE id_torneo=%s',(identificador,))
        assert cursor.fetchone()[0] == 'inscripción'
        cantidad += 1
        rechaza(lambda: crear_torneo(cursor,usuario,'Duplicado',anio,'Primero',inicio,fin))
        rechaza(lambda: crear_torneo(cursor,usuario,'',anio,'Segundo',inicio,fin))
        rechaza(lambda: crear_torneo(cursor,usuario,'Fechas',anio,'Segundo',fin,inicio))
        rechaza(lambda: crear_torneo(cursor,{'rol':'planillero'},'Rol',anio,'Segundo',inicio,fin))
        rechaza(lambda: cambiar_etapa(cursor,usuario,identificador,'finalizado'))
        rechaza(lambda: cambiar_etapa(cursor,usuario,identificador,'en curso'))
        cursor.execute('SELECT id_equipo,id_facultad,ci_capitan FROM equipo WHERE id_equipo IN (SELECT id_equipo FROM equipo_jugador_torneo GROUP BY id_equipo HAVING COUNT(*)>=5) LIMIT 2')
        fuentes = cursor.fetchall()
        assert len(fuentes) == 2, 'Se necesitan dos planteles existentes para esta prueba.'
        for original, facultad, capitan in fuentes:
            cursor.execute('INSERT INTO equipo (nombre,id_torneo,id_facultad,ci_capitan) VALUES (%s,%s,%s,%s)', ('Equipo temporal',identificador,facultad,capitan))
            equipo = cursor.lastrowid
            cursor.execute('INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo) SELECT %s,ci_jugador,%s FROM equipo_jugador_torneo WHERE id_equipo=%s LIMIT 4',(equipo,identificador,original))
        rechaza(lambda: cambiar_etapa(cursor,usuario,identificador,'en curso'))
        for original, facultad, capitan in fuentes:
            cursor.execute('SELECT id_equipo FROM equipo WHERE id_torneo=%s AND ci_capitan=%s',(identificador,capitan))
            equipo = cursor.fetchone()[0]
            cursor.execute('INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo) SELECT %s,r.ci_jugador,%s FROM equipo_jugador_torneo r WHERE r.id_equipo=%s AND NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo n WHERE n.id_torneo=%s AND n.ci_jugador=r.ci_jugador) LIMIT 1',(equipo,identificador,original,identificador))
        cambiar_etapa(cursor,usuario,identificador,'en curso')
        cantidad += 1
        rechaza(lambda: cambiar_etapa(cursor,usuario,identificador,'inscripción'))
        rechaza(lambda: cambiar_etapa(cursor,{'rol':'planillero'},identificador,'finalizado'))
        # Simula un partido pendiente para comprobar el bloqueo sin crear partidos.
        simulado = MagicMock()
        simulado.fetchone.side_effect = [(1,),('en curso',),('en curso',),(1,)]
        rechaza(lambda: cambiar_etapa(simulado,usuario,identificador,'finalizado'))
        cambiar_etapa(cursor,usuario,identificador,'finalizado')
        cantidad += 1
        rechaza(lambda: cambiar_etapa(cursor,usuario,identificador,'en curso'))
        with patch('builtins.input', return_value='0'):
            menu_torneos(usuario)
        cantidad += 1
        conexion.rollback()
        cursor.execute('SELECT COUNT(*) FROM torneo')
        assert cursor.fetchone()[0] == antes
        cantidad += 1
        print(f'{cantidad} comprobaciones OK. Cambios de prueba revertidos.')
    finally:
        conexion.rollback()
        cursor.close()
        conexion.close()


if __name__ == '__main__':
    main()
