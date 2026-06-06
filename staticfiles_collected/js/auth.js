// Authentication functions — fixed version

function setToken(token) {
    localStorage.setItem('cloudvault_token', token);
    localStorage.setItem('auth_token', token); // backward compat
}

function getToken() {
    return localStorage.getItem('cloudvault_token') || localStorage.getItem('auth_token') || '';
}

function isAuthenticated() {
    return Boolean(getToken());
}

async function login(usernameOrEmail, password) {
    try {
        const response = await axios.post('/api-token-auth/', { username: usernameOrEmail, password });
        setToken(response.data.token);
        return response.data.token;
    } catch (firstErr) {
        // If email used, retry with local-part as username
        if (usernameOrEmail.includes('@')) {
            try {
                const resp2 = await axios.post('/api-token-auth/', { username: usernameOrEmail.split('@')[0], password });
                setToken(resp2.data.token);
                return resp2.data.token;
            } catch (e2) { throw firstErr; }
        }
        throw firstErr;
    }
}

async function register(username, email, password) {
    const response = await axios.post('/api/v1/users/register/', { username, email, password });
    return response.data;
}

function logout() {
    localStorage.removeItem('cloudvault_token');
    localStorage.removeItem('auth_token');
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
        const token = getToken();
        await axios.post(`/api/v1/users/notifications/${id}/accept_share/`, {}, {
            headers: { Authorization: `Token ${token}` }
        });
        await loadNotifications();
    } catch (e) {
        alert('Failed to confirm share: ' + (e.response?.data?.detail || e.message));
    }
}

async function declineShareNotification(id) {
    try {
        const token = getToken();
        await axios.post(`/api/v1/users/notifications/${id}/decline_share/`, {}, {
            headers: { Authorization: `Token ${token}` }
        });
        await loadNotifications();
    } catch (e) {
        alert('Failed to clear share: ' + (e.response?.data?.detail || e.message));
    }
}

// Correct uploadFile for dashboard upload button
async function uploadFile(path, formData, config = {}) {
    const token = getToken();
    const response = await axios.post(`/api/v1${path}`, formData, {
        headers: { Authorization: `Token ${token}` },
        ...config,
    });
    return response.data;
}
