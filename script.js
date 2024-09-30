document.addEventListener("DOMContentLoaded", () => {
  const productTable = document.querySelector("#productTable tbody");
  const searchInput = document.getElementById("searchInput");
  const loader = document.getElementById("loader");
  const themeToggle = document.getElementById("themeToggle");
  const dollarDateElement = document.getElementById("dollarDate");
  const dollarPriceElement = document.getElementById("dollarPrice");

  //IMPORTANTE CAMBIAR SI SE SUBE UN NUEVO JSON ↓
  const currentJsonFileName = "lista_precio_original_27-09-2024_json_compres.gz";
  //IMPORTANTE CAMBIAR SI SE SUBE UN NUEVO JSON ↑

  let searchTimeout;
  let products = [];

  const fetchDollarPrice = async () => {
    try {
      const response = await fetch("https://dolarapi.com/v1/ambito/dolares/oficial");
      const data = await response.json();
      console.log(data)
      //const date = new Date(data.fechaActualizacion);
      //dollarDateElement.textContent = date.toLocaleDateString();
      dollarPriceElement.textContent = `$${data.venta.toFixed(2)}`; //
    } catch (error) {
      console.error("Error al obtener el precio del dólar:", error);
      //dollarDateElement.textContent = "N/A";
      dollarPriceElement.textContent = "N/A";
    }
  };

  const fetchAndDecompressProducts = async () => {
    console.log("Fetching and decompressing products...");
    loader.classList.remove("hidden");
    try {
      const response = await fetch(currentJsonFileName);
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const compressedStream = response.body.pipeThrough(
        new DecompressionStream("gzip")
      );
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
      // sessionStorage.setItem("products", JSON.stringify(products));
      // sessionStorage.setItem("jsonFileName", currentJsonFileName);

      localStorage.removeItem("products");
      localStorage.removeItem("jsonFileName");
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
      row.innerHTML = `
        <td data-label="Producto">${product.producto}</td>
        <td data-label="Detalle">${product.detalle}</td>
        <td data-label="Marca">${product.marca}</td>
        <td data-label="Un/Mts">${product.unidad === "UN" ? "Un" : "Mts"}</td>
        <td data-label="Precio">${product.moneda} ${product.precio}</td>
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

  const initializeProducts = () => {
    const storedJsonFileName = sessionStorage.getItem("jsonFileName");
    if (storedJsonFileName === currentJsonFileName) {
      const storedProducts = sessionStorage.getItem("products");
      products = JSON.parse(storedProducts);
      displayProducts(products);
    } else {
      fetchAndDecompressProducts();
    }
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

  initializeProducts();
  fetchDollarPrice();
  searchInput.focus();

  const extractDateFromFileName = (fileName) => {
    const datePattern = /\d{2}-\d{2}-\d{4}/;
    const match = fileName.match(datePattern);
    return match ? match[0] : null;
  };

  const displayDate = () => {
    const fechaListaElement = document.getElementById("fechaLista");
    const fechaExtraida = extractDateFromFileName(currentJsonFileName);
    
    if (fechaExtraida) {
      fechaListaElement.textContent = `Según Lista ${fechaExtraida}`;
      fechaListaElement.style.fontSize = "small";
      fechaListaElement.style.textAlign = "center";
    }
  };

  // Llamamos a la función displayDate para mostrar la fecha.
  displayDate();

});