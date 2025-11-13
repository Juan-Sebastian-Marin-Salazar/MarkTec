// auth.js (En la carpeta Marketec_Server)

const express = require('express');
const bcrypt = require('bcryptjs'); 

const router = express.Router();
const saltRounds = 10; 

// EXPORTA UNA FUNCIÓN QUE ACEPTA EL 'POOL' COMO ARGUMENTO
module.exports = (pool) => { 

    // =================================================================
    // 📝 RUTA DE REGISTRO DE USUARIO
    // =================================================================
    router.post('/register', async (req, res) => {
        const { email, password } = req.body; 

        if (!email || !password) {
            return res.status(400).json({ message: 'Email y contraseña son requeridos para el registro.' });
        }

        let connection;
        try {
            // Usa el pool pasado como argumento
            connection = await pool.getConnection(); 

            // 1. Verificar si el usuario ya existe (Tabla: usuarios, Columna: correo)
            const [existingUsers] = await connection.query(
                'SELECT idUsuarios FROM usuarios WHERE correo = ?',
                [email]
            );

            if (existingUsers.length > 0) {
                return res.status(409).json({ message: 'El email ya está registrado.' });
            }

            // 2. Encriptar la contraseña
            const clave_hash = await bcrypt.hash(password, saltRounds);

            // 3. Insertar el nuevo usuario (Tabla: usuarios, Columna: clave_hash)
            const insertUserQuery = `
                INSERT INTO usuarios (nombre, correo, clave_hash)
                VALUES (?, ?, ?)
            `;
            // Usamos el email como nombre por defecto si no se proporciona uno
            const [result] = await connection.query(insertUserQuery, [email, email, clave_hash]); 
            const newUserId = result.insertId;

            // 4. Asignar el rol 'comprador' por defecto (Tabla: roles)
            const [role] = await connection.query('SELECT idRoles FROM roles WHERE nombre_rol = "comprador"');
            if (role.length > 0) {
                // Tabla: usuarios_roles
                await connection.query(
                    'INSERT INTO usuarios_roles (id_usuario, id_rol) VALUES (?, ?)',
                    [newUserId, role[0].idRoles]
                );
            }

            console.log(`Usuario registrado y rol asignado: ID ${newUserId}, Email: ${email}`);
            res.status(201).json({ 
                message: 'Usuario registrado exitosamente.', 
                userId: newUserId 
            });

        } catch (error) {
            console.error('Error durante el registro:', error);
            res.status(500).json({ message: 'Error interno del servidor durante el registro.' });
        } finally {
            if (connection) connection.release();
        }
    });

    // =================================================================
    // 🔒 RUTA DE INICIO DE SESIÓN (LOGIN)
    // =================================================================
    router.post('/login', async (req, res) => {
        const { email, password } = req.body;
        
        if (!email || !password) {
            return res.status(400).json({ message: 'Email y contraseña son requeridos para iniciar sesión.' });
        }

        let connection;
        try {
            connection = await pool.getConnection();

            // 1. Buscar el usuario por email
            const [users] = await connection.query(
                'SELECT idUsuarios, clave_hash, nombre FROM usuarios WHERE correo = ?',
                [email]
            );

            if (users.length === 0) {
                return res.status(401).json({ message: 'Credenciales incorrectas (Usuario no encontrado).' });
            }

            const user = users[0];

            // 2. Comparar la contraseña ingresada con el hash guardado
            const isMatch = await bcrypt.compare(password, user.clave_hash);

            if (!isMatch) {
                return res.status(401).json({ message: 'Credenciales incorrectas (Contraseña).' });
            }

            // 3. Obtener el rol del usuario (Si tienes implementado JWT, iría aquí)
            const [userRoles] = await connection.query(
                'SELECT r.nombre_rol FROM usuarios_roles ur JOIN roles r ON ur.id_rol = r.idRoles WHERE ur.id_usuario = ?',
                [user.idUsuarios]
            );
            const roles = userRoles.map(r => r.nombre_rol);

            console.log(`Login exitoso: ID ${user.idUsuarios}, Email: ${email}, Roles: ${roles.join(', ')}`);
            res.status(200).json({
                message: 'Inicio de sesión exitoso.',
                user: {
                    id: user.idUsuarios,
                    nombre: user.nombre,
                    email: email,
                    roles: roles
                }
            });

        } catch (error) {
            console.error('Error durante el login:', error);
            res.status(500).json({ message: 'Error interno del servidor durante el login.' });
        } finally {
            if (connection) connection.release();
        }
    });

    return router; // RETORNA EL ROUTER DEFINIDO
}; // FINAL DE LA FUNCIÓN EXPORTADA