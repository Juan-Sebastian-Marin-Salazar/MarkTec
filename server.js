// server.js (En la carpeta Marketec_Server)

// Módulos para servidor y base de datos
const express = require('express');
const mysql = require('mysql2/promise');

const app = express();
const PORT = 3000;

// Configuración de la Base de Datos Marketec
// ¡AJUSTA LA CONTRASEÑA! (Si no usaste elferny23)
const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'elferny23', // <--- Revisa y ajusta esto si es diferente
    database: 'marketec',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
};

// Crear el Pool de Conexiones
const pool = mysql.createPool(dbConfig);

// Función para verificar la conexión
async function testDbConnection() {
    try {
        const connection = await pool.getConnection();
        console.log('✅ Conexión exitosa a la base de datos \'marketec\'.');
        connection.release();
    } catch (error) {
        console.error('❌ Error al conectar a la base de datos:', error.message);
    }
}

// Llama a la función para verificar la conexión al iniciar
testDbConnection();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// IMPORTACIÓN Y USO DE RUTAS DE AUTENTICACIÓN
// 1. Importa auth.js y llama a la función pasándole el pool
const authRouter = require('./auth')(pool); 
// 2. Usa el router para todas las rutas que empiezan con /api
app.use('/api', authRouter); 

// === 👇 NUEVO: IMPORTACIÓN Y USO DE RUTAS DE PRODUCTOS 👇 ===
// 1. Importa products.js y llama a la función pasándole el pool
const productsRouter = require('./products')(pool); 
// 2. Usa el router para las rutas de productos (/api/products...)
app.use('/api/products', productsRouter); 
// ==========================================================

// Ruta de prueba (para verificar que el servidor está activo en el navegador)
app.get('/', (req, res) => {
    res.status(404).json({ message: 'Ruta principal no definida. Use /api para las rutas.' });
});

// Inicio del Servidor
app.listen(PORT, () => {
    console.log(`Servidor Marketec corriendo en http://localhost:${PORT}`);
});