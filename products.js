const express = require('express');

// ENVUELVE todo en una función que recibe el 'pool'
module.exports = (pool) => { 
    const router = express.Router();
    // Usamos el 'pool' recibido como 'db'
    const db = pool; 

    // ====================================================================
    // RUTA 1: CREAR un nuevo producto (POST /api/products) - MODIFICADA
    // Incluye la validación de rol 'vendedor' para unir usuario con producto.
    // ====================================================================
    router.post('/', async (req, res) => {
        const { nombre, descripcion, precio, vendedor_id } = req.body; 

        if (!nombre || !precio || !vendedor_id) {
            return res.status(400).json({ 
                success: false,
                message: 'Nombre, precio y vendedor_id son obligatorios.' 
            });
        }
        
        let connection;
        try {
            connection = await db.getConnection(); // Obtener una conexión del pool

            // 1. Verificar si el usuario tiene el rol de 'vendedor'
            const [roleCheck] = await connection.query(
                `SELECT COUNT(ur.id_rol) AS is_vendedor
                 FROM usuarios_roles ur
                 JOIN roles r ON ur.id_rol = r.idRoles
                 WHERE ur.id_usuario = ? AND r.nombre_rol = 'vendedor'`,
                [vendedor_id]
            );

            if (roleCheck[0].is_vendedor === 0) {
                // Si el usuario no tiene el rol de vendedor, se niega la creación
                return res.status(403).json({
                    success: false,
                    message: 'Acceso denegado. Solo los usuarios con rol "vendedor" pueden crear productos.'
                });
            }

            // 2. Si es vendedor, procede a insertar el producto
            const insertSql = 'INSERT INTO productos (nombre, descripcion, precio, vendedor_id) VALUES (?, ?, ?, ?)';
            const [result] = await connection.query(insertSql, [nombre, descripcion, precio, vendedor_id]);
            
            res.status(201).json({
                success: true,
                message: 'Producto creado exitosamente.',
                productId: result.insertId,
            });

        } catch (error) {
            console.error('Error al crear el producto:', error);
            // Error 1452: Foreign key constraint failure (Usuario no existe)
            if (error.errno === 1452) {
                 return res.status(404).json({
                    success: false,
                    message: 'Vendedor no encontrado. El ID de vendedor proporcionado no existe en la tabla de usuarios.'
                });
            }
            res.status(500).json({ success: false, message: 'Error interno del servidor al crear producto.' });
        } finally {
            if (connection) connection.release(); // Liberar la conexión
        }
    });

    // ====================================================================
    // RUTA 2: OBTENER todos los productos (GET /api/products)
    // ====================================================================
    router.get('/', async (req, res) => {
        const sql = `
            SELECT 
                p.idProductos, 
                p.nombre AS nombre_producto, 
                p.descripcion, 
                p.precio, 
                p.fecha_creacion,
                u.nombre AS nombre_vendedor,
                u.correo AS correo_vendedor
            FROM productos p
            JOIN usuarios u ON p.vendedor_id = u.idUsuarios
            ORDER BY p.fecha_creacion DESC
        `;
        
        try {
            // Usamos db.query directamente del pool para consultas simples
            const [results] = await db.query(sql); 
            res.status(200).json({
                success: true,
                count: results.length,
                data: results
            });
        } catch (error) {
            console.error('Error al obtener productos:', error);
            res.status(500).json({ success: false, message: 'Error interno del servidor al obtener productos.' });
        }
    });

    return router; // Retornamos el router
};