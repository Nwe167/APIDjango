// Dashboard — fixed & complete

async function loadDashboard() {
    try {
        const token = localStorage.getItem('cloudvault_token') || localStorage.getItem('auth_token') || '';
        const headers = { Authorization: `Token ${token}` };

        const [filesRes, profileRes, activityRes, trashRes] = await Promise.allSettled([
            axios.get('/api/v1/files/', { headers }),
            axios.get('/api/v1/users/profile/me/', { headers }),
            axios.get('/api/v1/activity/', { headers }),
            axios.get('/api/v1/trash/', { headers }),
        ]);

        const files = filesRes.status === 'fulfilled'
            ? (filesRes.value.data.results || filesRes.value.data || []) : [];
        const profile = profileRes.status === 'fulfilled' ? profileRes.value.data : null;
        const activities = activityRes.status === 'fulfilled'
            ? (activityRes.value.data.results || activityRes.value.data || []) : [];
        const trashItems = trashRes.status === 'fulfilled'
            ? (trashRes.value.data.results || trashRes.value.data || []) : [];

        // Stats
        const totalFiles = files.filter(f => f.mime_type !== 'folder').length;
        const totalFolders = files.filter(f => f.mime_type === 'folder').length;
        const sharedCount = files.filter(f => f.is_shared).length;
        const trashCount = trashItems.length;

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl('fileCount', totalFiles);
        setEl('folderCount', totalFolders);
        setEl('sharedCount', sharedCount);
        setEl('trashCount', trashCount);

        // Account Info — FIX: profile.user.username not profile.username
        if (profile) {
            const username = profile.user?.username || profile.user?.email || profile.given_name || 'User';
            setEl('userDisplay', username);

            const usedBytes = Number(profile.storage_quota_usage_bytes || 0);
            const limitBytes = Number(profile.storage_quota_limit_bytes || 5 * 1024 * 1024 * 1024);
            const pct = limitBytes > 0 ? Math.min(100, Math.round((usedBytes / limitBytes) * 100)) : 0;
            const bar = document.getElementById('storageBar');
            const txt = document.getElementById('storageText');
            if (bar) bar.style.width = pct + '%';
            if (txt) txt.textContent = formatBytes(usedBytes) + ' / ' + formatBytes(limitBytes);
        }

        renderRecentFiles(files.slice(0, 5));
        renderActivityTimeline(activities.slice(0, 10));

    } catch (error) {
        console.error('Dashboard load error:', error);
        if (typeof showError === 'function') showError('Failed to load dashboard data');
    }
}

function formatBytes(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let v = bytes, i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(val) {
    if (!val) return 'N/A';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(val));
}

function getIcon(mime) {
    if (!mime) return 'bi-file-earmark';
    if (mime === 'folder') return 'bi-folder-fill';
    if (mime.startsWith('image/')) return 'bi-file-earmark-image';
    if (mime.includes('pdf')) return 'bi-file-earmark-pdf';
    if (mime.includes('spreadsheet') || mime.includes('excel')) return 'bi-file-earmark-spreadsheet';
    if (mime.startsWith('video/')) return 'bi-file-earmark-play';
    if (mime.startsWith('audio/')) return 'bi-file-earmark-music';
    if (mime.startsWith('text/')) return 'bi-file-earmark-text';
    return 'bi-file-earmark';
}

function renderRecentFiles(files) {
    const container = document.getElementById('recentFilesList');
    if (!container) return;
    if (!files.length) {
        container.innerHTML = '<div class="text-center text-muted py-4"><small>No files yet. Click "Upload File" to add your first file.</small></div>';
        return;
    }
    container.innerHTML = files.map(file => `
        <div class="d-flex align-items-center justify-content-between py-3 border-bottom">
            <div class="d-flex align-items-center gap-3" style="flex:1;min-width:0">
                <div style="width:40px;height:40px;border-radius:8px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;flex-shrink:0">
                    <i class="bi ${getIcon(file.mime_type)}"></i>
                </div>
                <div style="min-width:0">
                    <div class="fw-bold small text-truncate">${file.name || 'File'}</div>
                    <small class="text-muted">${formatDate(file.modified_time)}</small>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2 ms-2">
                <small class="text-muted">${formatBytes(file.size_bytes || 0)}</small>
                <button class="btn btn-sm btn-outline-primary" onclick="openShareDialog('${file.id}','${(file.name||'').replace(/'/g,"\\'")}')">
                    <i class="bi bi-share"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" onclick="previewFile('${file.id}','${file.mime_type||''}','${(file.name||'').replace(/'/g,"\\'")}')">
                    <i class="bi bi-eye"></i>
                </button>
            </div>
        </div>`).join('');
}

function renderActivityTimeline(activities) {
    const container = document.getElementById('activityFeed');
    if (!container) return;
    if (!activities.length) {
        container.innerHTML = '<div class="text-center text-muted py-4"><small>No activity yet</small></div>';
        return;
    }
    const icons = {
        file_create:'bi-file-earmark-plus', file_edit:'bi-pencil-square',
        file_delete:'bi-trash3', file_share:'bi-share',
        file_download:'bi-download', file_restore:'bi-arrow-counterclockwise',
        comment_add:'bi-chat-left-text',
    };
    container.innerHTML = activities.map(a => `
        <div class="d-flex gap-2 mb-3 pb-3 border-bottom">
            <div style="width:32px;height:32px;border-radius:8px;background:#e0e7ff;display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <i class="bi ${icons[a.action]||'bi-activity'}" style="color:#3b82f6"></i>
            </div>
            <div style="flex:1;min-width:0">
                <div class="small fw-bold">${(a.action||'').replace(/_/g,' ')}</div>
                <small class="text-muted d-block text-truncate">${a.file_name||'System'}</small>
                <small class="text-muted">${formatDate(a.occurred_at)}</small>
            </div>
        </div>`).join('');
}

// Inline preview from dashboard
function previewFile(fileId, mimeType, fileName) {
    const token = localStorage.getItem('cloudvault_token') || localStorage.getItem('auth_token') || '';
    const previewUrl = `/api/v1/files/${fileId}/preview/?token=${token}`;
    const mime = (mimeType || '').toLowerCase();
    const modal = document.getElementById('previewModal');
    const body = document.getElementById('previewModalBody');
    const label = document.getElementById('previewModalLabel');
    if (!modal || !body) return;

    label.textContent = fileName || 'Preview';

    if (mime.startsWith('image/')) {
        body.innerHTML = `<img src="${previewUrl}" class="img-fluid d-block mx-auto" style="max-height:70vh" alt="${fileName}">`;
    } else if (mime.includes('pdf')) {
        body.innerHTML = `<iframe src="${previewUrl}" style="width:100%;height:75vh;border:none"></iframe>`;
    } else if (mime.startsWith('text/') || mime.includes('json')) {
        body.innerHTML = `<iframe src="${previewUrl}" style="width:100%;height:65vh;border:none;background:#f8f9fa"></iframe>`;
    } else if (mime.startsWith('video/')) {
        body.innerHTML = `<video controls class="w-100"><source src="${previewUrl}" type="${mimeType}">Your browser cannot preview this video.</video>`;
    } else if (mime.startsWith('audio/')) {
        body.innerHTML = `<audio controls class="w-100"><source src="${previewUrl}" type="${mimeType}">Your browser cannot preview this audio.</audio>`;
    } else {
        body.innerHTML = `<div class="text-center py-5 text-muted">
            <i class="bi bi-file-earmark display-3 d-block mb-3"></i>
            <p>Cannot preview this file type.</p>
            <a class="btn btn-primary" href="/api/v1/files/${fileId}/download/" target="_blank">
                <i class="bi bi-download me-1"></i>Download instead
            </a></div>`;
    }
    new bootstrap.Modal(modal).show();
}
