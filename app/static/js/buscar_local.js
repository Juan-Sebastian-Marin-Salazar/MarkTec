// static/js/buscar_local.js
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("searchInput");
    const resultsBox = document.getElementById("searchResults");

    if (!input || !resultsBox) return;

    // Normalizar texto
    const normalize = (str) => {
        if (!str) return "";
        return str.toString().toLowerCase()
            .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
            .replace(/\s+/g, " ").trim();
    };

    // Obtener productos de la vista visible (cliente o vendedor)
    function obtenerProductosVisibles() {
        const vistaActiva = Array.from(document.querySelectorAll(".contenido_categoria"))
            .find(v => window.getComputedStyle(v).display !== "none");

        if (!vistaActiva) return [];
        return Array.from(vistaActiva.querySelectorAll(".producto"));
    }

    // Índice interno de productos
    let index = [];

    // Reindexar cada vez que cambie la vista o se cargue la página
    function actualizarIndice() {
        index = [];
        const productos = obtenerProductosVisibles();

        productos.forEach(el => {
            const tituloEl = el.querySelector(".nombre_p");
            const descripcionEl = el.querySelector(".descripcion");
            const vendedorEl = el.querySelector(".nombre_v");
            const imgEl = el.querySelector("img");

            const titulo = tituloEl ? tituloEl.textContent.trim() : "";
            const descripcion = descripcionEl ? descripcionEl.textContent.trim() : "";
            const vendedor = vendedorEl ? vendedorEl.textContent.trim() : "";
            const thumb = (imgEl && imgEl.src) ? imgEl.src : "/static/img/default.png";
            
            // Extract product ID from onclick attribute or data attribute
            // The producto element has onclick="window.location='/producto/{{ pub.idPublicaciones }}'"
            const onclickAttr = el.getAttribute("onclick");
            let productId = null;
            if (onclickAttr && onclickAttr.includes("/producto/")) {
                const match = onclickAttr.match(/\/producto\/(\d+)/);
                if (match) productId = match[1];
            }

            index.push({
                el,
                titulo,
                descripcion,
                vendedor,
                thumb,
                productId,
                searchable: normalize(`${titulo} ${descripcion} ${vendedor}`)
            });
        });
    }

    // Primera carga
    actualizarIndice();

    // Función para aplicar el filtro en la grilla
    function aplicarFiltro(term) {
        const nterm = normalize(term);
        if (!nterm) {
            index.forEach(item => item.el.classList.remove("oculto"));
            return;
        }

        index.forEach(item => {
            if (item.searchable.includes(nterm)) {
                item.el.classList.remove("oculto");
            } else {
                item.el.classList.add("oculto");
            }
        });
    }

    // Renderizar el dropdown
    function renderDropdown(matchesArr, term) {
        resultsBox.innerHTML = "";

        if (!term.trim()) {
            hideDropdown();
            return;
        }

        if (matchesArr.length === 0) {
            resultsBox.innerHTML = `<div class="no-results">Sin resultados</div>`;
        } else {
            matchesArr.slice(0, 10).forEach(item => {
                const div = document.createElement("div");
                div.className = "result-item";
                div.innerHTML = `
                    <div class="mini-thumb"><img src="${item.thumb}" alt=""></div>
                    <div class="mini-txt">
                        <div class="mini-main">${escapeHtml(item.titulo)}</div>
                        <div class="mini-sub">${escapeHtml(item.vendedor)} • ${truncate(item.descripcion, 60)}</div>
                    </div>
                `;
                div.addEventListener("click", () => {
                    // Navigate to product detail page
                    if (item.productId) {
                        window.location.href = `/producto/${item.productId}`;
                    } else {
                        // Fallback: just filter and highlight
                        input.value = item.titulo;
                        aplicarFiltro(item.titulo);
                        hideDropdown();
                    }
                });
                resultsBox.appendChild(div);
            });
        }

        showDropdown();
    }

    function hideDropdown() {
        resultsBox.classList.add("oculto");
    }

    function showDropdown() {
        resultsBox.classList.remove("oculto");
    }

    function escapeHtml(text) {
        return String(text).replace(/[&<>"']/g, function (m) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
        });
    }

    function truncate(text, n) {
        if (!text) return "";
        return text.length > n ? text.slice(0, n-1) + "…" : text;
    }

    // Evento de escritura con debounce
    let debounceTimer = null;
    input.addEventListener("input", () => {
        const term = input.value;
        clearTimeout(debounceTimer);

        debounceTimer = setTimeout(() => {
            actualizarIndice();  // ← Reindexa según la vista activa

            const matches = index.filter(item =>
                item.searchable.includes(normalize(term))
            );

            renderDropdown(matches, term);
            aplicarFiltro(term);

        }, 180);
    });

    // Escape para limpiar búsqueda
    input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            input.value = "";
            aplicarFiltro("");
            hideDropdown();
        }
    });

    // Clic fuera ~> cerrar dropdown
    document.addEventListener("click", (e) => {
        if (!resultsBox.contains(e.target) && e.target !== input) {
            hideDropdown();
        }
    });

});
