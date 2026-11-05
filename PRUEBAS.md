# Revisión funcional — 5 de noviembre de 2026

Entorno: Docker Desktop, imagen Python 3.14-slim y MySQL 8.0. SQL inicial cargado con utf8mb4; zona horaria America/Montevideo.

## Resultado

- probar_reglas: 60 comprobaciones correctas.
- probar_partidos: 30 comprobaciones correctas.
- probar_planillas: 40 comprobaciones correctas; incluye operaciones con la cuenta MySQL real del planillero.
- probar_torneos: 16 comprobaciones correctas.
- probar_usuarios: 7 comprobaciones correctas.
- probar_reportes: 12 comparaciones exactas correctas sobre los datos iniciales.
- probar_integracion: 12 grupos de recorridos correctos.
- probar_menu_completo: navegación por los nueve submenús administrativos; los doce reportes desde consola; ocho operaciones administrativas rechazadas por MySQL al planillero; alta y baja con commit real y comprobación desde otra conexión.
- Persistencia: reinicio del servicio db; las huellas de todas las filas antes y después coincidieron, incluidas las cuentas existentes.
- Hora: Python y MySQL coincidieron en la hora de Montevideo.

## Áreas cubiertas

Creación, modificación, eliminación, consulta y cancelación de bajas de jugadores, complejos, canchas, árbitros y asistencias. Creación de equipo con capitán, incorporación y baja de integrantes, rechazo de duplicados y de facultad distinta, camiseta, cambio de capitán, consulta del plantel y eliminación del equipo conservando las fichas de jugadores.

Programación y reprogramación de partidos, conflictos de cancha y árbitro, rivales y jornadas, etapas, min/max del plantel, límites de docentes/funcionarios, protección de partidos jugados y con planillas. Participantes, goles, autogoles, tarjetas, suspensiones automáticas, disciplinarias, correcciones, límite de 48 horas y auditoría de correcciones.

Autenticación con hash temporal válido, contraseña incorrecta, entrada que intenta inyección SQL, creación de cuentas faltantes y preservación de cuentas existentes. El recorrido del menú principal sustituye la autenticación por un usuario de prueba; la autenticación real se verifica por separado sin conocer ni cambiar contraseñas personales.

## Conservación de datos

Las pruebas transaccionales revierten las escrituras. La prueba de menú guarda y elimina un jugador temporal para verificar commit. Se compararon todas las filas originales mediante huellas, sin publicar hashes de contraseñas ni otros datos. Los contadores AUTO_INCREMENT pueden avanzar y dejar huecos, aunque los registros temporales se reviertan.

## Alcance

La revisión cubre los recorridos descritos y no es una garantía de ausencia absoluta de errores. No es una prueba de carga ni de concurrencia simultánea de múltiples usuarios. No cubre todos los fallos posibles de red, disco, hardware o instalaciones de terceros. El despliegue se comprobó en esta laptop; falta que otra persona repita el instructivo desde su equipo y revisar el informe académico final.

No se publicaron cambios en GitHub durante esta revisión.
