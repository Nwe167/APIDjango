// Authentication functions

function setToken(token) {
    localStorage.setItem('cloudvault_token', token);
}

function getToken() {
    // Prefer token injected by the server into the page (window.API_TOKEN),
    // then fall back to what is stored in localStorage.
    return window.API_TOKEN || localStorage.getItem('cloudvault_token') || '';
}

function isAuthenticated() {
    return Boolean(getToken()) && Boolean(localStorage.getItem('cloudvault_user_id'));
}

async function login(usernameOrEmail, password) {
    const response = await axios.post('/api/auth/login/', { username: usernameOrEmail, password });
    const data = response.data;
    // Store the global API token and user identity
    setToken(data.token);
    localStorage.setItem('cloudvault_user_id', data.user_id);
    localStorage.setItem('cloudvault_username', data.username);
    return data;
}

async function register(username, email, password) {
    const response = await axios.post('/api/v1/users/register/', { username, email, password });
    return response.data;
}

function logout() {
    axios.post('/api/auth/logout/').catch(() => {});
    localStorage.removeItem('cloudvault_token');
    localStorage.removeItem('cloudvault_user_id');
    localStorage.removeItem('cloudvault_username');
    localStorage.removeItem('cloudvault_refresh_token');
    sessionStorage.clear();
    window.location.href = '/frontend/login/';
}

function redirectToDashboard() {
    window.location.href = '/frontend/dashboard/';
}

function initTheme() {
    const saved = localStorage.getItem('theme') || localStorage.getItem('cloudvault_theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', saved);
    if (saved === 'dark') document.body.classList.add('dark-mode');
}

async function loadNotifications() {
    try {
        const token = getToken();
        if (!token) return;
        const response = await axios.get('/api/v1/users/notifications/', {
            headers: { Authorization: `Token ${token}` }
        });
        const notifications = response.data.results || response.data || [];
        const unreadCount = notifications.filter(n => !n.is_read).length;
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            badge.textContent = unreadCount;
            badge.style.display = unreadCount > 0 ? 'block' : 'none';
        }
        const list = document.getElementById('notificationsList');
        if (list) {
            list.innerHTML = notifications.length
                ? notifications.slice(0, 5).map(n => {
                    const isPendingShare = n.notification_type === 'share_received' && n.share_status === 'pending';
                    const link = n.deep_link || '/frontend/notifications/';
                    return `
                    <li><div class="dropdown-item">
                        <div class="d-flex justify-content-between">
                            <span>${n.title || 'Notification'}</span>
                            ${!n.is_read ? '<span class="badge bg-primary">New</span>' : ''}
                        </div>
                        <small class="text-muted">${n.body || ''}</small>
                        <div class="d-flex gap-2 mt-2">
                            <a class="btn btn-sm btn-outline-primary" href="${link}" onclick="event.stopPropagation()">View</a>
                            ${isPendingShare ? `
                                <button class="btn btn-sm btn-success" type="button" onclick="event.stopPropagation();acceptShareNotification('${n.id}')">Confirm</button>
                                <button class="btn btn-sm btn-outline-danger" type="button" onclick="event.stopPropagation();declineShareNotification('${n.id}')">Clear</button>
                            ` : ''}
                        </div>
                    </div></li>`;
                }).join('')
                : '<li><a class="dropdown-item text-center text-muted" href="#">No notifications</a></li>';
        }
    } catch (e) { console.warn('Notifications load failed', e); }
}

async function acceptShareNotification(id) {
    try {
        await axios.post(`/api/v1/users/notifications/${id}/accept_share/`, {}, {
            headers: { Authorization: `Token ${getToken()}` }
        });
        await loadNotifications();
    } catch (e) {
        alert('Failed to confirm share: ' + (e.response?.data?.detail || e.message));
    }
}

async function declineShareNotification(id) {
    try {
        await axios.post(`/api/v1/users/notifications/${id}/decline_share/`, {}, {
            headers: { Authorization: `Token ${getToken()}` }
        });
        await loadNotifications();
    } catch (e) {
        alert('Failed to clear share: ' + (e.response?.data?.detail || e.message));
    }
}

async function uploadFile(path, formData, config = {}) {
    const response = await axios.post(`/api/v1${path}`, formData, {
        headers: { Authorization: `Token ${getToken()}` },
        ...config,
    });
    return response.data;
}
