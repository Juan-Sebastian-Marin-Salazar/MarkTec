    document.addEventListener('DOMContentLoaded', function() {
      const loginBtn = document.getElementById('btnLogin');
      
      if (loginBtn) {
        loginBtn.addEventListener('click', function() {
          window.location.href = 'pagina_principar.html';
          
        });
      } else {
        console.error('No se encontró el botón con id btnLogin');
      }
    });

    function redirigirLogin() {
      const email = document.getElementById('egresado_correo').value;
      const password = document.getElementById('password').value;
      
      if (email && password) {
        window.location.href = 'pagina_principar.html';
      } else {
        alert('Por favor, completa todos los campos');
      }
    }

document.addEventListener('DOMContentLoaded', function() {
    const toggleIdentificar = document.getElementById('toggle-identificar');
    const studentForm = document.getElementById('student-form');
    const identificacionForm = document.getElementById('identificacion-form');
    const formDescription = document.querySelector('.form-description');

    toggleIdentificar.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (studentForm.classList.contains('hidden')) {
            // Mostrar login, ocultar registro
            studentForm.classList.remove('hidden');
            identificacionForm.classList.add('hidden');
            formDescription.textContent = 'Inicia sesión en tu cuenta';
            toggleIdentificar.textContent = '¡Regístrate!';
        } else {
            // Ocultar login, mostrar registro
            studentForm.classList.add('hidden');
            identificacionForm.classList.remove('hidden');
            formDescription.textContent = 'Crea tu cuenta';
            toggleIdentificar.textContent = '¿Ya tienes cuenta? ¡Inicia sesión!';
        }
    });
});