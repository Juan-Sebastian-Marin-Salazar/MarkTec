// === Selección y vista previa de imágenes ===
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const imageCount = document.getElementById("imageCount");
const maxImages = 6;

imageInput.addEventListener("change", handleImageSelection);

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