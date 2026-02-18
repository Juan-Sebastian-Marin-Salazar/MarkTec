// vendedor.js - alternar entre vista cliente y vista vendedor
// Se encarga únicamente del cambio visual de pantallas, SIN interferir con la verificación del usuario.
// La verificación se maneja desde manejarBotonVendedor() en el HTML.

document.addEventListener("DOMContentLoaded", function () {

    const btnCliente = document.querySelector(".cliente");
    const btnVendedor = document.querySelector(".vendor");

    const vistaCliente = document.getElementById("vistaCliente");
    const vistaVendedor = document.getElementById("vistaVendedor");

    const controlesVendedor = document.getElementById("controlesVendedor");

    // Si falta algo, no ejecutamos el script
    if (!btnCliente || !btnVendedor || !vistaCliente || !vistaVendedor) {
        console.warn("Elementos faltantes en vendedor.js");
        return;
    }

    // Por defecto: vista Cliente activa
    mostrarCliente();

    function mostrarCliente() {
        vistaCliente.style.display = "grid";
        vistaVendedor.style.display = "none";

        if (controlesVendedor) controlesVendedor.style.display = "none";

        btnCliente.classList.add("activo");
        btnVendedor.classList.remove("activo");
    }

    function mostrarVendedor() {
        // Aquí NO verificamos permisos.
        // Si el usuario NO es verificado, el HTML ya lo redirige con manejarBotonVendedor().
        // Si es verificado, entonces sí mostramos su vista.

        vistaCliente.style.display = "none";
        vistaVendedor.style.display = "grid";

        if (controlesVendedor) controlesVendedor.style.display = "block";

        btnVendedor.classList.add("activo");
        btnCliente.classList.remove("activo");
    }

    // EVENTOS PARA CAMBIAR DE MODO
    btnCliente.addEventListener("click", () => {
        mostrarCliente();
    });

    btnVendedor.addEventListener("click", () => {
        const esVerificado = btnVendedor.getAttribute("data-verificado") === "true";

        if (!esVerificado) {
            // El HTML ya manda al usuario a /verificar-vendedor
            return;
        }

        mostrarVendedor();
    });
});