import mysql.connector
from mysql.connector import errorcode

# 1. Configuración de la Conexión (¡Tu usuario y contraseña están aquí!)
db_config = {
    'host': 'localhost',
    'user': 'root',    # <-- Tu usuario de MySQL Workbench
    'password': 'elferny23', # <-- Tu contraseña (AJÚSTALA si es diferente a 'elferny23')
}

# 2. Script SQL Completo (Todas las tablas y seeds)
# El esquema ha sido actualizado con nombres en español (usuarios, roles, etc.)
SQL_SCHEMA_SCRIPT = """
-- CREACIÓN DE LA BASE DE DATOS Y USO
CREATE DATABASE IF NOT EXISTS marketec;
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

-- PRODUCTOS (Tabla con clave foránea a usuarios para "unir usuario con producto")
CREATE TABLE IF NOT EXISTS productos (
    idProductos INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vendedor_id INT NOT NULL, 
    FOREIGN KEY (vendedor_id) REFERENCES usuarios(idUsuarios)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ===== SEEDS (DATOS INICIALES) =====
INSERT INTO roles (nombre_rol, tipo_rol, descripcion) VALUES
('administrador','system','Administrador con todos los permisos'),
('moderador','system','Modera y revisa contenido'),
('soporte','system','Atiende tickets y verifica vendedores'),
('vendedor','regular','Usuario que publica productos'),
('comprador','regular','Usuario que compra')
ON DUPLICATE KEY UPDATE nombre_rol = VALUES(nombre_rol);

SET SQL_MODE=@OLD_SQL_MODE;

-- Nota: El resto de las tablas (posts, tags, conversaciones, etc.) del esquema anterior no se incluyeron en tu script de reemplazo. 
-- Por simplicidad, solo he incluido las tablas que nos enviaste para sustituir (roles, usuarios, usuarios_roles).
"""

# Script del Trigger (Ajustado a los nuevos nombres de tabla y columna)
SQL_TRIGGER_SCRIPT = """
USE marketec;
DROP TRIGGER IF EXISTS trg_usuarios_roles_prevent_multiple_system;

CREATE TRIGGER trg_usuarios_roles_prevent_multiple_system
BEFORE INSERT ON usuarios_roles
FOR EACH ROW
BEGIN
  DECLARE r_kind VARCHAR(20);
  DECLARE cnt INT DEFAULT 0;
  SELECT tipo_rol INTO r_kind FROM roles WHERE idRoles = NEW.id_rol LIMIT 1;
  IF r_kind = 'system' THEN
    SELECT COUNT(*) INTO cnt
    FROM usuarios_roles ur
    JOIN roles r ON ur.id_rol = r.idRoles
    WHERE ur.id_usuario = NEW.id_usuario AND r.tipo_rol = 'system';
    IF cnt > 0 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un usuario ya tiene un role de tipo system. Solo se permite 1 (admin/moderador/soporte).';
    END IF;
  END IF;
END;
"""

def setup_database():
    """Conecta a MySQL, ejecuta el script de esquema y el trigger."""
    cnx = None
    cursor = None
    try:
        print("Conectando al servidor MySQL...")
        # Conexión al servidor MySQL (sin especificar DB)
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()
        print("Conexión exitosa. Ejecutando script de esquema...")

        # Ejecuta el script principal (creación de DB, tablas y seeds)
        statements = [s for s in SQL_SCHEMA_SCRIPT.split(';') if s.strip()]
        
        for statement in statements:
            try:
                # Ejecutamos cada sentencia SQL individualmente
                cursor.execute(statement)
            except mysql.connector.Error as err:
                # El error 1007 es "DB ya existe"
                if err.errno == 1007: 
                    continue
                # Ignoramos el error 1061 de índice duplicado (por el ON DUPLICATE KEY UPDATE)
                if err.errno == 1061: 
                    continue
                # Si es otro error de MySQL, lo reportamos
                print(f"Error al ejecutar sentencia SQL: {err} en:\n{statement[:100]}...")
        
        # Ejecuta el script del Trigger (que es una sola sentencia)
        print("Ejecutando script del Trigger...")
        try:
             cursor.execute(SQL_TRIGGER_SCRIPT)
             print("Trigger trg_usuarios_roles_prevent_multiple_system creado exitosamente.")
        except mysql.connector.Error as err:
             print(f"Error al crear el Trigger: {err}")

        cnx.commit()
        print("\n✅ Base de Datos 'marketec' con esquema en español creada exitosamente.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("❌ Error: Acceso denegado. Revisa tu usuario y contraseña de MySQL en el archivo.")
        else:
            print(f"❌ Ocurrió un error inesperado: {err}")
    finally:
        if cursor:
            cursor.close()
        if cnx and cnx.is_connected():
            cnx.close()
            print("Conexión a MySQL cerrada.")

if __name__ == '__main__':
    setup_database()