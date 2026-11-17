-- EnerControl - Iteración #1 - Esquema MySQL 8.x
-- Crear la base de datos (una vez):
--   CREATE DATABASE enercontrol CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- La aplicación ejecuta este script automáticamente (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(120) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    usuario VARCHAR(40) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('ADMINISTRADOR','TECNICO_IOT','ANALISTA_ENERGETICO') NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuarios_correo UNIQUE (correo),
    CONSTRAINT uq_usuarios_usuario UNIQUE (usuario)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS negocios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    tarifa_kwh DECIMAL(12,2) NOT NULL,
    responsable VARCHAR(120) NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_negocios_nombre UNIQUE (nombre),
    CONSTRAINT ck_negocios_tarifa CHECK (tarifa_kwh > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    ubicacion VARCHAR(120) NOT NULL,
    potencia_w DECIMAL(12,2) NOT NULL,
    negocio_id INT NOT NULL,
    estado ENUM('activo','inactivo') NOT NULL DEFAULT 'activo',
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_equipos_negocio_nombre UNIQUE (negocio_id, nombre),
    CONSTRAINT ck_equipos_potencia CHECK (potencia_w > 0),
    CONSTRAINT fk_equipos_negocio FOREIGN KEY (negocio_id)
        REFERENCES negocios (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Un equipo puede tener varios sensores; un sensor pertenece a un solo equipo (o a ninguno).
CREATE TABLE IF NOT EXISTS sensores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(40) NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    fecha_instalacion DATE NOT NULL,
    equipo_id INT NULL,
    estado ENUM('activo','inactivo','sin_conexion') NOT NULL DEFAULT 'inactivo',
    simulado TINYINT(1) NOT NULL DEFAULT 0,
    ultima_conexion DATETIME NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sensores_codigo UNIQUE (codigo),
    CONSTRAINT fk_sensores_equipo FOREIGN KEY (equipo_id)
        REFERENCES equipos (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Códigos temporales (hash) para recuperación de contraseña.
CREATE TABLE IF NOT EXISTS recuperaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    codigo_hash VARCHAR(255) NOT NULL,
    expira_en DATETIME NOT NULL,
    intentos TINYINT NOT NULL DEFAULT 0,
    usado TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_recuperaciones_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- [Iteración #2 - PENDIENTE] lecturas (sensor_id, marca_tiempo, voltaje, corriente, potencia_w, energia_kwh)
-- [Iteración #3 - PENDIENTE] umbrales y alertas (equipo_id, tipo, valor, estado, notificada_en)
