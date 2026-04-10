document.addEventListener("DOMContentLoaded", async () => {
  const productTable = document.querySelector("#productTable tbody");
  const searchInput = document.getElementById("searchInput");
  const loader = document.getElementById("loader");
  const themeToggle = document.getElementById("themeToggle");
  const dollarPriceElement = document.getElementById("dollarPrice");
  const fechaListaElement = document.getElementById("fechaLista");

  let currentJsonFileName = "";
  let products = [];
  let searchTimeout;

  // Función para obtener el nombre del archivo JSON desde latest-json-filename.txt en la raíz
  const getLatestJsonFileName = async () => {
    try {
      console.log("Obteniendo nombre del archivo JSON desde /latest-json-filename.txt (raíz del sitio)...");
      const response = await fetch("/latest-json-filename.txt"); // Fetch desde la raíz del sitio web
      if (!response.ok) {
        throw new Error("No se pudo obtener el nombre del archivo JSON desde /latest-json-filename.txt");
      }
      const latestFile = await response.text(); // Leer el nombre del archivo como texto
      console.log("Nombre del archivo JSON obtenido desde /latest-json-filename.txt:", latestFile.trim());
      return latestFile.trim();
    } catch (error) {
      console.error("Error al obtener el nombre del JSON desde /latest-json-filename.txt:", error);
      throw error;
    }
  };

  const fetchDollarPrice = async () => {
    try {
      const response = await fetch("https://dolarapi.com/v1/ambito/dolares/oficial");
      const data = await response.json();
      console.log("Precio del dólar obtenido:", data);
      const ventaRedondeada = Math.round(data.venta);
      dollarPriceElement.textContent = `$${ventaRedondeada}`;
      
      const fecha = new Date(data.fechaActualizacion);
      const opciones = { day: '2-digit', month: '2-digit' };
      const dollarDateElement = document.getElementById("dollarDatee");
      if (dollarDateElement) {
        dollarDateElement.textContent = `(${fecha.toLocaleDateString('es-AR', opciones)})`;
      }
    } catch (error) {
      console.error("Error al obtener el precio del dólar:", error);
      dollarPriceElement.textContent = "N/A";
    }
  };

  const fetchAndDecompressProducts = async () => {
    console.log("Cargando y descomprimiendo productos desde:", currentJsonFileName);
    loader.classList.remove("hidden");
    try {
      const response = await fetch(currentJsonFileName);
      if (!response.ok) {
        throw new Error("Error en la respuesta de red");
      }

      // Descomprimir el stream gzip
      const compressedStream = response.body.pipeThrough(new DecompressionStream("gzip"));
      const reader = compressedStream.getReader();
      const decoder = new TextDecoder("utf-8");
      let jsonText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        jsonText += decoder.decode(value, { stream: true });
      }
      jsonText += decoder.decode();

      products = JSON.parse(jsonText);
      console.log("Productos descomprimidos:", products);

      // Guardamos en localStorage para cachear según el nombre del archivo
      localStorage.setItem("products", JSON.stringify(products));
      localStorage.setItem("jsonFileName", currentJsonFileName);
      displayProducts(products);
    } catch (error) {
      console.error("Error al cargar los productos:", error);
    }
    loader.classList.add("hidden");
  };

  const displayProducts = (productsToDisplay) => {
    productTable.innerHTML = "";
    if (productsToDisplay.length === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.textContent = "No se ha encontrado el producto.";
      cell.style.textAlign = "center";
      row.appendChild(cell);
      productTable.appendChild(row);
      return;
    }
    productsToDisplay.forEach((product) => {
      const row = document.createElement("tr");
      const monedaDisplay = (product.moneda === "DOL" || product.moneda === "USD") ? "U$S" : product.moneda;
      row.innerHTML = `
        <td data-label="Producto">${product.producto}</td>
        <td data-label="Detalle">${product.detalle}</td>
        <td data-label="Marca">${product.marca}</td>
        <td data-label="Un/Mts">${product.unidad === "UN" || product.unidad === "Un" ? "Un" : "Mts"}</td>
        <td data-label="Precio">${monedaDisplay} ${product.precio}</td>
      `;
      productTable.appendChild(row);
    });
  };

  const filterProducts = (searchTerm) => {
    const searchTerms = searchTerm.toLowerCase().split(/\s+/).filter(Boolean);
    return products.filter((product) =>
      searchTerms.every(
        (term) =>
          product.producto.toLowerCase().includes(term) ||
          product.detalle.toLowerCase().includes(term) ||
          product.marca.toLowerCase().includes(term)
      )
    );
  };

  // Inicialización: se comprueba si en localStorage ya se cargaron productos con el mismo archivo
  const initializeProducts = async () => {
    try {
      currentJsonFileName = await getLatestJsonFileName();
    } catch (error) {
      console.error("No se pudo obtener el nombre del archivo JSON.");
      loader.classList.add("hidden");
      return;
    }
    if (!currentJsonFileName) {
      console.error("No hay archivo JSON disponible para cargar los productos.");
      loader.classList.add("hidden");
      return;
    }
    const storedJsonFileName = localStorage.getItem("jsonFileName");
    const storedProducts = localStorage.getItem("products");
    if (storedJsonFileName === currentJsonFileName && storedProducts) {
      products = JSON.parse(storedProducts);
      console.log("Usando productos cacheados para el archivo:", currentJsonFileName);
      displayProducts(products);
    } else {
      await fetchAndDecompressProducts();
    }
    displayDate(); // Mostrar la fecha extraída del nombre del archivo
  };

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const searchTerm = searchInput.value.trim();
      const filteredProducts = searchTerm ? filterProducts(searchTerm) : products;
      displayProducts(filteredProducts);
    }, 400);
  });

  themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    themeToggle.innerHTML = document.body.classList.contains("dark-mode") ? "☀️" : "🌙";
    themeToggle.style.backgroundColor = document.body.classList.contains("dark-mode") ? "#2e2e2e" : "#fafafa";
  });

  // Función para extraer y mostrar la fecha del archivo (basada en su nombre)
  const extractDateFromFileName = (fileName) => {
    const datePattern = /(\d{2}-\d{2}-\d{2,4})/;
    const match = fileName.match(datePattern);
    return match ? match[0] : null;
  };

  const displayDate = () => {
    const fechaExtraida = extractDateFromFileName(currentJsonFileName);
    if (fechaExtraida) {
      fechaListaElement.textContent = `Según Lista ${fechaExtraida}`;
      fechaListaElement.style.fontSize = "small";
      fechaListaElement.style.textAlign = "center";
      console.log("Fecha extraída del archivo:", fechaExtraida);
    } else {
      console.log("No se pudo extraer fecha del nombre del archivo:", currentJsonFileName);
    }
  };

  // Inicializamos la aplicación
  await initializeProducts();
  fetchDollarPrice();
  searchInput.focus();
});