console.log("[api.js] Loading...");

const API_BASE = "/api/v1";
const TOKEN_KEY = "cloudvault_token";
const REFRESH_KEY = "cloudvault_refresh_token";
const THEME_KEY = "cloudvault_theme";

if (typeof axios === "undefined") {
  throw new Error("Axios must be loaded before api.js");
}

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: {
    "Content-Type": "application/json",
  },
});

function getToken() {
  // Check both keys for compatibility
  return (
    localStorage.getItem(TOKEN_KEY) || localStorage.getItem("auth_token") || ""
  );
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY) || "";
}

function setAuthTokens(payload) {
  if (payload.token) {
    localStorage.setItem(TOKEN_KEY, payload.token);
  }

  if (payload.access) {
    localStorage.setItem(TOKEN_KEY, payload.access);
  }

  if (payload.refresh) {
    localStorage.setItem(REFRESH_KEY, payload.refresh);
  }
}

function clearAuthTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function getAuthHeaderValue(token) {
  if (!token) {
    return "";
  }

  return token.includes(".") ? `Bearer ${token}` : `Token ${token}`;
}

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = getAuthHeaderValue(token);
  }
  return config;
});

function apiResponse(data) {
  if (data && Array.isArray(data.results)) {
    return data;
  }
  return data;
}

async function apiRequest(method, url, data = null, config = {}) {
  const response = await apiClient.request({
    method,
    url,
    data,
    ...config,
  });
  return apiResponse(response.data);
}

async function fetchAllPages(url, config = {}) {
  const items = [];
  let nextUrl = url;

  while (nextUrl) {
    const response = await apiRequest("get", nextUrl, null, config);
    if (Array.isArray(response)) {
      items.push(...response);
      break;
    }

    items.push(...(response.results || []));
    nextUrl = response.next || "";
  }

  return items;
}

async function loadComponent(selector, path) {
  const target = document.querySelector(selector);
  if (!target) {
    return;
  }

  const response = await fetch(path, { cache: "no-store" });
  target.innerHTML = await response.text();
}

function setTheme(theme) {
  const resolvedTheme = theme || localStorage.getItem(THEME_KEY) || "light";
  localStorage.setItem(THEME_KEY, resolvedTheme);
  document.documentElement.setAttribute("data-bs-theme", resolvedTheme);
  return resolvedTheme;
}

function toggleTheme() {
  const currentTheme =
    document.documentElement.getAttribute("data-bs-theme") || "light";
  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  setTheme(nextTheme);
  return nextTheme;
}

function setupThemeToggle() {
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const theme = toggleTheme();
      renderToast(`Theme switched to ${theme}`, "info");
    });
  });
}

function setupSidebarToggle() {
  document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", () =>
      document.body.classList.add("sidebar-open"),
    );
  });

  document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
    button.addEventListener("click", () =>
      document.body.classList.remove("sidebar-open"),
    );
  });

  const backdrop = document.querySelector(".sidebar-backdrop");
  if (backdrop) {
    backdrop.addEventListener("click", () =>
      document.body.classList.remove("sidebar-open"),
    );
  }
}

function setupLogoutButtons() {
  document.querySelectorAll("[data-logout-btn]").forEach((button) => {
    button.addEventListener("click", () => {
      clearAuthTokens();
      renderToast("Logged out successfully", "success");
      window.location.href = "login.html";
    });
  });
}

async function hydrateAccountSummary() {
  if (!isAuthenticated()) {
    return;
  }

  try {
    const [profile, preference, notifications] = await Promise.allSettled([
      apiRequest("get", "/users/profile/me/"),
      apiRequest("get", "/users/preferences/me/"),
      apiRequest("get", "/users/notifications/"),
    ]);

    const profileData = profile.status === "fulfilled" ? profile.value : null;
    const preferenceData =
      preference.status === "fulfilled" ? preference.value : null;
    const notificationData =
      notifications.status === "fulfilled" ? notifications.value : null;

    const displayName = profileData?.user
      ? [profileData.user.first_name, profileData.user.last_name]
          .filter(Boolean)
          .join(" ")
      : "User";
    const email = profileData?.user?.email || "user@example.com";
    const initials =
      (displayName || "User")
        .split(" ")
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase() || "U";

    document
      .querySelectorAll("#navUserName, #sidebarUserName")
      .forEach((node) => {
        node.textContent = displayName || "User";
      });

    document.querySelectorAll("#sidebarUserEmail").forEach((node) => {
      node.textContent = email;
    });

    document.querySelectorAll("#navAvatar, #sidebarAvatar").forEach((node) => {
      node.textContent = initials;
    });

    if (preferenceData?.theme) {
      setTheme(
        preferenceData.theme === "system"
          ? window.matchMedia("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light"
          : preferenceData.theme,
      );
    }

    const unreadCount = (
      notificationData?.results ||
      notificationData ||
      []
    ).filter((item) => !item.is_read).length;
    const badge = document.querySelector("#navUnreadBadge");
    if (badge) {
      badge.textContent = String(unreadCount);
      badge.classList.toggle("d-none", unreadCount === 0);
    }

    const list = document.querySelector("#navNotificationList");
    if (list && notificationData) {
      const notificationsList =
        notificationData.results || notificationData || [];
      list.innerHTML =
        notificationsList
          .slice(0, 5)
          .map(
            (item) => `
                <button class="list-group-item list-group-item-action notification-row" type="button" data-notification-id="${item.id}">
                    <div class="d-flex gap-3 align-items-start">
                        <div class="file-icon"><i class="bi bi-bell"></i></div>
                        <div class="flex-grow-1 text-start">
                            <div class="fw-semibold">${escapeHtml(item.title)}</div>
                            <small class="text-secondary d-block">${escapeHtml(item.body || "No description")}</small>
                        </div>
                        ${item.is_read ? "" : '<span class="notification-dot mt-2"></span>'}
                    </div>
                </button>
            `,
          )
          .join("") ||
        '<div class="p-3 text-secondary">No notifications yet.</div>';
    }

    const markAllReadButton = document.querySelector("#markAllReadBtn");
    if (markAllReadButton && !markAllReadButton.dataset.bound) {
      markAllReadButton.dataset.bound = "true";
      markAllReadButton.addEventListener("click", async () => {
        try {
          await apiRequest("post", "/users/notifications/mark_all_as_read/");
          renderToast("All notifications marked as read", "success");
          await hydrateAccountSummary();
        } catch (error) {
          renderToast("Unable to update notifications", "danger");
        }
      });
    }

    const storageMeta = document.querySelector("#sidebarStorageMeta");
    const storageBar = document.querySelector("#sidebarStorageBar");
    const storageBadge = document.querySelector("#sidebarStorageBadge");
    if (storageMeta && profileData) {
      const usage = Number(profileData.storage_quota_usage_bytes || 0);
      const limit = Number(profileData.storage_quota_limit_bytes || 0);
      const percent =
        limit > 0 ? Math.min(100, Math.round((usage / limit) * 100)) : 0;
      storageMeta.textContent = `${formatBytes(usage)} used`;
      storageBar.style.width = `${percent}%`;
      storageBar.setAttribute("aria-valuenow", String(percent));
      storageBadge.textContent = `${percent}%`;
    }
  } catch (error) {
    console.warn("Account summary hydration skipped:", error);
  }
}

async function bootstrapShell(activePage, options = {}) {
  if (options.requireAuth !== false && !isAuthenticated()) {
    window.location.href = "login.html";
    return;
  }

  setTheme();
  if (document.querySelector("#navbarSlot")) {
    await loadComponent("#navbarSlot", "components/navbar.html");
  }

  if (options.sidebar !== false && document.querySelector("#sidebarSlot")) {
    await loadComponent("#sidebarSlot", "components/sidebar.html");
  }

  if (!document.querySelector(".sidebar-backdrop")) {
    const backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    document.body.appendChild(backdrop);
  }

  setupThemeToggle();
  setupSidebarToggle();
  setupLogoutButtons();
  highlightNav(activePage);

  // When the bell dropdown opens, mark all notifications read and refresh summary
  try {
    const notifToggle = document.querySelector(
      'button[aria-label="Notifications"]',
    );
    if (notifToggle) {
      const dropdownRoot = notifToggle.closest(".dropdown");
      if (dropdownRoot && !dropdownRoot.dataset.notifBound) {
        dropdownRoot.dataset.notifBound = "true";
        dropdownRoot.addEventListener("show.bs.dropdown", async () => {
          try {
            await apiRequest("post", "/users/notifications/mark_all_as_read/");
            await hydrateAccountSummary();
          } catch (e) {
            /* ignore */
          }
        });
      }
    }
  } catch (e) {
    /* ignore */
  }

  const globalSearchForm = document.querySelector("#globalSearchForm");
  const globalSearchInput = document.querySelector("#globalSearchInput");
  if (globalSearchForm && globalSearchInput) {
    globalSearchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = globalSearchInput.value.trim();
      window.location.href = `files.html?q=${encodeURIComponent(query)}`;
    });
  }

  await hydrateAccountSummary();
}

function highlightNav(activePage) {
  document.querySelectorAll("[data-nav-item]").forEach((link) => {
    link.classList.toggle("active", link.dataset.navItem === activePage);
  });
}

function isAuthenticated() {
  return Boolean(getToken());
}

function enforceAuthentication() {
  // Check if user is authenticated, redirect to login if not
  if (!isAuthenticated()) {
    window.location.href = "/frontend/login/";
  }
}

function bytesToHuman(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getFileIconClass(fileName, mimeType = "") {
  const name = String(fileName || "").toLowerCase();
  const mime = String(mimeType || "").toLowerCase();

  if (mime.includes("folder") || name.endsWith("/")) return "bi-folder2";
  if (mime.includes("image/") || /\.(png|jpe?g|gif|webp|svg)$/.test(name))
    return "bi-file-earmark-image";
  if (mime.includes("pdf") || name.endsWith(".pdf"))
    return "bi-file-earmark-pdf";
  if (mime.includes("spreadsheet") || /\.(csv|xls|xlsx)$/.test(name))
    return "bi-file-earmark-spreadsheet";
  if (mime.includes("presentation") || /\.(ppt|pptx)$/.test(name))
    return "bi-file-earmark-slides";
  if (mime.includes("video/") || /\.(mp4|mov|webm|mkv)$/.test(name))
    return "bi-file-earmark-play";
  if (mime.includes("audio/") || /\.(mp3|wav|ogg)$/.test(name))
    return "bi-file-earmark-music";
  if (mime.includes("zip") || /\.(zip|rar|7z|tar|gz)$/.test(name))
    return "bi-file-earmark-zip";
  if (mime.includes("text/") || /\.(txt|md|json|xml|csv)$/.test(name))
    return "bi-file-earmark-text";
  return "bi-file-earmark";
}

async function uploadFile(path, formData, config = {}) {
  const response = await axios.post(`${API_BASE}${path}`, formData, {
    headers: {
      // DON'T set Content-Type header for FormData - let axios handle it with correct boundary
      Authorization: getAuthHeaderValue(getToken()),
    },
    ...config,
  });
  return apiResponse(response.data);
}

function renderToast(message, type = "success") {
  let toastContainer = document.querySelector("#toastContainer");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toastContainer";
    toastContainer.className = "toast-container position-fixed top-0 end-0 p-3";
    document.body.appendChild(toastContainer);
  }

  const toastId = `toast-${Date.now()}`;
  toastContainer.insertAdjacentHTML(
    "beforeend",
    `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `,
  );

  const toastElement = document.querySelector(`#${toastId}`);
  const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
  toast.show();
  toastElement.addEventListener("hidden.bs.toast", () => toastElement.remove());
}

function renderAlert(container, message, type = "danger") {
  const target =
    typeof container === "string"
      ? document.querySelector(container)
      : container;
  if (!target) {
    return;
  }

  target.innerHTML = `
        <div class="alert alert-${type} border-0 shadow-sm mb-0" role="alert">
            ${escapeHtml(message)}
        </div>
    `;
}

async function tryEndpoints(endpoints, payload, method = "post") {
  let lastError = null;

  for (const endpoint of endpoints) {
    try {
      const response = await axios.request({
        method,
        url: endpoint,
        data: payload,
      });
      return response.data;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Unable to complete request");
}

async function login(username, password) {
  const payload = { username, password };
  return tryEndpoints(["/api/token/", "/api-token-auth/"], payload, "post");
}

async function register(payload) {
  return tryEndpoints(
    ["/api/register/", "/api/v1/auth/register/", "/api/v1/users/register/"],
    payload,
    "post",
  );
}

async function requestPasswordReset(payload) {
  return tryEndpoints(
    ["/api/password-reset/", "/api/auth/password-reset/"],
    payload,
    "post",
  );
}

function storeAndRedirect(authPayload, redirectTo = "dashboard.html") {
  setAuthTokens(authPayload);
  window.location.href = redirectTo;
}

function formatBytes(bytes) {
  return bytesToHuman(bytes);
}

window.CloudVault = {
  apiRequest,
  apiClient,
  API_BASE,
  TOKEN_KEY,
  THEME_KEY,
  getToken,
  getRefreshToken,
  setAuthTokens,
  clearAuthTokens,
  loadComponent,
  bootstrapShell,
  bytesToHuman,
  formatBytes,
  formatDate,
  escapeHtml,
  getFileIconClass,
  uploadFile,
  renderToast,
  renderAlert,
  isAuthenticated,
  enforceAuthentication,
  fetchAllPages,
  login,
  register,
  requestPasswordReset,
  storeAndRedirect,
  setTheme,
  toggleTheme,
};

console.log("[api.js] Loaded successfully. CloudVault exported.");
