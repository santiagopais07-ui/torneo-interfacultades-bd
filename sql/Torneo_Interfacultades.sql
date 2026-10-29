CREATE DATABASE Torneo_Interfacultades CHARACTER SET utf8mb4;
USE Torneo_Interfacultades;
-- Creación de tablas
CREATE TABLE login (
    correo varchar(50) primary key,
    contraseña varchar(50) not null,
    rol varchar(20) not null,
    CHECK ( rol IN ('administrador', 'planillero') )
);
CREATE TABLE facultad (
    id_facultad int auto_increment primary key,
    nombre varchar(50) not null
);
CREATE TABLE jugador (
    ci int primary key,
    nombre varchar(50),
    apellido varchar(50) not null,
    email varchar(50) not null unique,
    fecha_nacimiento date,
    id_facultad int not null,
    tipo varchar(20) not null,
    CHECK ( tipo IN ('grado', 'posgrado', 'docente', 'funcionario') ),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad)
);
CREATE TABLE torneo (
    id_torneo int auto_increment primary key,
    nombre varchar(50) not null,
    anio int not null,
    semestre varchar(20) not null,
    fecha_inicio date,
    fecha_fin date,
    estado varchar(20) not null default 'inscripción',
    UNIQUE (anio, semestre),
    CHECK ( estado IN ('inscripción', 'en curso', 'finalizado') ),
    CHECK ( semestre IN ('Primero', 'Segundo') ),
    CHECK ( fecha_fin >= fecha_inicio )
);
CREATE TABLE equipo (
    id_equipo int auto_increment primary key,
    nombre varchar(50) not null,
    id_torneo int not null,
    id_facultad int not null,
    ci_capitan int not null,
    UNIQUE (id_equipo, id_torneo),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad),
    FOREIGN KEY (ci_capitan) REFERENCES jugador(ci)
);
CREATE TABLE equipo_jugador_torneo (
    id_equipo int,
    ci_jugador int,
    id_torneo int,
    numero_camiseta int,
    UNIQUE (ci_jugador, id_torneo),
    UNIQUE (id_equipo, ci_jugador),
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    FOREIGN KEY (id_equipo, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci)
);
CREATE TABLE complejo (
    id_complejo int auto_increment primary key,
    nombre varchar(50),
    direccion varchar(100) not null,
    departamento varchar(50)
);
CREATE TABLE cancha (
    nombre_cancha varchar(50),
    id_complejo int,
    superficie varchar(20),
    techada boolean default false,
    PRIMARY KEY (nombre_cancha, id_complejo),
    CHECK ( superficie IN ('sintético', 'parquet') ),
    FOREIGN KEY (id_complejo) REFERENCES complejo(id_complejo)
);
CREATE TABLE turno (
    id_turno int auto_increment primary key,
    hora_inicio time not null,
    hora_fin time not null,
    CHECK ( hora_inicio >= '18:00:00' AND hora_fin <= '23:00:00' ),
    CHECK ( TIME_TO_SEC(hora_fin) - TIME_TO_SEC(hora_inicio) = 3600 )
);
CREATE TABLE partido (
    id_partido int auto_increment unique,
    id_torneo int,
    numero_fecha int not null,
    id_equipo_local int not null,
    id_equipo_visitante int not null,
    dia date not null,
    id_turno int not null,
    nombre_cancha varchar(50) not null,
    id_complejo int not null,
    estado varchar(20) not null default 'programado',
    PRIMARY KEY (id_partido, id_torneo),
    CHECK ( estado IN ('programado', 'jugado', 'postergado', 'cancelado') ),
    CHECK ( id_equipo_local <> id_equipo_visitante ),
    CHECK ( numero_fecha >= 1 ),
    UNIQUE (dia, id_turno, nombre_cancha, id_complejo),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_equipo_local, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (id_equipo_visitante, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (id_turno) REFERENCES turno(id_turno),
    FOREIGN KEY (nombre_cancha, id_complejo) REFERENCES cancha(nombre_cancha, id_complejo)
);
CREATE TABLE planilla_partido (
    id_partido int,
    ci_jugador int,
    id_equipo int not null,
    PRIMARY KEY (id_partido, ci_jugador),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (id_equipo, ci_jugador) REFERENCES equipo_jugador_torneo(id_equipo, ci_jugador)
);
CREATE TABLE gol (
    id_gol int auto_increment primary key,
    id_partido int not null,
    ci_jugador int not null,
    minuto int,
    autogol boolean default false,
    CHECK ( minuto >= 0 ),
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido(id_partido, ci_jugador)
);
CREATE TABLE tarjeta (
    id_tarjeta int auto_increment primary key,
    id_partido int not null,
    ci_jugador int not null,
    minuto int,
    color varchar(20) not null,
    CHECK ( color IN ('amarilla', 'roja') ),
    CHECK ( minuto >= 0 ),
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido(id_partido, ci_jugador)
);
CREATE TABLE sancion_jugador (
    id_sancion int auto_increment primary key,
    ci_jugador int not null,
    id_torneo int not null,
    motivo varchar(50) not null,
    numero_fecha_inicio int not null,
    cantidad_fechas int not null,
    CHECK ( motivo IN ('roja', 'acumulación de amarillas', 'disciplinaria') ),
    CHECK ( cantidad_fechas >= 1 ),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo)
);
CREATE TABLE cambios (
    id_cambio int auto_increment primary key,
    fecha_cambio datetime not null default current_timestamp,
    descripcion_cambio varchar(100),
    id_partido int not null,
    correo_cambiante varchar(50) not null,
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (correo_cambiante) REFERENCES login(correo)
);

-- Datos mestros de la tabla turno (Regla 3)
INSERT INTO turno (hora_inicio, hora_fin) VALUES
    ('18:00:00', '19:00:00'),
    ('19:00:00', '20:00:00'),
    ('20:00:00', '21:00:00'),
    ('21:00:00', '22:00:00'),
    ('22:00:00', '23:00:00');

-- Inserciones a las tablas
INSERT INTO facultad (nombre) VALUES
    ('Artes y Arquitectura'),
    ('Ciencias Empresariales'),
    ('Derecho'),
    ('Ingeniería y Tecnologías'),
    ('Salud'),
    ('Educación y Humanidades');

INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
    (50000001, 'Martín', 'Roso', 'm.roso@correo.ucu.edu.uy', '2000-01-01', 1, 'grado'),
    (50000002, 'Lucía', 'Aguirre', 'l.aguirre@correo.ucu.edu.uy', '2001-09-10', 1, 'grado'),
    (50000003, 'Sol', 'Pereira', 's.pereira@correo.ucu.edu.uy', '2006-07-23', 1, 'grado'),
    (50000004, 'Tomas', 'Lopez', 't.lopez@correo.ucu.edu.uy', '2002-04-12', 1, 'grado'),
    (30000001, 'Valentina', 'Gómez', 'v.gomez@correo.ucu.edu.uy', '1998-11-30', 1, 'posgrado'),
    (50000006, 'Mateo', 'Silva', 'm.silva@correo.ucu.edu.uy', '2004-09-18', 1, 'grado'),
    (10000001, 'Carolina', 'Acosta', 'c.acosta@correo.ucu.edu.uy', '1988-05-02', 1, 'funcionario'),

    (50000008, 'Facundo', 'Barrios', 'f.barrios@correo.ucu.edu.uy', '2003-04-21', 2, 'grado'),
    (50000009, 'Agustina', 'López', 'a.lopez@correo.ucu.edu.uy', '2004-08-15', 2, 'grado'),
    (50000010, 'Bruno', 'Cabrera', 'b.cabrera@correo.ucu.edu.uy', '2005-06-03', 2, 'grado'),
    (50000011, 'Florencia', 'Núñez', 'f.nunez@correo.ucu.edu.uy', '2002-12-11', 2, 'grado'),
    (30000002, 'Emiliano', 'Suárez', 'e.suarez@correo.ucu.edu.uy', '1997-10-07', 2, 'posgrado'),
    (10000002, 'Rodrigo', 'Méndez', 'r.mendez@correo.ucu.edu.uy', '1981-03-19', 2, 'docente'),
    (50000012, 'Tomás', 'Ibarra', 't.ibarra@correo.ucu.edu.uy', '2005-11-28', 2, 'grado'),

    (50000013, 'Federico', 'Castro', 'f.castro@correo.ucu.edu.uy', '2003-02-08', 3, 'grado'),
    (50000014, 'Julieta', 'Martínez', 'j.martinez@correo.ucu.edu.uy', '2004-05-17', 3, 'grado'),
    (50000015, 'Gonzalo', 'Ramos', 'g.ramos@correo.ucu.edu.uy', '2002-09-23', 3, 'grado'),
    (50000016, 'Sofía', 'Benítez', 's.benitez@correo.ucu.edu.uy', '2005-12-01', 3, 'grado'),
    (50000017, 'Ignacio', 'Olivera', 'i.olivera@correo.ucu.edu.uy', '2003-10-14', 3, 'grado'),
    (10000003, 'Patricia', 'Vega', 'p.vega@correo.ucu.edu.uy', '1979-07-22', 3, 'docente'),
    (50000018, 'Leandro', 'Correa', 'l.correa@correo.ucu.edu.uy', '2006-01-30', 3, 'grado'),

    (50000019, 'Paula', 'Díaz', 'p.diaz@correo.ucu.edu.uy', '2004-04-05', 4, 'grado'),
    (50000020, 'Martina', 'Rojas', 'm.rojas@correo.ucu.edu.uy', '2003-11-19', 4, 'grado'),
    (50000021, 'Diego', 'Sosa', 'd.sosa@correo.ucu.edu.uy', '2002-06-27', 4, 'grado'),
    (30000003, 'Antonella', 'Giménez', 'a.gimenez@correo.ucu.edu.uy', '1999-08-09', 4, 'posgrado'),
    (50000022, 'Lucas', 'Morales', 'l.morales@correo.ucu.edu.uy', '2005-03-24', 4, 'grado'),
    (10000004, 'Andrés', 'Pintos', 'a.pintos@correo.ucu.edu.uy', '1985-09-12', 4, 'funcionario'),
    (50000023, 'Micaela', 'Ferreira', 'm.ferreira@correo.ucu.edu.uy', '2006-05-06', 4, 'grado'),

    (50000024, 'Gabriel', 'Cardozo', 'g.cardozo@correo.ucu.edu.uy', '2003-01-16', 5, 'grado'),
    (50000025, 'Rocío', 'Alonso', 'r.alonso@correo.ucu.edu.uy', '2004-10-02', 5, 'grado'),
    (50000026, 'Maximiliano', 'Da Silva', 'm.dasilva@correo.ucu.edu.uy', '2002-07-13', 5, 'grado'),
    (30000004, 'Natalia', 'Pereyra', 'n.pereyra@correo.ucu.edu.uy', '1996-04-29', 5, 'posgrado'),
    (50000027, 'Pablo', 'Domínguez', 'p.dominguez@correo.ucu.edu.uy', '2005-02-20', 5, 'grado'),
    (10000005, 'Silvia', 'Arias', 's.arias@correo.ucu.edu.uy', '1976-12-08', 5, 'docente'),
    (50000028, 'Franco', 'Maidana', 'f.maidana@correo.ucu.edu.uy', '2006-08-18', 5, 'grado'),

    (50000029, 'Ana', 'Romero', 'a.romero@correo.ucu.edu.uy', '2004-06-30', 6, 'grado'),
    (50000030, 'Sebastián', 'Lemos', 's.lemos@correo.ucu.edu.uy', '2003-03-10', 6, 'grado'),
    (50000031, 'Victoria', 'Texeira', 'v.texeira@correo.ucu.edu.uy', '2004-12-22', 6, 'grado'),
    (50000032, 'Ramiro', 'Bentancor', 'r.bentancor@correo.ucu.edu.uy', '2002-05-25', 6, 'grado'),
    (30000005, 'Belén', 'Cruz', 'b.cruz@correo.ucu.edu.uy', '1995-09-04', 6, 'posgrado'),
    (10000006, 'Hugo', 'Fagúndez', 'h.fagundez@correo.ucu.edu.uy', '1983-01-27', 6, 'funcionario'),
    (50000033, 'Delfina', 'Sánchez', 'd.sanchez@correo.ucu.edu.uy', '2005-07-15', 6, 'grado');

INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado) VALUES
    ('Torneo Interfacultades 2026-2', 2026, 'Segundo', '2026-08-06', '2026-11-28', 'inscripción');

INSERT INTO equipo (nombre, id_torneo, id_facultad, ci_capitan) VALUES
    ('Empresariales FC', 1, 1, 50000001),
    ('Ingeniería United', 1, 2, 50000008),
    ('Derecho Atlético', 1, 3, 50000013),
    ('Psicología FC', 1, 4, 50000019),
    ('Salud Deportivo', 1, 5, 50000024),
    ('Humanas Lovers', 1, 6, 50000029);

INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
    (1, 50000001, 1, 10), (1, 50000002, 1, 7), (1, 50000003, 1, 9), (1, 30000001, 1, 5),
    (1, 50000006, 1, 3), (1, 10000001, 1, 1), (1, 50000004, 1, 8),
    (2, 50000008, 1, 10), (2, 50000009, 1, 7), (2, 50000010, 1, 9), (2, 50000011, 1, 5),
    (2, 30000002, 1, 3), (2, 10000002, 1, 1), (2, 50000012, 1, 8),
    (3, 50000013, 1, 10), (3, 50000014, 1, 7), (3, 50000015, 1, 9), (3, 50000016, 1, 5),
    (3, 50000017, 1, 3), (3, 10000003, 1, 1), (3, 50000018, 1, 8),
    (4, 50000019, 1, 10), (4, 50000020, 1, 7), (4, 50000021, 1, 9), (4, 30000003, 1, 5),
    (4, 50000022, 1, 3), (4, 10000004, 1, 1), (4, 50000023, 1, 8),
    (5, 50000024, 1, 10), (5, 50000025, 1, 7), (5, 50000026, 1, 9), (5, 30000004, 1, 5),
    (5, 50000027, 1, 3), (5, 10000005, 1, 1), (5, 50000028, 1, 8),
    (6, 50000029, 1, 10), (6, 50000030, 1, 7), (6, 50000031, 1, 9), (6, 50000032, 1, 5),
    (6, 30000005, 1, 3), (6, 10000006, 1, 1), (6, 50000033, 1, 8);

UPDATE torneo SET estado = 'en curso' WHERE id_torneo = 1;

INSERT INTO complejo (nombre, direccion, departamento) VALUES
    ( 'Complejo Pocitos', 'Av. Brasil 2500', 'Montevideo'),
    ( 'Complejo Los Aromos', 'Camino Carrasco 4400', 'Montevideo'),
    ( 'Complejo Costa Azul', 'Rambla Costanera 100', 'Canelones');

INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES
    ('Cancha 001', 1, 'sintético', false),
    ('Cancha 002', 1, 'sintético', true),
    ('Cancha 001', 2, 'parquet', true),
    ('Cancha 002', 2, 'parquet', true),
    ('Cancha 001', 3, 'sintético', false);

INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante,
                     dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
    (1, 1, 1, 1, 6, '2026-10-06', 1, 'Cancha 001', 1, 'jugado'),
    (2, 1, 1, 2, 5, '2026-10-06', 2, 'Cancha 001', 1, 'jugado'),
    (3, 1, 1, 3, 4, '2026-10-06', 1, 'Cancha 001', 2, 'jugado'),
    (4, 1, 2, 1, 5, '2026-10-13', 3, 'Cancha 001', 1, 'jugado'),
    (5, 1, 2, 6, 4, '2026-10-13', 1, 'Cancha 002', 2, 'jugado'),
    (6, 1, 2, 2, 3, '2026-10-13', 4, 'Cancha 001', 3, 'jugado'),
    (7, 1, 3, 1, 4, '2026-10-20', 2, 'Cancha 002', 1, 'jugado'),
    (8, 1, 3, 5, 3, '2026-10-20', 1, 'Cancha 001', 2, 'jugado'),
    (9, 1, 3, 6, 2, '2026-10-20', 5, 'Cancha 001', 1, 'jugado'),
    (10, 1, 4, 1, 3, '2026-10-27', 1, 'Cancha 001', 1, 'programado'),
    (11, 1, 4, 4, 2, '2026-10-27', 2, 'Cancha 001', 1, 'postergado'),
    (12, 1, 4, 5, 6, '2026-10-27', 1, 'Cancha 002', 1, 'cancelado');

INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) VALUES
    (50000014, 1, 'roja', 3, 1),
    (30000001, 1, 'roja', 4, 1),
    (50000031, 1, 'acumulación de amarillas', 4, 1),
    (50000021, 1, 'disciplinaria', 3, 2);

INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo)
SELECT partido.id_partido, equipo_jugador_torneo.ci_jugador, equipo_jugador_torneo.id_equipo
FROM partido
JOIN equipo_jugador_torneo ON equipo_jugador_torneo.id_equipo IN (partido.id_equipo_local, partido.id_equipo_visitante)
    WHERE partido.estado = 'jugado'
        AND equipo_jugador_torneo.ci_jugador NOT IN (50000004, 50000012, 50000018, 50000023, 50000028, 50000033)
        AND NOT EXISTS (
            SELECT 1
            FROM sancion_jugador
            WHERE sancion_jugador.ci_jugador = equipo_jugador_torneo.ci_jugador
                AND sancion_jugador.id_torneo = partido.id_torneo
                AND partido.numero_fecha BETWEEN sancion_jugador.numero_fecha_inicio
                                            AND sancion_jugador.numero_fecha_inicio + sancion_jugador.cantidad_fechas - 1
  );
SELECT COUNT(*) FROM planilla_partido; #Verificar que hay 106 filas.

INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES
    (1, 50000001, 8, false),
    (1, 50000001, 22, false),
    (1, 50000003, 35, false),
    (1, 50000030, 15, false),
    (2, 50000008, 10, false),
    (2, 50000011, 38, false),
    (2, 50000024, 20, false),
    (2, 30000004, 41, false),
    (3, 50000015, 27, false),
    (4, 50000002, 12, false),
    (4, 50000001, 30, false),
    (4, 50000025, 44, false),
    (5, 50000029, 18, false),
    (5, 30000003, 33, false),
    (6, 50000008, 5, false),
    (6, 50000008, 19, false),
    (6, 50000009, 25, false),
    (6, 30000002, 40, false),
    (6, 50000013, 16, false),
    (6, 50000010, 31, true),
    (7, 30000001, 14, false),
    (7, 50000019, 22, false),
    (7, 50000020, 37, false),
    (8, 50000024, 9, false),
    (8, 50000026, 28, false),
    (9, 50000032, 33, false),
    (9, 50000008, 11, false),
    (9, 50000011, 23, false),
    (9, 50000008, 39, false);

INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES
    (1, 50000031, 12, 'amarilla'),
    (1, 50000006, 30, 'amarilla'),
    (2, 50000026, 25, 'amarilla'),
    (3, 50000020, 18, 'amarilla'),
    (3, 50000016, 33, 'amarilla'),
    (4, 30000004, 36, 'amarilla'),
    (5, 50000031, 20, 'amarilla'),
    (5, 50000019, 29, 'amarilla'),
    (6, 50000014, 34, 'roja'),
    (6, 50000011, 8, 'amarilla'),
    (7, 30000003, 27, 'amarilla'),
    (7, 30000001, 41, 'roja'),
    (8, 50000027, 15, 'amarilla'),
    (9, 50000031, 30, 'amarilla'),
    (9, 30000002, 36, 'amarilla');

INSERT INTO login (correo, contraseña, rol) VALUES
    ('admin@correo.ucu.edu.uy', 'admin123', 'administrador'),
    ('planillero@correo.ucu.edu.uy', 'planillero123', 'planillero');

INSERT INTO cambios (fecha_cambio, descripcion_cambio, id_partido, correo_cambiante) VALUES
    ('2026-10-21 10:15:00', 'Corrección del minuto de un gol (de 38 a 39)', 9, 'planillero@correo.ucu.edu.uy');

-- Creación de usuarios
CREATE USER IF NOT EXISTS 'admin_torneo'@'%' IDENTIFIED BY 'usuario1';
CREATE USER IF NOT EXISTS 'planillero_torneo'@'%' IDENTIFIED BY 'usuario2';

-- Permisos
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.facultad TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.jugador  TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.torneo   TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.equipo   TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.equipo_jugador_torneo TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.complejo TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.cancha   TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.turno    TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.planilla_partido TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.gol  TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.tarjeta  TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.sancion_jugador  TO 'admin_torneo'@'%';

GRANT SELECT, INSERT, UPDATE ON Torneo_Interfacultades.partido TO 'admin_torneo'@'%';
GRANT SELECT, INSERT, UPDATE ON Torneo_Interfacultades.login TO 'admin_torneo'@'%';

GRANT SELECT, INSERT ON Torneo_Interfacultades.cambios TO 'admin_torneo'@'%';

GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.planilla_partido TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.gol TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.tarjeta TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON Torneo_Interfacultades.sancion_jugador TO 'planillero_torneo'@'%';

GRANT SELECT ON Torneo_Interfacultades.partido TO 'planillero_torneo'@'%';
GRANT UPDATE (estado) ON Torneo_Interfacultades.partido TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT ON Torneo_Interfacultades.cambios TO 'planillero_torneo'@'%';

GRANT SELECT ON Torneo_Interfacultades.torneo   TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.equipo   TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.equipo_jugador_torneo TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.jugador  TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.turno    TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.cancha   TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.complejo TO 'planillero_torneo'@'%';
GRANT SELECT ON Torneo_Interfacultades.facultad TO 'planillero_torneo'@'%';

