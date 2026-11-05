# Torneo Interfacultades

Aplicación de consola en Python y MySQL, sin ORM. Incluye administración de jugadores, equipos y planteles, infraestructura, árbitros, espectadores, partidos, sanciones y ediciones; carga de planillas, goles, tarjetas y reportes.

## Ejecutar con Docker Desktop

Abrir Docker Desktop y esperar a que esté funcionando. Desde la carpeta del proyecto:

```powershell
docker compose build
docker compose up -d db
docker compose run --rm app
```

El primer arranque descarga las imágenes y crea una base independiente con los datos de `sql/Torneo_Interfacultades.sql`. La aplicación espera a que MySQL esté disponible. No utiliza ni modifica el MySQL local de Windows y no publica su puerto.

La primera vez, el programa solicita elegir y confirmar una contraseña de al menos ocho caracteres para cada cuenta que falte:

- `admin@correo.ucu.edu.uy`: administrador.
- `planillero@correo.ucu.edu.uy`: planillero.

Al escribir las contraseñas no se muestran caracteres. Las contraseñas se almacenan como hash. Si las cuentas existen, no se vuelven a crear ni se cambia su contraseña.

Para volver a entrar:

```powershell
docker compose run --rm app
```

Para detener MySQL conservando los datos:

```powershell
docker compose down
```

Los datos se conservan en el volumen `datos_mysql`. El SQL inicial solo se carga cuando ese volumen está vacío; modificar el archivo no actualiza automáticamente una base existente. No usar `docker compose down -v` si se quieren conservar los datos: esa opción elimina el volumen de esta instalación.

Las claves de conexión incluidas en Compose son de demostración para esta instalación local. Son distintas de las contraseñas personales elegidas para iniciar sesión. No usar esta configuración como despliegue público.

Se usa MySQL 8.0 para mantener compatibilidad con las claves foráneas del esquema. La aplicación y MySQL usan America/Montevideo para las comprobaciones de horarios.

## Ejecutar sin Docker

Requiere Python 3.14 y MySQL compatible. Instalar las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Cargar `sql/Torneo_Interfacultades.sql` con una cuenta administradora de MySQL. **Ese archivo elimina y recrea la base Torneo_Interfacultades; no ejecutarlo sobre una instalación cuyos datos se quieran conservar.**

Crear `.env` en la carpeta principal con DB_HOST, DB_PORT, DB_NAME, DB_ADMIN_USER, DB_ADMIN_PASSWORD, DB_PLANILLERO_USER y DB_PLANILLERO_PASSWORD, según la instalación. El archivo debe permanecer fuera de GitHub.

```powershell
python -m src.main
```

## Organización

- `src/main.py`: inicio de sesión y menú por rol.
- `src/conexion.py`: conexión directa a MySQL.
- `src/reglas.py`: validaciones del negocio.
- Los demás módulos de `src` implementan cada área de gestión.
- `sql/Torneo_Interfacultades.sql`: esquema, datos iniciales y permisos.

Los usuarios de MySQL controlan los permisos de conexión. Las cuentas de la tabla login identifican a las personas que ingresan al programa. Las operaciones que modifican varios registros se guardan juntas con commit o se revierten con rollback si fallan.

## Comprobaciones automatizadas

Con Docker Desktop abierto y la base iniciada, ejecutar desde la carpeta del proyecto:

```powershell
docker compose run --rm -T app python -m src.probar_integracion
docker compose run --rm -T app python -m src.probar_menu_completo
```

Las pruebas de integración usan datos temporales y revierten sus transacciones. La prueba de menú comprueba además un alta y una baja reales de un jugador temporal, y verifica al terminar que todas las filas originales se conservan. No ejecutar estas pruebas mientras otra persona edita simultáneamente esa misma base.

También están disponibles los módulos probar_reglas, probar_partidos, probar_planillas, probar_torneos, probar_usuarios y probar_reportes. Algunos requieren los datos iniciales: probar_reportes compara resultados exactos de la edición de ejemplo y probar_planillas necesita un partido programado sin planilla. Los huecos en los identificadores automáticos después de probar son normales y no representan registros guardados.
