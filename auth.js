// auth.js

const express = require('express');
const bcrypt = require('bcryptjs'); 
const { pool } = require('./server'); // Importa la conexión a la DB desde server.js

const router = express.Router();
const saltRounds = 10; 

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
        connection = await pool.getConnection();

        // 1. Verificar si el usuario ya existe
        const [existingUsers] = await connection.query(
            'SELECT id FROM users WHERE email = ?',
            [email]
        );

        if (existingUsers.length > 0) {
            return res.status(409).json({ message: 'El email ya está registrado.' });
        }

        // 2. Encriptar la contraseña de forma segura
        const password_hash = await bcrypt.hash(password, saltRounds);

        // 3. Insertar el nuevo usuario en la tabla 'users'
        const insertUserQuery = `
            INSERT INTO users (nombre, email, password_hash)
            VALUES (?, ?, ?)
        `;
        const [result] = await connection.query(insertUserQuery, [email, email, password_hash]); 
        const newUserId = result.insertId;

        // 4. Asignar el rol 'comprador' por defecto
        const [role] = await connection.query('SELECT id FROM roles WHERE name = "comprador"');
        if (role.length > 0) {
            await connection.query(
                'INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)',
                [newUserId, role[0].id]
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
        return res.status(400).json({ message: 'Email y contraseña son requeridos para el login.' });
    }

    let connection;
    try {
        connection = await pool.getConnection();

        // 1. Buscar el usuario por email
        const [users] = await connection.query(
            'SELECT id, password_hash, nombre FROM users WHERE email = ?',
            [email]
        );

        if (users.length === 0) {
            return res.status(401).json({ message: 'Credenciales incorrectas (Usuario no encontrado).' });
        }

        const user = users[0];

        // 2. Comparar la contraseña ingresada con el hash guardado
        const isMatch = await bcrypt.compare(password, user.password_hash);

        if (!isMatch) {
            return res.status(401).json({ message: 'Credenciales incorrectas (Contraseña inválida).' });
        }

        // 3. Login exitoso
        console.log(`Login exitoso para usuario: ${user.nombre} (${user.id})`);
        
        res.status(200).json({ 
            message: 'Inicio de sesión exitoso.', 
            user: { id: user.id, nombre: user.nombre, email: email }
        });

    } catch (error) {
        console.error('Error durante el login:', error);
        res.status(500).json({ message: 'Error interno del servidor durante el login.' });
    } finally {
        if (connection) connection.release();
    }
});


module.exports = router;