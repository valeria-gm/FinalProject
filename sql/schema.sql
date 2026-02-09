-- Crear base de datos
CREATE DATABASE IF NOT EXISTS market;
USE market;

-- Tabla TIPO_CLIENTE (define categorías de clientes)
CREATE TABLE tipo_cliente (
    id_tipo_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nombre_tipo VARCHAR(100) NOT NULL UNIQUE,
    descuento DECIMAL(5,2) NOT NULL DEFAULT 0.00 CHECK (descuento BETWEEN 0 AND 100)-- porcentaje (ej. 10.00 = 10%)
);

-- Tabla GRUPO 
CREATE TABLE grupo (
    id_grupo INT AUTO_INCREMENT PRIMARY KEY,
    clave_grupo VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    id_tipo_cliente INT,
    FOREIGN KEY (id_tipo_cliente) REFERENCES tipo_cliente(id_tipo_cliente),
    UNIQUE KEY (id_grupo, id_tipo_cliente)
);


-- Tabla CLIENTE
CREATE TABLE cliente (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nombre_cliente VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    correo VARCHAR(100),
    id_grupo INT NOT NULL,
    FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo)
);

-- Tabla PRODUCTO (sin precio_base)
CREATE TABLE producto (
    id_producto INT AUTO_INCREMENT PRIMARY KEY,
    nombre_producto VARCHAR(250) NOT NULL,
    unidad_producto VARCHAR(50) NOT NULL,
    stock DECIMAL(10,2) NOT NULL,
    es_especial BOOLEAN DEFAULT FALSE
);

-- Tabla PRECIO_POR_GRUPO (precios específicos por Grupo de cliente)
CREATE TABLE precio_por_grupo (
    id_precio_grupo INT AUTO_INCREMENT PRIMARY KEY,
    id_grupo INT NOT NULL,
    id_producto INT NOT NULL,
    precio_base DECIMAL(10,2) NOT NULL,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_grupo) REFERENCES grupo(id_grupo),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto),
    UNIQUE KEY (id_grupo, id_producto) -- Cada combinación grupo-producto es única
);

-- Tabla FACTURA
CREATE TABLE factura (
    id_factura INT AUTO_INCREMENT PRIMARY KEY,
    fecha_factura DATE NOT NULL,
    id_cliente INT NOT NULL,
    folio_numero INT NOT NULL UNIQUE,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente),
    INDEX idx_folio (folio_numero)
);

-- Tabla SECCION_FACTURA
CREATE TABLE seccion_factura (
    id_seccion INT AUTO_INCREMENT PRIMARY KEY,
    id_factura INT NOT NULL,
    nombre_seccion VARCHAR(100) NOT NULL,
    orden_seccion INT NOT NULL DEFAULT 0,
    FOREIGN KEY (id_factura) REFERENCES factura(id_factura) ON DELETE CASCADE,
    INDEX idx_factura_seccion (id_factura)
);

-- Tabla DETALLE_FACTURA
CREATE TABLE detalle_factura (
    id_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_factura INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad_factura DECIMAL(10,2) NOT NULL,
    precio_unitario_venta DECIMAL(10,2) NOT NULL,
    id_seccion INT NULL,
    FOREIGN KEY (id_factura) REFERENCES factura(id_factura),
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto),
    FOREIGN KEY (id_seccion) REFERENCES seccion_factura(id_seccion) ON DELETE SET NULL
);

-- Tabla COMPRA
CREATE TABLE compra (
    id_compra INT AUTO_INCREMENT PRIMARY KEY,
    fecha_compra DATE NOT NULL,
    id_producto INT NOT NULL,
    cantidad_compra DECIMAL(10,2) NOT NULL,
    precio_unitario_compra DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (id_producto) REFERENCES producto(id_producto)
);

-- Tabla de usuarios
CREATE TABLE usuarios_sistema (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    rol ENUM('admin', 'usuario') DEFAULT 'usuario',
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP NULL,
    intentos_fallidos INT DEFAULT 0,
    bloqueado_hasta TIMESTAMP NULL
);

-- Tabla DEUDA
CREATE TABLE deuda (
    id_deuda INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_factura INT NOT NULL UNIQUE,
    monto DECIMAL(10,2) NOT NULL CHECK (monto > 0),
    monto_pagado DECIMAL(10,2) DEFAULT 0.00,
    fecha_generada DATE NOT NULL,
    pagado BOOLEAN DEFAULT FALSE,
    fecha_pago DATE NULL,
    descripcion VARCHAR(255),
    metodo_pago VARCHAR(50),
    referencia_pago VARCHAR(100),
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente),
    FOREIGN KEY (id_factura) REFERENCES factura(id_factura),
    CHECK (monto_pagado <= monto),
    CHECK (fecha_pago IS NULL OR pagado = TRUE)
);

-- Tabla de logs
CREATE TABLE log_accesos (
    id_log INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NULL,
    username_intento VARCHAR(50),
    ip_address VARCHAR(45) DEFAULT 'localhost',
    exito BOOLEAN,
    fecha_intento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detalle VARCHAR(255),
    FOREIGN KEY (id_usuario) REFERENCES usuarios_sistema(id_usuario) ON DELETE SET NULL
);

-- Tabla FACTURA_METADATA
CREATE TABLE factura_metadata (
    id_factura INT PRIMARY KEY,
    usa_secciones BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_factura) REFERENCES factura(id_factura) ON DELETE CASCADE
);

-- Tabla para secuencia de folios
CREATE TABLE folio_sequence (
    id INT PRIMARY KEY DEFAULT 1,
    next_val INT NOT NULL DEFAULT 1
);

-- Tabla ORDENES_GUARDADAS
CREATE TABLE ordenes_guardadas (
    id_orden INT AUTO_INCREMENT PRIMARY KEY,
    folio_numero INT NOT NULL UNIQUE,
    id_cliente INT NOT NULL,
    usuario_creador VARCHAR(50) NOT NULL,
    datos_carrito JSON NOT NULL,
    total_estimado DECIMAL(10,2) NOT NULL,
    estado ENUM('guardada', 'registrada') DEFAULT 'guardada',
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente),
    FOREIGN KEY (usuario_creador) REFERENCES usuarios_sistema(username),
    INDEX idx_folio (folio_numero),
    INDEX idx_estado (estado),
    INDEX idx_usuario (usuario_creador),
    INDEX idx_activo (activo)
);

-- Índices
CREATE INDEX idx_username ON usuarios_sistema(username);
CREATE INDEX idx_activo ON usuarios_sistema(activo);
CREATE INDEX idx_detalle_seccion ON detalle_factura(id_seccion);

-- Inicializar secuencia de folios
INSERT INTO folio_sequence (id, next_val) VALUES (1, 1);