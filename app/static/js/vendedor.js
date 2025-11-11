// vendedor.js - Funcionalidad para el modo vendedor

document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const btnCliente = document.querySelector('.cliente');
    const btnVendedor = document.querySelector('.vendor');
    const controlesVendedor = document.getElementById('controlesVendedor');
    const btnAgregarProducto = document.getElementById('btnAgregarProducto');
    const productos = document.querySelectorAll('.producto');

    // Inicializar estado - Cliente activo por defecto
    let modoActual = 'cliente';

    // Función para cambiar entre modos
    function cambiarModo(modo) {
        modoActual = modo;
        
        // Remover clase activa de ambos botones primero
        btnCliente.classList.remove('activo');
        btnVendedor.classList.remove('activo');
        
        if (modo === 'vendedor') {
            // Activar modo vendedor
            btnVendedor.classList.add('activo');
            
            // Mostrar controles de vendedor
            if (controlesVendedor) {
                controlesVendedor.style.display = 'block';
            }
            
            // Filtrar productos: mostrar solo los propios
            productos.forEach(producto => {
                if (producto.classList.contains('mi-producto')) {
                    // Mostrar productos propios con controles
                    producto.style.display = 'block';
                    producto.classList.add('mostrar-controles');
                } else {
                    // Ocultar productos de otros vendedores
                    producto.style.display = 'none';
                }
            });
            
        } else {
            // Activar modo cliente
            btnCliente.classList.add('activo');
            
            // Ocultar controles de vendedor
            if (controlesVendedor) {
                controlesVendedor.style.display = 'none';
            }
            
            // Mostrar todos los productos
            productos.forEach(producto => {
                producto.style.display = 'block';
                producto.classList.remove('mostrar-controles');
            });
        }
    }

    // Event listeners para los botones de modo
    if (btnCliente) {
        btnCliente.addEventListener('click', function() {
            cambiarModo('cliente');
        });
    }

    if (btnVendedor) {
        btnVendedor.addEventListener('click', function() {
            cambiarModo('vendedor');
        });
    }

    // Agregar controles a los productos propios
    productos.forEach((producto, index) => {
        if (producto.classList.contains('mi-producto')) {
            // Crear y agregar controles a cada producto propio
            const controlesProducto = document.createElement('div');
            controlesProducto.className = 'controles-producto';
            
            const btnEditar = document.createElement('button');
            btnEditar.className = 'btn-editar';
            btnEditar.textContent = 'Editar';
            btnEditar.onclick = () => editarProducto(index + 1);
            
            const btnEliminar = document.createElement('button');
            btnEliminar.className = 'btn-eliminar';
            btnEliminar.textContent = 'Eliminar';
            btnEliminar.onclick = () => eliminarProducto(index + 1);
            
            controlesProducto.appendChild(btnEditar);
            controlesProducto.appendChild(btnEliminar);
            producto.appendChild(controlesProducto);
        }
    });

    // Funciones para manejar productos
    function agregarProducto() {
        alert('Abriendo formulario para agregar nuevo producto');
        // Aquí puedes implementar la lógica para agregar producto
        // Por ejemplo: mostrar un modal, redirigir a formulario, etc.
    }

    function editarProducto(id) {
        alert(`Editando producto ${id}`);
        // Aquí puedes implementar la lógica para editar producto
    }

    function eliminarProducto(id) {
        if (confirm('¿Estás seguro de que quieres eliminar este producto?')) {
            alert(`Producto ${id} eliminado`);
            // Aquí puedes implementar la lógica para eliminar producto
        }
    }

    // Event listener para agregar producto
    if (btnAgregarProducto) {
        btnAgregarProducto.addEventListener('click', agregarProducto);
    }

    // Inicializar en modo cliente
    cambiarModo('cliente');
});