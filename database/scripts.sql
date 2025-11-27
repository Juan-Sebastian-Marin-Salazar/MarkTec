CREATE DATABASE marketec;
USE marketec;

SET @OLD_SQL_MODE=@@SQL_MODE;
SET SQL_MODE='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- ===== ROLES =====
CREATE TABLE IF NOT EXISTS roles (
  idRoles INT AUTO_INCREMENT PRIMARY KEY,
  nombre_rol VARCHAR(50) NOT NULL UNIQUE,
  tipo_rol VARCHAR(20) NOT NULL DEFAULT 'regular',
  descripcion TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== USUARIOS =====
CREATE TABLE IF NOT EXISTS usuarios (
  idUsuarios INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(150) NOT NULL,
  correo VARCHAR(255) NOT NULL UNIQUE,
  clave_hash VARCHAR(255) NOT NULL,
  telefono VARCHAR(30),
  universidad VARCHAR(255) DEFAULT 'Tecnologico de Mexicali',
  matricula VARCHAR(100),
  es_vendedor_verificado TINYINT(1) NOT NULL DEFAULT 0,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  eliminado_en TIMESTAMP NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_usuarios_correo ON usuarios(correo);

-- ===== USUARIOS_ROLES =====
CREATE TABLE IF NOT EXISTS usuarios_roles (
  id_usuario INT NOT NULL,
  id_rol INT NOT NULL,
  asignado_por INT NULL,
  asignado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_usuario, id_rol),
  CONSTRAINT fk_ur_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(idUsuarios) ON DELETE CASCADE,
  CONSTRAINT fk_ur_rol FOREIGN KEY (id_rol) REFERENCES roles(idRoles) ON DELETE CASCADE,
  CONSTRAINT fk_ur_asignado_por FOREIGN KEY (asignado_por) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Trigger para evitar múltiples roles del tipo sistema
DROP TRIGGER IF EXISTS trg_usuarios_roles_prevenir_multiple_sistema;
DELIMITER $$
CREATE TRIGGER trg_usuarios_roles_prevenir_multiple_sistema
BEFORE INSERT ON usuarios_roles
FOR EACH ROW
BEGIN
  DECLARE v_tipo VARCHAR(20);
  DECLARE v_contador INT DEFAULT 0;
  SELECT tipo_rol INTO v_tipo FROM roles WHERE idRoles = NEW.id_rol LIMIT 1;
  IF v_tipo = 'system' THEN
    SELECT COUNT(*) INTO v_contador
    FROM usuarios_roles ur
    JOIN roles r ON ur.id_rol = r.idRoles
    WHERE ur.id_usuario = NEW.id_usuario AND r.tipo_rol = 'system';
    IF v_contador > 0 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un usuario ya tiene un rol de tipo system. Solo se permite uno.';
    END IF;
  END IF;
END$$
DELIMITER ;

-- ===== PUBLICACIONES =====
CREATE TABLE IF NOT EXISTS publicaciones (
  idPublicaciones INT AUTO_INCREMENT PRIMARY KEY,
  id_vendedor INT NOT NULL,
  titulo VARCHAR(255) NOT NULL,
  descripcion TEXT,
  precio DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (precio >= 0),
  moneda VARCHAR(10) DEFAULT 'MXN',
  existencias INT DEFAULT 1,
  condicion_producto VARCHAR(30) DEFAULT 'usado',
  estado_publicacion VARCHAR(30) DEFAULT 'borrador',
  metadatos JSON DEFAULT (JSON_OBJECT()),
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  eliminado_en TIMESTAMP NULL DEFAULT NULL,
  CONSTRAINT fk_publicaciones_vendedor FOREIGN KEY (id_vendedor) REFERENCES usuarios(idUsuarios) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_publicaciones_vendedor ON publicaciones(id_vendedor);
CREATE INDEX idx_publicaciones_estado ON publicaciones(estado_publicacion);
ALTER TABLE publicaciones ADD FULLTEXT INDEX ft_publicaciones_titulo_descripcion (titulo, descripcion);

-- ===== IMAGENES_PUBLICACION =====
CREATE TABLE IF NOT EXISTS imagenes_publicacion (
  idImagenesPublicacion INT AUTO_INCREMENT PRIMARY KEY,
  id_publicacion INT NOT NULL,
  url VARCHAR(1000) NOT NULL,
  texto_alternativo VARCHAR(255),
  orden INT DEFAULT 0,
  CONSTRAINT fk_imagenes_publicacion FOREIGN KEY (id_publicacion) REFERENCES publicaciones(idPublicaciones) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_imagenes_publicacion ON imagenes_publicacion(id_publicacion);

-- ===== TRANSACCIONES =====
CREATE TABLE transaccion (
  id_transaccion int NOT NULL AUTO_INCREMENT,
  id_vendedor int NOT NULL,
  id_comprador int NOT NULL,
  id_publicacion int NOT NULL,
  estado varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'en progreso',
  fecha_creacion timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_transaccion),
  KEY fk_vendedor (id_vendedor),
  KEY fk_comprador (id_comprador),
  KEY fk_publicacion (id_publicacion),
  CONSTRAINT fk_comprador FOREIGN KEY (id_comprador) REFERENCES usuarios (idUsuarios) ON DELETE RESTRICT,
  CONSTRAINT fk_publicacion FOREIGN KEY (id_publicacion) REFERENCES publicaciones (idPublicaciones) ON DELETE RESTRICT,
  CONSTRAINT fk_vendedor FOREIGN KEY (id_vendedor) REFERENCES usuarios (idUsuarios) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== CATEGORIAS =====
CREATE TABLE IF NOT EXISTS categorias (
  idCategorias INT AUTO_INCREMENT PRIMARY KEY,
  nombre_categoria VARCHAR(150) NOT NULL,
  id_creador INT NULL,
  esta_activa TINYINT(1) DEFAULT 1,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_etiquetas_creador FOREIGN KEY (id_creador) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== PUBLICACIONES_CATEGORIAS =====
CREATE TABLE IF NOT EXISTS publicaciones_categoria (
  id_publicacion INT NOT NULL,
  id_categoria INT NOT NULL,
  PRIMARY KEY (id_publicacion, id_categoria),
  CONSTRAINT fk_pe_publicacion FOREIGN KEY (id_publicacion) REFERENCES publicaciones(idPublicaciones) ON DELETE CASCADE,
  CONSTRAINT fk_pe_categoria FOREIGN KEY (id_categoria) REFERENCES categorias(idCategorias) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- ===== ETIQUETAS =====
-- CREATE TABLE IF NOT EXISTS etiquetas (
--   idEtiquetas INT AUTO_INCREMENT PRIMARY KEY,
--   nombre_etiqueta VARCHAR(150) NOT NULL,
--   slug VARCHAR(150) NOT NULL,
--   id_creador INT NULL,
--   esta_activa TINYINT(1) DEFAULT 1,
--   creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
--   UNIQUE KEY ux_etiquetas_slug (slug),
--   CONSTRAINT fk_etiquetas_creador FOREIGN KEY (id_creador) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- ===== PUBLICACIONES_ETIQUETAS =====
-- CREATE TABLE IF NOT EXISTS publicaciones_etiquetas (
--   id_publicacion INT NOT NULL,
--   id_etiqueta INT NOT NULL,
--   PRIMARY KEY (id_publicacion, id_etiqueta),
--   CONSTRAINT fk_pe_publicacion FOREIGN KEY (id_publicacion) REFERENCES publicaciones(idPublicaciones) ON DELETE CASCADE,
--   CONSTRAINT fk_pe_etiqueta FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(idEtiquetas) ON DELETE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== CONVERSACIONES =====
CREATE TABLE IF NOT EXISTS conversaciones (
  idConversaciones INT AUTO_INCREMENT PRIMARY KEY,
  id_producto INT NULL,
  id_comprador INT NULL,
  id_vendedor INT NULL,
  efimera TINYINT(1) DEFAULT 1,
  expira_en TIMESTAMP NULL DEFAULT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_mensaje_en TIMESTAMP NULL DEFAULT NULL,
  CONSTRAINT fk_conversaciones_producto FOREIGN KEY (id_producto) REFERENCES publicaciones(idPublicaciones) ON DELETE SET NULL,
  CONSTRAINT fk_conversaciones_comprador FOREIGN KEY (id_comprador) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL,
  CONSTRAINT fk_conversaciones_vendedor FOREIGN KEY (id_vendedor) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_conversaciones_expira_en ON conversaciones(expira_en);

-- ===== MENSAJES_CONVERSACION =====
CREATE TABLE IF NOT EXISTS mensajes_conversacion (
  idMensajesConversacion INT AUTO_INCREMENT PRIMARY KEY,
  id_conversacion INT NOT NULL,
  id_remitente INT NULL,
  mensaje TEXT,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  eliminado TINYINT(1) DEFAULT 0,
  CONSTRAINT fk_mensajes_conversacion_conv FOREIGN KEY (id_conversacion) REFERENCES conversaciones(idConversaciones) ON DELETE CASCADE,
  CONSTRAINT fk_mensajes_conversacion_remitente FOREIGN KEY (id_remitente) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== TICKETS_SOPORTE =====
CREATE TABLE IF NOT EXISTS tickets_soporte (
  idTicketsSoporte INT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NULL,
  asignado_a INT NULL,
  asunto VARCHAR(255) NOT NULL,
  estado_ticket VARCHAR(30) DEFAULT 'abierto',
  prioridad VARCHAR(20) DEFAULT 'normal',
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_tickets_soporte_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL,
  CONSTRAINT fk_tickets_soporte_asignado FOREIGN KEY (asignado_a) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== MENSAJES_SOPORTE =====
CREATE TABLE IF NOT EXISTS mensajes_soporte (
  idMensajesSoporte INT AUTO_INCREMENT PRIMARY KEY,
  id_ticket INT NOT NULL,
  id_remitente INT NULL,
  mensaje TEXT NOT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_mensajes_soporte_ticket FOREIGN KEY (id_ticket) REFERENCES tickets_soporte(idTicketsSoporte) ON DELETE CASCADE,
  CONSTRAINT fk_mensajes_soporte_remitente FOREIGN KEY (id_remitente) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== REGISTROS_AUDITORIA =====
CREATE TABLE IF NOT EXISTS registros_auditoria (
  idRegistrosAuditoria INT AUTO_INCREMENT PRIMARY KEY,
  id_actor INT NULL,
  accion VARCHAR(150) NOT NULL,
  tipo_objetivo VARCHAR(50),
  id_objetivo INT,
  detalles JSON,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_auditoria_actor FOREIGN KEY (id_actor) REFERENCES usuarios(idUsuarios) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== PERMISOS =====
CREATE TABLE IF NOT EXISTS permisos (
  idPermisos INT AUTO_INCREMENT PRIMARY KEY,
  nombre_permiso VARCHAR(150) NOT NULL UNIQUE,
  descripcion TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS roles_permisos (
  id_rol INT NOT NULL,
  id_permiso INT NOT NULL,
  PRIMARY KEY (id_rol, id_permiso),
  CONSTRAINT fk_roles_permisos_rol FOREIGN KEY (id_rol) REFERENCES roles(idRoles) ON DELETE CASCADE,
  CONSTRAINT fk_roles_permisos_permiso FOREIGN KEY (id_permiso) REFERENCES permisos(idPermisos) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== SEED DATA =====
INSERT INTO roles (nombre_rol, tipo_rol, descripcion) VALUES
('administrador','system','Administrador con todos los permisos'),
('moderador','system','Modera y revisa contenido'),
('soporte','system','Atiende tickets y verifica vendedores'),
('vendedor','regular','Usuario que publica productos'),
('comprador','regular','Usuario que compra')
ON DUPLICATE KEY UPDATE nombre_rol = VALUES(nombre_rol);

-- INSERT INTO etiquetas (nombre_etiqueta, slug, id_creador, esta_activa) VALUES
-- ('Libros','libros', NULL, 1),
-- ('Muebles','muebles', NULL, 1),
-- ('Ropa','ropa', NULL, 1),
-- ('Cursos / Clases','cursos', NULL, 1),
-- ('Electronica','electronica', NULL, 1)
-- ON DUPLICATE KEY UPDATE nombre_etiqueta = VALUES(nombre_etiqueta);

INSERT INTO categorias (nombre_categoria, id_creador, esta_activa) VALUES ('Alimentos', NULL, 1);
INSERT INTO categorias (nombre_categoria, id_creador, esta_activa) VALUES ('Productos', NULL, 1);
INSERT INTO categorias (nombre_categoria, id_creador, esta_activa) VALUES ('Servicios', NULL, 1);

SET SQL_MODE=@OLD_SQL_MODE;