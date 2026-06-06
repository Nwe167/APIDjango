const {
  bootstrapShell,
  apiRequest,
  bytesToHuman,
  formatDate,
  escapeHtml,
  renderToast,
  fetchAllPages,
} = window.CloudVault;

async function loadProducts() {
  try {
    const response = await fetch(
      "http://127.0.0.1:8000/api/v1/apiproducts/products/",
    );
    const data = await response.json();
    return data.results || [];
  } catch (error) {
    console.error("Failed to load products:", error);
    renderToast("Failed to load products", "danger");
    return [];
  }
}

function renderProductsGrid(products) {
  const target = document.querySelector("#productsGrid");
  if (!target) return;

  target.innerHTML = products.length
    ? products
        .map(
          (product) => `
        <div class="col-12 col-sm-6 col-md-4 col-lg-3">
            <div class="card product-card h-100 shadow-sm">
                <div class="product-image" style="background-image: url('${escapeHtml(product.productImage || "")}')">
                    ${!product.productImage ? `<div class="placeholder"><i class="bi bi-image"></i></div>` : ""}
                </div>
                <div class="card-body d-flex flex-column">
                    <h6 class="card-title text-truncate">${escapeHtml(product.productName)}</h6>
                    <p class="card-text text-secondary small mb-3">${escapeHtml(product.productImage || "No image")}</p>
                    <div class="d-flex justify-content-between align-items-center mt-auto">
                        <span class="fw-bold text-primary">$${parseFloat(product.price).toFixed(2)}</span>
                        <small class="text-secondary">${formatDate(product.productDate)}</small>
                    </div>
                </div>
                <div class="card-footer bg-transparent border-top">
                    <button class="btn btn-sm btn-primary w-100" data-product-id="${product.id}" data-action="add-to-cart">
                        <i class="bi bi-cart-plus"></i> Add to Cart
                    </button>
                </div>
            </div>
        </div>
    `,
        )
        .join("")
    : '<div class="col-12"><div class="empty-state">No products available.</div></div>';

  // Bind cart buttons
  target.querySelectorAll('[data-action="add-to-cart"]').forEach((button) => {
    button.addEventListener("click", async (event) => {
      const productId = event.currentTarget.getAttribute("data-product-id");
      const product = products.find((p) => String(p.id) === String(productId));
      if (product) {
        addProductToCart(product);
      }
    });
  });
}

function renderProductsTable(products) {
  const target = document.querySelector("#productsTable");
  if (!target) return;

  target.innerHTML = products.length
    ? products
        .map(
          (product) => `
        <tr>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <img src="${escapeHtml(product.productImage || "")}" alt="${escapeHtml(product.productName)}" 
                         style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">
                    <div>
                        <div class="fw-bold">${escapeHtml(product.productName)}</div>
                        <small class="text-secondary">ID: ${escapeHtml(product.id)}</small>
                    </div>
                </div>
            </td>
            <td>$${parseFloat(product.price).toFixed(2)}</td>
            <td>${formatDate(product.productDate)}</td>
            <td>
                <button class="btn btn-sm btn-primary" data-product-id="${product.id}" data-action="add-to-cart">
                    Add to Cart
                </button>
            </td>
        </tr>
    `,
        )
        .join("")
    : '<tr><td colspan="4"><div class="empty-state">No products available.</div></td></tr>';

  target.querySelectorAll('[data-action="add-to-cart"]').forEach((button) => {
    button.addEventListener("click", async (event) => {
      const productId = event.currentTarget.getAttribute("data-product-id");
      const product = products.find((p) => String(p.id) === String(productId));
      if (product) {
        addProductToCart(product);
      }
    });
  });
}

function addProductToCart(product) {
  let cart = JSON.parse(localStorage.getItem("shopping_cart") || "[]");

  const existingItem = cart.find((item) => item.id === product.id);
  if (existingItem) {
    existingItem.quantity += 1;
  } else {
    cart.push({
      id: product.id,
      productName: product.productName,
      price: product.price,
      productImage: product.productImage,
      quantity: 1,
    });
  }

  localStorage.setItem("shopping_cart", JSON.stringify(cart));
  renderToast(`${product.productName} added to cart`, "success");
  updateCartBadge();
}

function updateCartBadge() {
  const cart = JSON.parse(localStorage.getItem("shopping_cart") || "[]");
  const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
  const badge = document.querySelector("#cartBadge");
  if (badge) {
    badge.textContent = String(totalItems);
    badge.classList.toggle("d-none", totalItems === 0);
  }
}

function getShoppingCart() {
  return JSON.parse(localStorage.getItem("shopping_cart") || "[]");
}

function clearShoppingCart() {
  localStorage.removeItem("shopping_cart");
  updateCartBadge();
}

function renderShoppingCart() {
  const cart = getShoppingCart();
  const target = document.querySelector("#cartItems");
  const totalTarget = document.querySelector("#cartTotal");

  if (!target) return;

  let total = 0;
  target.innerHTML = cart.length
    ? cart
        .map((item) => {
          const itemTotal = parseFloat(item.price) * item.quantity;
          total += itemTotal;
          return `
            <div class="cart-item border-bottom pb-3 mb-3">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div class="d-flex gap-3">
                        ${
                          item.productImage
                            ? `<img src="${escapeHtml(item.productImage)}" alt="${escapeHtml(item.productName)}" 
                             style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;">`
                            : '<div style="width: 60px; height: 60px; background: #f0f0f0; border-radius: 4px;"></div>'
                        }
                        <div>
                            <div class="fw-bold">${escapeHtml(item.productName)}</div>
                            <div class="text-secondary small">$${parseFloat(item.price).toFixed(2)} x ${item.quantity}</div>
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">$${itemTotal.toFixed(2)}</div>
                        <button class="btn btn-sm btn-outline-danger mt-2" data-product-id="${item.id}" data-action="remove-from-cart">
                            Remove
                        </button>
                    </div>
                </div>
            </div>
        `;
        })
        .join("")
    : '<div class="empty-state py-4">Your cart is empty.</div>';

  if (totalTarget) {
    totalTarget.textContent = `$${total.toFixed(2)}`;
  }

  // Bind remove buttons
  target
    .querySelectorAll('[data-action="remove-from-cart"]')
    .forEach((button) => {
      button.addEventListener("click", (event) => {
        const productId = event.currentTarget.getAttribute("data-product-id");
        removeProductFromCart(productId);
      });
    });
}

function removeProductFromCart(productId) {
  let cart = JSON.parse(localStorage.getItem("shopping_cart") || "[]");
  cart = cart.filter((item) => String(item.id) !== String(productId));
  localStorage.setItem("shopping_cart", JSON.stringify(cart));
  renderToast("Item removed from cart", "info");
  updateCartBadge();
  renderShoppingCart();
}

async function initProductsPage() {
  await bootstrapShell("products", { sidebar: false, requireAuth: false });
  const products = await loadProducts();

  // Render based on view mode
  if (document.querySelector("#productsGrid")) {
    renderProductsGrid(products);
  }
  if (document.querySelector("#productsTable")) {
    renderProductsTable(products);
  }

  updateCartBadge();
}

// Export for use in other pages
window.CloudVaultProducts = {
  loadProducts,
  renderProductsGrid,
  renderProductsTable,
  addProductToCart,
  updateCartBadge,
  getShoppingCart,
  clearShoppingCart,
  renderShoppingCart,
  removeProductFromCart,
};
