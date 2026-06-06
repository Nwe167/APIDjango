const {
  bootstrapShell,
  apiRequest,
  escapeHtml,
  formatDate,
  renderToast,
  fetchAllPages,
} = window.CloudVault;

async function renderNotificationPage() {
  const target = document.querySelector("#notificationList");
  if (!target) return;

  const notifications = await fetchAllPages("/users/notifications/");
  const unreadCount = notifications.filter((item) => !item.is_read).length;
  const badge = document.querySelector("#notificationUnreadCount");
  if (badge) badge.textContent = `${unreadCount} unread`;

  target.innerHTML = notifications.length
    ? notifications
        .map(
          (item) => `
        <div class="content-card notification-row mb-3 ${item.is_read ? "opacity-75" : ""}">
            <div class="d-flex align-items-start gap-3">
                <div class="file-icon"><i class="bi bi-bell"></i></div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between gap-3">
                        <div>
                            <div class="fw-bold">${escapeHtml(item.title)}</div>
                            <div class="text-secondary">${escapeHtml(item.body || "No description")}</div>
                        </div>
                        <small class="text-secondary">${formatDate(item.created_at)}</small>
                    </div>
                    <div class="mt-3 d-flex gap-2">
                        <button class="btn btn-sm ${item.is_read ? "btn-outline-secondary" : "btn-primary"}" data-mark-read="${item.id}" ${item.is_read ? "disabled" : ""}>Mark as read</button>
                        ${item.deep_link ? `<a class="btn btn-sm btn-outline-primary" href="${item.deep_link}">Open</a>` : ""}
                    </div>
                </div>
            </div>
        </div>
    `,
        )
        .join("")
    : '<div class="empty-state">No notifications available.</div>';

  target.querySelectorAll("[data-mark-read]").forEach((button) => {
    button.addEventListener("click", async () => {
      await apiRequest(
        "post",
        `/users/notifications/${button.dataset.markRead}/mark_as_read/`,
      );
      renderToast("Notification marked as read", "success");
      await renderNotificationPage();
      try {
        const all = await apiRequest("get", "/users/notifications/");
        const navUnread = (all.results || all || []).filter(
          (n) => !n.is_read,
        ).length;
        const navBadge = document.querySelector("#navUnreadBadge");
        if (navBadge) {
          navBadge.textContent = String(navUnread);
          navBadge.classList.toggle("d-none", navUnread === 0);
        }
      } catch (e) {
        /* non-fatal */
      }
    });
  });
}

async function initNotificationsPage() {
  await bootstrapShell("notifications", { sidebar: true, requireAuth: true });
  await renderNotificationPage();

  const markAllReadBtn = document.querySelector("#markAllReadPageBtn");
  if (markAllReadBtn) {
    markAllReadBtn.addEventListener("click", async () => {
      await apiRequest("post", "/users/notifications/mark_all_as_read/");
      renderToast("All notifications marked as read", "success");
      await renderNotificationPage();
      try {
        const navBadge = document.querySelector("#navUnreadBadge");
        if (navBadge) {
          navBadge.textContent = "0";
          navBadge.classList.add("d-none");
        }
      } catch (e) {
        /* non-fatal */
      }
    });
  }
}

initNotificationsPage();
