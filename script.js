document.addEventListener("DOMContentLoaded", () => {
  const productTable = document.querySelector("#productTable tbody");
  const searchInput = document.getElementById("searchInput");
  const loader = document.getElementById("loader");
  let products = [];
  const currentJsonFileName = "Lista_Precio_Julio_2024_json_compres.gz"; // Actualiza este nombre cada mes

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

      let done, value;
      while ((({ value, done } = await reader.read()), !done)) {
        jsonText += decoder.decode(value, { stream: true });
      }
      jsonText += decoder.decode(); // Decodes any remaining bytes

      products = JSON.parse(jsonText);
      sessionStorage.setItem("products", JSON.stringify(products));
      sessionStorage.setItem("jsonFileName", currentJsonFileName);
      displayProducts(products);
    } catch (error) {
      console.error("Error al cargar los productos:", error);
    }

    loader.classList.add("hidden");
  };

  const displayProducts = (products) => {
    productTable.innerHTML = ""; // Limpiar el contenido de la tabla
    if (products.length === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 6; // Asumiendo que tienes 6 columnas
      cell.textContent = "No se ha encontrado el producto.";
      cell.style.textAlign = "center";
      row.appendChild(cell);
      productTable.appendChild(row);
      return;
    }
    products.forEach((product) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${product.producto}</td>
        <td>${product.detalle}</td>
        <td>${product.marca}</td>
        <td>${product.unidad}</td>
        <td>${product.moneda}</td>
        <td>${product.precio}</td>
      `;
      productTable.appendChild(row);
    });
  };

  const filterProducts = (searchTerm, products) => {
    return products.filter(
      (product) =>
        product.producto.toLowerCase().includes(searchTerm) ||
        product.detalle.toLowerCase().includes(searchTerm) ||
        product.marca.toLowerCase().includes(searchTerm)
    );
  };

  const initializeProducts = () => {
    const storedProducts = sessionStorage.getItem("products");
    const storedJsonFileName = sessionStorage.getItem("jsonFileName");

    if (storedProducts && storedJsonFileName === currentJsonFileName) {
      products = JSON.parse(storedProducts);
      displayProducts(products);
    } else {
      fetchAndDecompressProducts();
    }
  };

  searchInput.addEventListener("input", () => {
    const searchTerm = searchInput.value.toLowerCase();
    const filteredProducts = filterProducts(searchTerm, products);
    productTable.innerHTML = "";
    displayProducts(filteredProducts);
  });

  initializeProducts();
});
