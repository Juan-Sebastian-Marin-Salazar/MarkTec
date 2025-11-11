// server.js

// Módulos para servidor y base de datos
const express = require('express');
const mysql = require('mysql2/promise');

// Módulos de autenticación
const authRouter = require('./auth'); 

const app = express();
const PORT = 3000;

// Configuración de la Base de Datos Marketec
// ¡AJUSTA LA CONTRASEÑA! (Si es 'elfernny23', úsala)
const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'elferny23', // <--- Ajusta esto
    database: 'marketec',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
};

// Crear el Pool de Conexiones
const pool = mysql.createPool(dbConfig);

// Middleware
app.use(express.json()); // Para parsear JSON
app.use(express.urlencoded({ extended: true })); // Para parsear formularios

// Montar el Router de Autenticación
app.use('/api', authRouter);

// Endpoint simple para la raíz
app.get('/', (req, res) => {
    res.send("Servidor Marketec listo. Usa /api/register o /api/login.");
});


// Función para probar la conexión al iniciar
async function testDbConnection() {
    try {
        const connection = await pool.getConnection();
        console.log("✅ Conexión exitosa a la base de datos 'marketec'.");
        connection.release();
    } catch (err) {
        console.error("❌ Error al conectar a la base de datos:", err.message);
    }
}

// Exportar el pool para que auth.js pueda usarlo
module.exports.pool = pool;


// Inicio del Servidor
testDbConnection().then(() => {
    app.listen(PORT, () => {
        console.log(`Servidor Marketec corriendo en http://localhost:${PORT}`);
    });
});