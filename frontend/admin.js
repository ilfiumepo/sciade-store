const ordersRoot = document.querySelector("[data-orders]");
const refreshButton = document.querySelector("[data-refresh-orders]");
const logoutButton = document.querySelector("[data-logout]");
const emptyMessage = document.querySelector("[data-empty-orders]");
const productsRoot = document.querySelector("[data-admin-products]");
const productForm = document.querySelector("[data-product-form]");
const productMessage = document.querySelector("[data-product-message]");
const productResetButton = document.querySelector("[data-product-reset]");

let products = [];

const formatPrice = (value) => `€${Number(value).toFixed(0)}`;
const formatDate = (value) =>
  new Intl.DateTimeFormat("it", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

function renderOrders(orders) {
  emptyMessage.hidden = orders.length > 0;
  ordersRoot.innerHTML = orders
    .map(
      (order) => `
        <article class="order-card">
          <div class="order-card-header">
            <div>
              <p class="eyebrow">Nuovo ordine</p>
              <h2>${order.customer.name}</h2>
              <p>${formatDate(order.createdAt)}</p>
            </div>
            <div class="order-actions">
              <strong>${formatPrice(order.total)}</strong>
              <button type="button" data-delete-order="${order.id}">
                Rimuovi completato
              </button>
            </div>
          </div>
          <div class="order-grid">
            <section>
              <h3>Prodotti</h3>
              ${order.items
                .map(
                  (item) => `
                    <div class="admin-line">
                      <span>${item.name} × ${item.quantity}</span>
                      <strong>${formatPrice(item.lineTotal)}</strong>
                    </div>
                  `,
                )
                .join("")}
            </section>
            <section>
              <h3>Cliente</h3>
              <p>${order.customer.email}</p>
              <p>${order.customer.phone || "Nessun telefono"}</p>
              <p>${order.customer.address}</p>
            </section>
            <section>
              <h3>Preferenze</h3>
              <p>Consegna: ${order.preferences.delivery}</p>
              <p>Pagamento: ${order.preferences.payment}</p>
              <p>Tempistiche: ${order.preferences.timing}</p>
              <p>Note: ${order.preferences.notes || "Nessuna"}</p>
            </section>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderProducts() {
  productsRoot.innerHTML = products
    .map(
      (product) => `
        <article class="product-admin-card">
          <img src="${product.image}" alt="${product.name}" style="object-position: ${product.position || "center"}" />
          <div>
            <p class="eyebrow">${product.category}</p>
            <h2>${product.name}</h2>
            <p>${product.description}</p>
            <strong>${formatPrice(product.price)}</strong>
          </div>
          <div class="product-admin-actions">
            <button type="button" data-edit-product="${product.id}">Modifica</button>
            <button type="button" data-delete-product="${product.id}">Rimuovi venduto</button>
          </div>
        </article>
      `,
    )
    .join("");
}

async function loadProducts() {
  try {
    const response = await fetch("/api/products");
    if (!response.ok) throw new Error("Impossibile caricare i prodotti");
    const data = await response.json();
    products = data.products;
    renderProducts();
  } catch (error) {
    productsRoot.innerHTML = `
      <article class="order-card">
        <h2>Prodotti non disponibili</h2>
        <p>Controlla che il server Sciadè sia acceso.</p>
      </article>
    `;
  }
}

async function loadOrders() {
  refreshButton.disabled = true;
  refreshButton.textContent = "Aggiornamento...";

  try {
    const response = await fetch("/api/orders");
    if (response.status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (!response.ok) throw new Error("Impossibile caricare gli ordini");
    const data = await response.json();
    renderOrders(data.orders);
  } catch (error) {
    ordersRoot.innerHTML = `
      <article class="order-card">
        <h2>Ordini non disponibili</h2>
        <p>Controlla che il server Sciadè sia acceso.</p>
      </article>
    `;
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Aggiorna";
  }
}

refreshButton.addEventListener("click", loadOrders);

ordersRoot.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest("[data-delete-order]");
  if (!deleteButton) return;

  const orderId = deleteButton.dataset.deleteOrder;
  deleteButton.disabled = true;
  deleteButton.textContent = "Rimozione...";

  try {
    const response = await fetch(`/api/orders/${orderId}`, { method: "DELETE" });
    if (response.status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (!response.ok) throw new Error("Impossibile rimuovere l'ordine");
    await loadOrders();
  } catch (error) {
    deleteButton.disabled = false;
    deleteButton.textContent = "Rimuovi completato";
  }
});

function resetProductForm() {
  productForm.reset();
  productForm.elements.id.value = "";
  productForm.elements.position.value = "center";
  productMessage.textContent = "";
  productForm.querySelector(".submit-order").textContent = "Salva prodotto";
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file) {
      resolve("");
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsDataURL(file);
  });
}

productsRoot.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-product]");
  const deleteButton = event.target.closest("[data-delete-product]");

  if (editButton) {
    const product = products.find((item) => item.id === editButton.dataset.editProduct);
    if (!product) return;

    productForm.elements.id.value = product.id;
    productForm.elements.name.value = product.name;
    productForm.elements.category.value = product.category;
    productForm.elements.price.value = product.price;
    productForm.elements.position.value = product.position || "center";
    productForm.elements.description.value = product.description;
    productForm.elements.imageFile.value = "";
    productForm.querySelector(".submit-order").textContent = "Aggiorna prodotto";
    productMessage.textContent = `Stai modificando ${product.name}. Carica una nuova immagine solo se vuoi sostituirla.`;
    productMessage.style.color = "#6b625d";
    productForm.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  if (deleteButton) {
    const productId = deleteButton.dataset.deleteProduct;
    deleteButton.disabled = true;
    deleteButton.textContent = "Rimozione...";

    try {
      const response = await fetch(`/api/products/${productId}`, { method: "DELETE" });
      if (response.status === 401) {
        window.location.href = "/login.html";
        return;
      }
      if (!response.ok) throw new Error("Impossibile rimuovere il prodotto");
      await loadProducts();
      resetProductForm();
    } catch (error) {
      deleteButton.disabled = false;
      deleteButton.textContent = "Rimuovi venduto";
    }
  }
});

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  productMessage.textContent = "Salvataggio prodotto...";
  productMessage.style.color = "#6b625d";

  const formData = new FormData(productForm);
  const productId = formData.get("id");
  const imageFile = productForm.elements.imageFile.files[0];
  const existingProduct = products.find((product) => product.id === productId);

  try {
    const payload = {
      id: productId || undefined,
      name: formData.get("name"),
      category: formData.get("category"),
      price: formData.get("price"),
      image: existingProduct?.image || "",
      imageData: await fileToDataUrl(imageFile),
      position: formData.get("position") || "center",
      description: formData.get("description"),
    };

    const response = await fetch(productId ? `/api/products/${productId}` : "/api/products", {
      method: productId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      window.location.href = "/login.html";
      return;
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Impossibile salvare il prodotto");
    }

    await loadProducts();
    resetProductForm();
    productMessage.textContent = "Prodotto salvato.";
    productMessage.style.color = "#26716f";
  } catch (error) {
    productMessage.textContent = error.message || "Impossibile salvare il prodotto.";
    productMessage.style.color = "#bc5965";
  }
});

productResetButton.addEventListener("click", resetProductForm);

logoutButton.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login.html";
});

loadOrders();
loadProducts();
resetProductForm();
