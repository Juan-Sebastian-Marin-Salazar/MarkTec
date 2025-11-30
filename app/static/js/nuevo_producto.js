// === Selección y vista previa de imágenes ===
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const imageCount = document.getElementById("imageCount");
const maxImages = 6;

imageInput.addEventListener("change", handleImageSelection);

// === DRAG & DROP ===
const uploadArea = document.getElementById("uploadArea");

// Evitar comportamiento por defecto del navegador
["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
    uploadArea.addEventListener(eventName, e => e.preventDefault());
    uploadArea.addEventListener(eventName, e => e.stopPropagation());
});

// Efecto visual al arrastrar
uploadArea.addEventListener("dragover", () => {
    uploadArea.classList.add("dragover");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
});

// Cuando sueltan la imagen
uploadArea.addEventListener("drop", (e) => {
    uploadArea.classList.remove("dragover");

    const newFiles = Array.from(e.dataTransfer.files);  // nuevas imágenes arrastradas
    const currentFiles = Array.from(imageInput.files);  // imágenes ya elegidas antes

    // Combinar ambas sin exceder tu límite de imágenes
    const combinedFiles = [...currentFiles, ...newFiles].slice(0, maxImages);

    // Crear un DataTransfer nuevo con todas las imágenes
    const dt = new DataTransfer();
    combinedFiles.forEach(f => dt.items.add(f));

    // Actualizar input y vista previa
    imageInput.files = dt.files;
    handleImageSelection({ target: { files: dt.files } });
});

function handleImageSelection(event) {
  const files = Array.from(event.target.files);
  imagePreview.innerHTML = ""; // Limpia previas
  let validFiles = [];

  files.forEach((file, index) => {
    if (!file.type.startsWith("image/")) {
      alert(`El archivo ${file.name} no es una imagen válida.`);
      return;
    }

    if (index < maxImages) {
      validFiles.push(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = document.createElement("img");
        img.src = e.target.result;
        img.alt = file.name;
        img.classList.add("preview-img");
        imagePreview.appendChild(img);
      };
      reader.readAsDataURL(file);
    }
  });

  imageCount.textContent = `${validFiles.length}/${maxImages}`;
}

// === Envío del formulario ===
const productForm = document.getElementById("product-form");

// IMPORTANTE: no rehacemos FormData ni usamos fetch aquí.
// Deja que el navegador envíe el formulario con enctype="multipart/form-data".
// Flask recibirá correctamente request.files.getlist("imagenes").

productForm.addEventListener("submit", (e) => {
  // Validación simple antes de enviar
  const titulo = document.getElementById("titulo").value.trim();
  const precio = document.getElementById("precio").value.trim();

  if (!titulo || !precio) {
    e.preventDefault();
    alert("El título y el precio son obligatorios.");
    return;
  }

  // Si quieres confirmar visualmente que el form se envió:
  console.log("Formulario enviado normalmente al backend con imágenes.");
});