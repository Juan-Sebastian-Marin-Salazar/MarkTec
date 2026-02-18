// === Selección y vista previa de imágenes ===
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const imageCount = document.getElementById("imageCount");
const maxImages = 6;

// guard clauses (only run listeners if elements exist on the page)
if (imageInput && imagePreview) {
  imageInput.addEventListener("change", handleImageSelection);
}

// === DRAG & DROP ===
const uploadArea = document.getElementById("uploadArea");

// Evitar comportamiento por defecto del navegador y efectos visuales
if (uploadArea) {
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
}

// Cuando sueltan la imagen
if (uploadArea) {
  uploadArea.addEventListener("drop", (e) => {
    uploadArea.classList.remove("dragover");

    const newFiles = Array.from(e.dataTransfer.files);  // nuevas imágenes arrastradas
    const currentFiles = imageInput ? Array.from(imageInput.files) : [];

    // Combinar ambas sin exceder tu límite de imágenes
    const combinedFiles = [...currentFiles, ...newFiles].slice(0, maxImages);

    // Crear un DataTransfer nuevo con todas las imágenes
    const dt = new DataTransfer();
    combinedFiles.forEach(f => dt.items.add(f));

    // Actualizar input y vista previa
    if (imageInput) imageInput.files = dt.files;
    handleImageSelection({ target: { files: dt.files } });
  });
}

function handleImageSelection(event) {
  const files = event && event.target && event.target.files ? Array.from(event.target.files) : [];

  // Detect edit mode by presence of server-side rendered .image-meta nodes
  const isEditPage = !!imagePreview.querySelector('.image-meta');

  if (!isEditPage) {
    // Default/new-product behavior: replace preview with selected files
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
          const wrapper = document.createElement('div');
          wrapper.classList.add('image-meta');
          wrapper.setAttribute('data-selected', 'true');
          const img = document.createElement("img");
          img.src = e.target.result;
          img.alt = file.name;
          img.classList.add("preview-img");
          wrapper.appendChild(img);
          imagePreview.appendChild(wrapper);
        };
        reader.readAsDataURL(file);
      }
    });

    if (imageCount) imageCount.textContent = `${validFiles.length}/${maxImages}`;
    return;
  }

  // Edit page behavior: merge existing server images with newly-selected files
  // Remove previously added selected previews (data-selected="true")
  imagePreview.querySelectorAll('[data-selected="true"]').forEach(n => n.remove());

  // Count existing server images that are NOT marked for deletion
  const existingNodes = Array.from(imagePreview.querySelectorAll('.image-meta')).filter(n => !n.classList.contains('marked-for-deletion') && !n.hasAttribute('data-selected'));
  const existingCount = existingNodes.length;

  const remaining = Math.max(0, maxImages - existingCount);
  let added = 0;

  files.forEach((file) => {
    if (added >= remaining) return;
    if (!file.type.startsWith("image/")) {
      alert(`El archivo ${file.name} no es una imagen válida.`);
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const wrapper = document.createElement('div');
      wrapper.classList.add('image-meta');
      wrapper.setAttribute('data-selected', 'true');
      const img = document.createElement("img");
      img.src = e.target.result;
      img.alt = file.name;
      img.classList.add("preview-img");
      wrapper.appendChild(img);
      imagePreview.appendChild(wrapper);
    };
    reader.readAsDataURL(file);
    added++;
  });

  if (imageCount) imageCount.textContent = `${existingCount + added}/${maxImages}`;
}

// === Envío del formulario ===
const productForm = document.getElementById("product-form");

// IMPORTANTE: no rehacemos FormData ni usamos fetch aquí.
// Deja que el navegador envíe el formulario con enctype="multipart/form-data".
// Flask recibirá correctamente request.files.getlist("imagenes").

if (productForm) {
  productForm.addEventListener("submit", (e) => {
    // Validación simple antes de enviar
    const tituloEl = document.getElementById("titulo") || document.getElementById("productName");
    const precioEl = document.getElementById("precio") || document.getElementById("price");

    const titulo = tituloEl ? tituloEl.value.trim() : "";
    const precio = precioEl ? precioEl.value.trim() : "";

    if (!titulo || !precio) {
      e.preventDefault();
      alert("El título y el precio son obligatorios.");
      return;
    }

    // Si quieres confirmar visualmente que el form se envió:
    console.log("Formulario enviado normalmente al backend con imágenes.");
  });
}