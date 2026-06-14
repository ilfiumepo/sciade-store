let products = [];

const state = {
  filter: "all",
  cart: JSON.parse(localStorage.getItem("sciadeCart") || "{}"),
};

const formatPrice = (value) => `€${value.toFixed(0)}`;

const productGrid = document.querySelector("[data-products]");
const cartPanel = document.querySelector("[data-cart-panel]");
const cartItems = document.querySelector("[data-cart-items]");
const cartTotal = document.querySelector("[data-cart-total]");
const cartCount = document.querySelector("[data-cart-count]");
const miniCart = document.querySelector("[data-mini-cart]");
const scrim = document.querySelector("[data-scrim]");
const formMessage = document.querySelector("[data-form-message]");
const accountLinks = document.querySelectorAll("[data-account-link]");
const checkoutAuth = document.querySelector("[data-checkout-auth]");
const guestCheckoutButton = document.querySelector("[data-guest-checkout]");
const checkoutIdentity = document.querySelector("[data-checkout-identity]");
const accountCheckoutNote = document.querySelector("[data-account-checkout-note]");
let currentSession = { authenticated: false, role: "guest", email: "" };

function cartEntries() {
  return Object.entries(state.cart)
    .map(([id, quantity]) => {
      const product = products.find((item) => item.id === id);
      return product ? { ...product, quantity } : null;
    })
    .filter((item) => item && item.quantity > 0);
}

function cartTotalValue() {
  return cartEntries().reduce((sum, item) => sum + item.price * item.quantity, 0);
}

function cartQuantity() {
  return cartEntries().reduce((sum, item) => sum + item.quantity, 0);
}

function saveCart() {
  localStorage.setItem("sciadeCart", JSON.stringify(state.cart));
}

function renderProducts() {
  if (!productGrid) return;

  const visible = products.filter(
    (product) => state.filter === "all" || product.category === state.filter,
  );

  if (visible.length === 0) {
    productGrid.innerHTML = `
      <article class="product-card empty-product-card">
        <div class="product-body">
          <h3>Non ci sono ancora prodotti in questa categoria.</h3>
          <p>Torna presto per nuovi pezzi fatti a mano.</p>
        </div>
      </article>
    `;
    return;
  }

  productGrid.innerHTML = visible
    .map(
      (product) => `
        <article class="product-card" data-category="${product.category}">
          <figure>
            <img src="${product.image}" alt="${product.name}" style="object-position: ${product.position || "center"}" />
          </figure>
          <div class="product-body">
            <div class="product-meta">
              <div>
                <h3>${product.name}</h3>
                <p>${product.description}</p>
              </div>
              <span class="product-price">${formatPrice(product.price)}</span>
            </div>
            <button class="add-button" type="button" data-add="${product.id}">
              Aggiungi al carrello
            </button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderCart() {
  const entries = cartEntries();
  const quantity = cartQuantity();
  cartCount.textContent = quantity;
  cartCount.classList.toggle("is-hidden", quantity === 0);
  cartTotal.textContent = formatPrice(cartTotalValue());

  if (entries.length === 0) {
    cartItems.innerHTML = "<p>Il carrello è vuoto.</p>";
    if (miniCart) miniCart.innerHTML = "<p>Il carrello è vuoto.</p>";
    return;
  }

  cartItems.innerHTML = entries
    .map(
      (item) => `
        <div class="cart-line">
          <div>
            <strong>${item.name}</strong>
            <small>${formatPrice(item.price)} ciascuno</small>
            <div class="quantity-tools" aria-label="Quantità per ${item.name}">
              <button type="button" data-decrease="${item.id}" aria-label="Diminuisci ${item.name}">−</button>
              <span>${item.quantity}</span>
              <button type="button" data-increase="${item.id}" aria-label="Aumenta ${item.name}">+</button>
            </div>
          </div>
          <strong>${formatPrice(item.price * item.quantity)}</strong>
        </div>
      `,
    )
    .join("");

  if (!miniCart) return;

  miniCart.innerHTML = `
    ${entries
      .map(
        (item) => `
          <div class="mini-cart-row">
            <span>
              <strong>${item.name}</strong>
              <small>Qtà ${item.quantity}</small>
            </span>
            <strong>${formatPrice(item.price * item.quantity)}</strong>
          </div>
        `,
      )
      .join("")}
    <div class="mini-cart-row">
      <span><strong>Totale</strong></span>
      <strong>${formatPrice(cartTotalValue())}</strong>
    </div>
  `;
}

function setCartOpen(isOpen) {
  cartPanel.classList.toggle("is-open", isOpen);
  scrim.classList.toggle("is-open", isOpen);
  cartPanel.setAttribute("aria-hidden", String(!isOpen));
}

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  const increaseButton = event.target.closest("[data-increase]");
  const decreaseButton = event.target.closest("[data-decrease]");

  if (addButton) {
    const id = addButton.dataset.add;
    state.cart[id] = (state.cart[id] || 0) + 1;
    saveCart();
    renderCart();
    setCartOpen(true);
  }

  if (increaseButton) {
    const id = increaseButton.dataset.increase;
    state.cart[id] = (state.cart[id] || 0) + 1;
    saveCart();
    renderCart();
  }

  if (decreaseButton) {
    const id = decreaseButton.dataset.decrease;
    state.cart[id] = Math.max((state.cart[id] || 0) - 1, 0);
    saveCart();
    renderCart();
  }

  if (event.target.closest("[data-cart-toggle]")) setCartOpen(true);
  if (event.target.closest("[data-cart-close]") || event.target === scrim) setCartOpen(false);
  if (event.target.closest("[data-cart-close-link]")) setCartOpen(false);
});

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((tab) => {
      tab.classList.toggle("is-active", tab === button);
    });
    renderProducts();
  });
});

async function loadProducts() {
  try {
    const response = await fetch("/api/products");
    if (!response.ok) throw new Error("Impossibile caricare i prodotti");
    const data = await response.json();
    products = data.products;
  } catch (error) {
    if (productGrid) {
      productGrid.innerHTML = `
        <article class="product-card empty-product-card">
          <div class="product-body">
            <h3>Prodotti non disponibili</h3>
            <p>Controlla che il server Sciadè sia acceso.</p>
          </div>
        </article>
      `;
    }
  }
}

async function loadSession() {
  try {
    const response = await fetch("/api/session");
    if (!response.ok) return;
    const session = await response.json();
    currentSession = session;
    if (session.authenticated) {
      accountLinks.forEach((link) => {
        link.textContent = "Account";
        link.href = "account.html";
      });
    }
  } catch (error) {
    // Public shop should keep working even if session state is unavailable.
  }
}

const checkoutForm = document.querySelector("[data-checkout-form]");

function showCheckoutForm() {
  if (checkoutAuth) checkoutAuth.classList.add("is-hidden");
  if (checkoutForm) checkoutForm.classList.remove("is-hidden");
}

async function setupCheckoutIdentity() {
  if (!checkoutForm) return;

  if (!currentSession.authenticated) {
    if (checkoutAuth) checkoutAuth.classList.remove("is-hidden");
    checkoutForm.classList.add("is-hidden");
    return;
  }

  try {
    const response = await fetch("/api/account");
    if (!response.ok) throw new Error("Impossibile caricare l'account");
    const data = await response.json();
    const user = data.user;
    checkoutForm.elements.firstName.value = user.firstName || "";
    checkoutForm.elements.lastName.value = user.lastName || "";
    checkoutForm.elements.email.value = user.email || "";
    checkoutIdentity.classList.add("is-hidden");
    accountCheckoutNote.textContent = `Stiamo usando i dati del tuo account Sciadè: ${user.firstName} ${user.lastName} (${user.email}).`;
    accountCheckoutNote.classList.remove("is-hidden");
    showCheckoutForm();
  } catch (error) {
    if (checkoutAuth) checkoutAuth.classList.remove("is-hidden");
    checkoutForm.classList.add("is-hidden");
  }
}

if (guestCheckoutButton) {
  guestCheckoutButton.addEventListener("click", showCheckoutForm);
}

if (checkoutForm) {
  checkoutForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const entries = cartEntries();

    if (entries.length === 0) {
      formMessage.textContent = "Aggiungi almeno un prodotto prima di inviare l'ordine.";
      formMessage.style.color = "#bc5965";
      return;
    }

    const formData = new FormData(event.currentTarget);
    const firstName = String(formData.get("firstName") || "").trim();
    const lastName = String(formData.get("lastName") || "").trim();
    const name = `${firstName} ${lastName}`.trim();

    const order = {
      customer: {
        name,
        email: formData.get("email"),
        phone: formData.get("phone"),
        address: formData.get("address"),
      },
      preferences: {
        delivery: formData.get("delivery"),
        payment: formData.get("payment"),
        timing: formData.get("timing"),
        notes: formData.get("notes"),
      },
      items: entries.map((item) => ({
        id: item.id,
        name: item.name,
        category: item.category,
        price: item.price,
        quantity: item.quantity,
        lineTotal: item.price * item.quantity,
      })),
      total: cartTotalValue(),
    };

    formMessage.textContent = "Salvataggio ordine...";
    formMessage.style.color = "#6b625d";

    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(order),
      });

      if (!response.ok) throw new Error("Salvataggio ordine non riuscito");
      await response.json();
    } catch (error) {
      formMessage.textContent =
        "Non è stato possibile salvare l'ordine. Controlla che il server Sciadè sia acceso.";
      formMessage.style.color = "#bc5965";
      return;
    }

    formMessage.textContent = `Grazie, ${name}. La tua richiesta d'ordine è stata salvata.`;
    formMessage.style.color = "#26716f";
    state.cart = {};
    saveCart();
    renderCart();
    event.currentTarget.reset();
  });
}

async function init() {
  await loadSession();
  await loadProducts();
  await setupCheckoutIdentity();
  renderProducts();
  renderCart();
}

init();
