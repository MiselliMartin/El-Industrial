document.addEventListener("DOMContentLoaded", () => {
  //let currentPage = 1;
  //const productContainer = document.getElementById("productContainer");
  const productTable = document.querySelector("#productTable tbody");
  const searchInput = document.getElementById("searchInput");
  const loader = document.getElementById("loader");
  let products;
  /*
  const fetchAndDecompressProducts = async (page) => {
    loader.classList.remove("hidden");
    try {
      const response = await fetch(`productos${page}.json.gz`);
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const compressedStream = response.body;
      const decompressedStream = compressedStream.pipeThrough(
        new DecompressionStream("gzip")
      );
      const reader = decompressedStream.getReader();
      let decoder = new TextDecoder("utf-8");
      let jsonText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        jsonText += decoder.decode(value, { stream: true });
      }

      jsonText += decoder.decode();
      const data = JSON.parse(jsonText);
      displayProducts(data);
    } catch (error) {
      console.error("Error al cargar los productos:", error);
    }
    loader.classList.add("hidden");
  };
*/

  const fetchProducts = async () => {
    loader.classList.remove("hidden");
    try {
      const response = await fetch("products.json");
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const data = await response.json();
      products = data;
      displayProducts(data);
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
          <td>${product.Articulo}</td>
          <td>${product.Detalle}</td>
          <td>${product.Marca}</td>
          <td>${product.Unidad}</td>
          <td>${product.Dto}</td>
          <td>${product.PLista}</td>
      `;
      productTable.appendChild(row);
    });
  };

  //Articulo Detalle Marca	IVA	Unidad	Dto.	Mon.	P/Lista

  const handleScroll = () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
      currentPage++;
      fetchAndDecompressProducts(currentPage);
    }
  };

  const filterProducts = (searchTerm, products) => {
    return products.filter(
      (product) =>
        product.Articulo.toLowerCase().includes(searchTerm) ||
        product.Detalle.toLowerCase().includes(searchTerm) ||
        product.Marca.toLowerCase().includes(searchTerm)
    );
    /*
    let filteredProductsDetalle = products.filter((product) =>
      product.Detalle.toLowerCase().includes(searchTerm.toLowerCase())
    );
    if (filterProducts.length < 1) return filteredProductsDetalle;
    else {
      return products.filter((product) =>
        product.Marca.toLowerCase().includes(searchTerm.toLowerCase())
      ); // No hay coincidencias, devuelve todos los productos
      
    }*/
  };

  fetchProducts();

  searchInput.addEventListener("input", () => {
    const searchTerm = searchInput.value.toLowerCase();
    const filteredProducts = filterProducts(searchTerm, products);
    productTable.innerHTML = "";
    displayProducts(
      filteredProducts ? filteredProducts : "No se han encontrado productos"
    );
  });

  window.addEventListener("scroll", handleScroll);
});
