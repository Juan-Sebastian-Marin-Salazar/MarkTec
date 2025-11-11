// nuevo_producto.js - Funcionalidad para el formulario de nuevo producto

document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const productForm = document.getElementById('product-form');
    const imageInput = document.getElementById('imageInput');
    const uploadArea = document.getElementById('uploadArea');
    const imagePreview = document.getElementById('imagePreview');
    const productName = document.getElementById('productName');
    const nameCharCount = document.getElementById('nameCharCount');
    const category = document.getElementById('category');
    const price = document.getElementById('price');
    const description = document.getElementById('description');
    const descCharCount = document.getElementById('descCharCount');

    // Variables
    let selectedImages = [];

    // Event Listeners
    imageInput.addEventListener('change', handleImageSelection);
    productName.addEventListener('input', updateNameCharCount);
    description.addEventListener('input', updateDescCharCount);
    productForm.addEventListener('submit', handleFormSubmit);

    // Drag and drop para imágenes
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Funciones

    function handleDragOver(e) {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    }

    function handleDragLeave(e) {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
    }

    function handleDrop(e) {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleImageFiles(files);
        }
    }

    function handleImageSelection(e) {
        const files = e.target.files;
        handleImageFiles(files);
    }

    function handleImageFiles(files) {
        for (let file of files) {
            // Validar tipo de archivo
            if (!file.type.match('image.*')) {
                alert('Solo se permiten archivos de imagen (JPG, PNG, WEBP)');
                continue;
            }

            // Validar tamaño (5MB)
            if (file.size > 5 * 1024 * 1024) {
                alert('La imagen es demasiado grande. Máximo 5MB.');
                continue;
            }

            // Crear preview
            const reader = new FileReader();
            reader.onload = function(e) {
                addImagePreview(file.name, e.target.result);
            };
            reader.readAsDataURL(file);

            // Agregar a array de imágenes seleccionadas
            selectedImages.push(file);
        }
    }

    function addImagePreview(fileName, imageData) {
        const previewItem = document.createElement('div');
        previewItem.className = 'preview-item';
        
        previewItem.innerHTML = `
            <img src="${imageData}" alt="${fileName}">
            <button type="button" class="remove-image" onclick="removeImage(this)">×</button>
        `;
        
        imagePreview.appendChild(previewItem);
    }

    function removeImage(button) {
        const previewItem = button.parentElement;
        const index = Array.from(imagePreview.children).indexOf(previewItem);
        
        // Remover del array
        selectedImages.splice(index, 1);
        
        // Remover del DOM
        previewItem.remove();
    }

    function updateNameCharCount() {
        nameCharCount.textContent = productName.value.length;
    }

    function updateDescCharCount() {
        descCharCount.textContent = description.value.length;
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        
        // Validaciones
        if (!validateForm()) {
            return;
        }

        // Aquí iría la lógica para enviar el formulario
        // Por ejemplo: subir imágenes y datos del producto
        
        const formData = new FormData();
        
        // Agregar imágenes
        selectedImages.forEach((image, index) => {
            formData.append(`image_${index}`, image);
        });
        
        // Agregar datos del producto
        formData.append('name', productName.value);
        formData.append('category', category.value);
        formData.append('price', price.value);
        formData.append('description', description.value);
        
        // Simular envío (reemplazar con tu lógica real)
        console.log('Datos del producto:', {
            name: productName.value,
            category: category.value,
            price: price.value,
            description: description.value,
            images: selectedImages.length
        });
        
        alert('¡Producto publicado exitosamente!');
        
        // Redirigir o limpiar formulario
        // window.location.href = 'pagina_principar.html';
    }

    function validateForm() {
        // Validar imágenes
        if (selectedImages.length === 0) {
            alert('Por favor, selecciona al menos una imagen del producto.');
            return false;
        }

        // Validar nombre
        if (!productName.value.trim()) {
            alert('Por favor, ingresa el nombre del producto.');
            productName.focus();
            return false;
        }

        // Validar categoría
        if (!category.value) {
            alert('Por favor, selecciona una categoría.');
            category.focus();
            return false;
        }

        // Validar precio
        if (!price.value || parseFloat(price.value) <= 0) {
            alert('Por favor, ingresa un precio válido.');
            price.focus();
            return false;
        }

        // Validar descripción
        if (!description.value.trim()) {
            alert('Por favor, ingresa una descripción del producto.');
            description.focus();
            return false;
        }

        return true;
    }

    // Hacer funciones disponibles globalmente para los onclick
    window.removeImage = removeImage;
});

// Función para redirigir desde el botón "Agregar Producto"
function redirectToNewProduct() {
    window.location.href = 'nuevo_producto.html';
}