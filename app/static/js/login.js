document.addEventListener("DOMContentLoaded", function () {

    // Mostrar/ocultar formularios
    const toggle = document.getElementById("toggle-identificar");
    const loginForm = document.getElementById("student-form");
    const registerForm = document.getElementById("identificacion-form");

    toggle.addEventListener("click", function () {
        loginForm.classList.toggle("hidden");
        loginForm.classList.toggle("active");

        registerForm.classList.toggle("hidden");
        registerForm.classList.toggle("active");
    });

    // Botón login
    document.getElementById("btnLogin").addEventListener("click", function () {
        loginForm.submit();   // ← Enviar POST a /login
    });

    // Botón registro
    document.getElementById("btnRegistro").addEventListener("click", function () {
        registerForm.submit();  // ← Enviar POST a /register
    });

});