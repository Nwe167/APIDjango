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
  // Prefer the global token injected by the server into window.API_TOKEN
  return window.API_TOKEN || localStorage.getItem(TOKEN_KEY) || "";
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

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Ensure error has response structure for consistent handling
    if (!error.response) {
      error.response = {
        status: error.status || 0,
        data: { detail: error.message || "Network error" },
      };
    }
    return Promise.reject(error);
  },
);

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
    await loadComponent("#navbarSlot", "/static/components/navbar.html");
  }

  if (options.sidebar !== false && document.querySelector("#sidebarSlot")) {
    await loadComponent("#sidebarSlot", "/static/components/sidebar.html");
    _initSidebarFolders();
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

  // mark notifications read when user opens the bell dropdown
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
            // refresh account summary which updates the navbar badge and list
            await hydrateAccountSummary();
          } catch (e) {
            // non-fatal
          }
        });
      }
    }
  } catch (e) {
    // ignore
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

  // Bind sidebar upload input to allow uploading into a selected/current folder
  try {
    const sidebarUpload = document.querySelector("#sidebarUploadInput");
    const sidebarUploadLabel = document.querySelector("#sidebarUploadLabel");
    if (sidebarUpload && !sidebarUpload.dataset.bound) {
      sidebarUpload.dataset.bound = "true";
      sidebarUpload.addEventListener("change", async (e) => {
        const files = Array.from(e.target.files || []);
        if (!files.length) return renderToast("No files selected", "warning");

        // Prefer explicit selection stored on the page, then URL folder param
        const parent =
          window.selectedFolder ||
          new URLSearchParams(window.location.search).get("folder") ||
          null;
        if (!parent) {
          // ask user to confirm upload to root
          if (!confirm("No folder selected. Upload to My Drive root?")) {
            sidebarUpload.value = "";
            return;
          }
        }

        const form = new FormData();
        files.forEach((f) => form.append("files", f));
        if (parent) form.append("parent", parent);

        // Show loading state
        const originalText = sidebarUploadLabel.innerHTML;
        sidebarUploadLabel.innerHTML =
          '<i class="bi bi-hourglass-split me-2"></i>Uploading...';
        sidebarUploadLabel.disabled = true;

        try {
          await uploadFile("/files/upload_multiple/", form, {
            onUploadProgress: (ev) => {
              const percent = Math.round((ev.loaded / ev.total) * 100);
              sidebarUploadLabel.innerHTML = `<i class="bi bi-cloud-arrow-up me-2"></i>${percent}%`;
            },
          });
          const folderName = parent ? `folder` : "My Drive";
          renderToast(
            `${files.length} file(s) uploaded to ${folderName}`,
            "success",
          );
          // Reload to refresh UI state (folders/files)
          setTimeout(() => window.location.reload(), 1500);
        } catch (err) {
          console.error("Sidebar upload failed", err);
          const errMsg =
            err.response?.data?.detail || err.message || "Unknown error";
          renderToast(`Upload failed: ${errMsg}`, "danger");
        } finally {
          sidebarUploadLabel.innerHTML = originalText;
          sidebarUploadLabel.disabled = false;
          sidebarUpload.value = "";
        }
      });
    }
  } catch (e) {
    // non-fatal
  }
}

function highlightNav(activePage) {
  document.querySelectorAll("[data-nav-item]").forEach((link) => {
    link.classList.toggle("active", link.dataset.navItem === activePage);
  });
}

function isAuthenticated() {
  return Boolean(getToken());
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
      "Content-Type": "multipart/form-data",
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
  const response = await axios.post('/api/auth/login/', { username, password });
  const data = response.data;
  setAuthTokens({ token: data.token });
  localStorage.setItem('cloudvault_user_id', data.user_id);
  return data;
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

function _initSidebarFolders() {
  const toggle  = document.getElementById("sidebarFoldersToggle");
  const list    = document.getElementById("sidebarFolderList");
  const inner   = document.getElementById("sidebarFolderListInner");
  const chevron = document.getElementById("sidebarFoldersChevron");
  if (!toggle || !list || !inner) return;

  let loaded = false;

  // ── inline folder panel (works on any page) ──────────────────────────────
  function ensurePanel() {
    if (document.getElementById('sidebarFolderPanel')) return;
    const panel = document.createElement('div');
    panel.id = 'sidebarFolderPanel';
    panel.innerHTML = `
      <div style="position:fixed;inset:0;z-index:1055;display:flex;align-items:stretch;pointer-events:none">
        <div style="pointer-events:auto;width:min(92vw,480px);background:var(--app-surface,#fff);border-right:1px solid var(--app-border,#dee2e6);
                    box-shadow:4px 0 24px rgba(0,0,0,.13);display:flex;flex-direction:column;transform:translateX(-100%);transition:transform .25s ease;" id="sidebarFolderPanelInner">
          <!-- panel toolbar -->
          <div style="display:flex;align-items:center;gap:.5rem;padding:.6rem .8rem;background:#f8f9fa;border-bottom:1px solid #dee2e6;flex-shrink:0">
            <button id="sfpBack" class="btn btn-sm btn-outline-secondary" disabled title="Back"><i class="bi bi-arrow-left"></i></button>
            <nav class="flex-grow-1"><ol class="breadcrumb mb-0 small" id="sfpBreadcrumb"><li class="breadcrumb-item active">My Drive</li></ol></nav>
            <button id="sfpNewFolder" class="btn btn-sm btn-primary" title="New Folder"><i class="bi bi-folder-plus"></i></button>
            <label class="btn btn-sm btn-outline-success mb-0" title="Upload files here">
              <i class="bi bi-cloud-arrow-up"></i>
              <input type="file" id="sfpUploadInput" class="d-none" multiple/>
            </label>
            <button id="sfpClose" class="btn btn-sm btn-outline-secondary"><i class="bi bi-x-lg"></i></button>
          </div>
          <!-- panel grid -->
          <div style="flex:1;overflow-y:auto;padding:.75rem" id="sfpGrid"></div>
        </div>
        <!-- backdrop -->
        <div style="flex:1;pointer-events:auto;cursor:pointer" id="sfpBackdrop"></div>
      </div>`;
    document.body.appendChild(panel);

    const panelInner = document.getElementById('sidebarFolderPanelInner');
    const sfpGrid    = document.getElementById('sfpGrid');
    const sfpBc      = document.getElementById('sfpBreadcrumb');
    const sfpBack    = document.getElementById('sfpBack');
    const sfpClose   = document.getElementById('sfpClose');
    const sfpNew     = document.getElementById('sfpNewFolder');
    const sfpUpload  = document.getElementById('sfpUploadInput');

    let sfpStack = [{ id: null, name: 'My Drive' }];
    let sfpFiles = [];
    const sfpCur = () => sfpStack[sfpStack.length - 1];

    function sfpRender() {
      const fid = sfpCur().id;
      const items = sfpFiles.filter(f => String(f.parent || '') === String(fid || ''));
      const folders = items.filter(f => (f.mime_type || '').includes('folder'));
      const files   = items.filter(f => !(f.mime_type || '').includes('folder'));
      const sorted  = [...folders, ...files];

      sfpBack.disabled = sfpStack.length <= 1;
      sfpBc.innerHTML = sfpStack.map((c, i) =>
        i === sfpStack.length - 1
          ? `<li class="breadcrumb-item active">${escapeHtml(c.name)}</li>`
          : `<li class="breadcrumb-item"><a href="#" data-si="${i}">${escapeHtml(c.name)}</a></li>`
      ).join('');
      sfpBc.querySelectorAll('[data-si]').forEach(a =>
        a.addEventListener('click', e => { e.preventDefault(); sfpStack = sfpStack.slice(0, +a.dataset.si + 1); sfpRender(); })
      );

      if (!sorted.length) {
        sfpGrid.innerHTML = `<div style="text-align:center;padding:2rem;color:#adb5bd">
          <i class="bi bi-folder2-open" style="font-size:2.5rem"></i>
          <div class="mt-2">Empty folder</div>
          <small>Upload files or create a subfolder</small>
        </div>`;
        return;
      }

      sfpGrid.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:.6rem">${
        sorted.map(item => {
          const isF = (item.mime_type || '').includes('folder');
          const icon = isF ? 'bi-folder-fill' : getFileIconClass(item.name, item.mime_type);
          const color = isF ? '#ffc107' : '#6c757d';
          return `<div class="sfp-item" data-id="${item.id}" data-is-folder="${isF}"
                       style="border:1px solid transparent;border-radius:8px;padding:.6rem .4rem;text-align:center;cursor:pointer;user-select:none;transition:background .12s">
            <i class="bi ${icon}" style="font-size:2rem;color:${color};display:block;margin-bottom:.2rem"></i>
            <div style="font-size:.72rem;word-break:break-word;line-height:1.3">${escapeHtml(item.name)}</div>
          </div>`;
        }).join('')
      }</div>`;

      sfpGrid.querySelectorAll('.sfp-item').forEach(el => {
        el.addEventListener('mouseenter', () => { el.style.background = '#e9f0ff'; el.style.borderColor = '#b6d0ff'; });
        el.addEventListener('mouseleave', () => { el.style.background = ''; el.style.borderColor = 'transparent'; });
        el.addEventListener('dblclick', () => {
          if (el.dataset.isFolder === 'true') {
            sfpStack.push({ id: el.dataset.id, name: el.querySelector('div').textContent });
            sfpRender();
          }
        });
        el.addEventListener('click', () => {
          sfpGrid.querySelectorAll('.sfp-item').forEach(n => { n.style.background = ''; n.style.borderColor = 'transparent'; });
          el.style.background = '#cfe2ff'; el.style.borderColor = '#0d6efd';
        });
      });
    }

    async function sfpLoad() {
      sfpGrid.innerHTML = '<div style="text-align:center;padding:2rem"><div class="spinner-border spinner-border-sm"></div></div>';
      sfpFiles = await fetchAllPages('/files/');
      sfpRender();
    }

    sfpBack.addEventListener('click', () => { if (sfpStack.length > 1) { sfpStack.pop(); sfpRender(); } });
    sfpClose.addEventListener('click', closePanel);
    document.getElementById('sfpBackdrop').addEventListener('click', closePanel);

    sfpNew.addEventListener('click', async () => {
      const name = prompt('Folder name:');
      if (!name) return;
      const payload = { name, mime_type: 'folder' };
      if (sfpCur().id) payload.parent = sfpCur().id;
      try {
        await apiRequest('post', '/files/', payload);
        renderToast('Folder created', 'success');
        await sfpLoad();
      } catch (e) { renderToast(e?.response?.data?.detail || 'Failed', 'danger'); }
    });

    sfpUpload.addEventListener('change', async () => {
      const files = Array.from(sfpUpload.files || []);
      if (!files.length) return;
      const form = new FormData();
      files.forEach(f => form.append('files', f));
      if (sfpCur().id) form.append('parent', sfpCur().id);
      try {
        await uploadFile('/files/upload_multiple/', form);
        renderToast(`${files.length} file(s) uploaded to "${sfpCur().name}"`, 'success');
        await sfpLoad();
      } catch (err) { renderToast(err?.response?.data?.detail || 'Upload failed', 'danger'); }
      finally { sfpUpload.value = ''; }
    });

    // expose open function
    panel._open = async (id, name) => {
      sfpStack = id ? [{ id: null, name: 'My Drive' }, { id, name }] : [{ id: null, name: 'My Drive' }];
      panelInner.style.transform = 'translateX(0)';
      panel.style.display = 'block';
      await sfpLoad();
    };

    function closePanel() {
      panelInner.style.transform = 'translateX(-100%)';
      setTimeout(() => { panel.style.display = 'none'; }, 260);
    }
  }

  function openPanel(id, name) {
    // If we're on the folders page and it exposed openFolder, use it directly
    if (typeof window.explorerOpenFolder === 'function') {
      window.explorerOpenFolder(id, name);
      return;
    }
    ensurePanel();
    document.getElementById('sidebarFolderPanel')._open(id, name);
  }

  // ── load folder tree ──────────────────────────────────────────────────────
  async function loadFolders() {
    inner.innerHTML = '<span class="text-secondary small px-1">Loading...</span>';
    try {
      const all = await fetchAllPages('/files/');
      const folders = all.filter(f => (f.mime_type || '').includes('folder'));
      if (!folders.length) {
        inner.innerHTML = '<span class="text-secondary small px-1">No folders yet</span>';
        return;
      }

      function renderLevel(parentId, depth) {
        return folders
          .filter(f => String(f.parent || '') === String(parentId || ''))
          .map(f => {
            const pl = depth * 10;
            const children = renderLevel(f.id, depth + 1);
            return `
              <div class="sidebar-folder-row">
                <div class="d-flex align-items-center gap-1" style="padding-left:${pl}px">
                  <i class="bi bi-folder-fill text-warning flex-shrink-0" style="font-size:.85rem"></i>
                  <span class="small text-truncate flex-grow-1 sidebar-folder-name"
                        data-folder-id="${f.id}" data-folder-name="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
                  <label class="btn btn-link p-0 ms-auto flex-shrink-0 sidebar-upload-btn" title="Add files to ${escapeHtml(f.name)}">
                    <i class="bi bi-plus-circle text-success" style="font-size:.8rem"></i>
                    <input type="file" class="d-none sidebar-folder-file-input" multiple
                           data-folder-id="${f.id}" data-folder-name="${escapeHtml(f.name)}"/>
                  </label>
                </div>
                ${children ? `<div>${children}</div>` : ''}
              </div>`;
          }).join('');
      }

      inner.innerHTML = renderLevel('', 0) || '<span class="text-secondary small px-1">No folders yet</span>';

      // click folder name → open panel (no page navigation)
      inner.querySelectorAll('.sidebar-folder-name').forEach(span => {
        span.addEventListener('click', () => openPanel(span.dataset.folderId, span.dataset.folderName));
      });

      // click [+] → upload directly into that folder
      inner.querySelectorAll('.sidebar-folder-file-input').forEach(input => {
        input.addEventListener('change', async () => {
          const files = Array.from(input.files || []);
          if (!files.length) return;
          const form = new FormData();
          files.forEach(f => form.append('files', f));
          form.append('parent', input.dataset.folderId);
          try {
            await uploadFile('/files/upload_multiple/', form);
            renderToast(`${files.length} file(s) added to "${input.dataset.folderName}"`, 'success');
          } catch (err) {
            renderToast(err?.response?.data?.detail || 'Upload failed', 'danger');
          } finally { input.value = ''; }
        });
      });

    } catch (e) {
      inner.innerHTML = '<span class="text-danger small px-1">Failed to load</span>';
    }
  }

  toggle.addEventListener('click', async e => {
    e.preventDefault();
    const isOpen = list.style.display !== 'none';
    if (isOpen) {
      list.style.display = 'none';
      if (chevron) chevron.style.transform = '';
    } else {
      list.style.display = 'block';
      if (chevron) chevron.style.transform = 'rotate(90deg)';
      if (!loaded) { loaded = true; await loadFolders(); }
    }
  });
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
  fetchAllPages,
  login,
  register,
  requestPasswordReset,
  storeAndRedirect,
  setTheme,
  toggleTheme,
};
