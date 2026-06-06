// files.js — complete working implementation
console.log('[files.js] loading');

const F = {
    allFiles: [],
    currentView: 'table',
    currentFolderId: null,
    searchQuery: '',
};

function tok() {
    return localStorage.getItem('cloudvault_token') || localStorage.getItem('auth_token') || '';
}
function authHeaders() { return { Authorization: `Token ${tok()}` }; }

function fmt(bytes) {
    if (!bytes || bytes <= 0) return '0 B';
    const u = ['B','KB','MB','GB']; let v=bytes,i=0;
    while(v>=1024&&i<u.length-1){v/=1024;i++;} return `${v.toFixed(i?1:0)} ${u[i]}`;
}
function fmtDate(val) {
    if(!val) return '—';
    return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(val));
}
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function icon(mime){
    if(!mime) return 'bi-file-earmark';
    if(mime==='folder') return 'bi-folder-fill text-warning';
    if(mime.startsWith('image/')) return 'bi-file-earmark-image text-info';
    if(mime.includes('pdf')) return 'bi-file-earmark-pdf text-danger';
    if(mime.includes('spreadsheet')||mime.includes('excel')||mime.includes('csv')) return 'bi-file-earmark-spreadsheet text-success';
    if(mime.includes('presentation')||mime.includes('powerpoint')) return 'bi-file-earmark-slides text-warning';
    if(mime.includes('word')||mime.includes('document')) return 'bi-file-earmark-word text-primary';
    if(mime.startsWith('video/')) return 'bi-file-earmark-play text-danger';
    if(mime.startsWith('audio/')) return 'bi-file-earmark-music text-purple';
    if(mime.startsWith('text/')||mime.includes('json')) return 'bi-file-earmark-text text-secondary';
    if(mime.includes('zip')||mime.includes('archive')) return 'bi-file-earmark-zip text-secondary';
    return 'bi-file-earmark';
}

async function loadFiles() {
    const tbody = document.getElementById('filesTableBody');
    const grid  = document.getElementById('filesGrid');
    if(tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm me-2"></div>Loading files...</td></tr>';

    try {
        const url = F.currentFolderId
            ? `/api/v1/files/${F.currentFolderId}/children/`
            : '/api/v1/files/';
        const r = await axios.get(url, { headers: authHeaders() });
        let files = r.data.results || r.data || [];
        if (F.searchQuery) {
            const q = F.searchQuery.toLowerCase();
            files = files.filter(f => (f.name||'').toLowerCase().includes(q) || (f.mime_type||'').toLowerCase().includes(q));
        }
        F.allFiles = files;
        const count = document.getElementById('filesTotalCount');
        if(count) count.textContent = `(${files.length} items)`;
        renderTable(files);
        renderGrid(files);
        loadStorageBar();
    } catch(err) {
        console.error('loadFiles error', err);
        if(tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-danger">Failed to load files: ${esc(err.response?.data?.detail || err.message)}</td></tr>`;
    }
}

function renderTable(files) {
    const tbody = document.getElementById('filesTableBody');
    if(!tbody) return;
    if(!files.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-5 text-muted"><i class="bi bi-folder2-open d-block mb-2" style="font-size:2rem"></i>No files here yet. Upload your first file!</td></tr>';
        return;
    }
    tbody.innerHTML = files.map(f => `
    <tr class="file-row" data-id="${f.id}">
        <td>
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${icon(f.mime_type)}" style="font-size:1.3rem"></i>
                <div>
                    <div class="fw-semibold text-truncate" style="max-width:220px" title="${esc(f.name)}">${esc(f.name)}</div>
                    <small class="text-muted">${esc(f.mime_type||'—')}</small>
                </div>
            </div>
        </td>
        <td><small class="text-muted">${esc(f.mime_type||'—')}</small></td>
        <td>${fmt(f.size_bytes)}</td>
        <td><small>${esc(f.owner_email||'Me')}</small></td>
        <td><span class="badge ${f.trashed?'bg-secondary':'bg-success'}">${f.trashed?'Trashed':'Active'}</span></td>
        <td><button class="btn btn-sm btn-link p-0 star-btn" data-id="${f.id}" data-starred="${f.starred}" title="${f.starred?'Unstar':'Star'}">
            <i class="bi ${f.starred?'bi-star-fill text-warning':'bi-star text-muted'}"></i></button></td>
        <td><small>${fmtDate(f.modified_time)}</small></td>
        <td class="text-end">
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-secondary preview-btn" data-id="${f.id}" data-mime="${esc(f.mime_type||'')}" data-name="${esc(f.name)}" title="Preview"><i class="bi bi-eye"></i></button>
                <button class="btn btn-outline-primary download-btn" data-id="${f.id}" data-name="${esc(f.name)}" title="Download"><i class="bi bi-download"></i></button>
                <button class="btn btn-outline-success share-btn" data-id="${f.id}" data-name="${esc(f.name)}" title="Share"><i class="bi bi-share"></i></button>
                <button class="btn btn-outline-danger trash-btn" data-id="${f.id}" data-name="${esc(f.name)}" title="Move to trash"><i class="bi bi-trash3"></i></button>
            </div>
        </td>
    </tr>`).join('');
    bindTableActions();
}

function renderGrid(files) {
    const grid = document.getElementById('filesGrid');
    if(!grid) return;
    if(!files.length) { grid.innerHTML = ''; return; }
    grid.innerHTML = `<div class="row g-3">${files.map(f=>`
        <div class="col-6 col-md-4 col-lg-3">
            <div class="card h-100 shadow-sm file-grid-card" style="cursor:pointer" data-id="${f.id}">
                <div class="card-body text-center p-3">
                    <i class="bi ${icon(f.mime_type)}" style="font-size:2.5rem"></i>
                    <div class="fw-semibold mt-2 text-truncate small" title="${esc(f.name)}">${esc(f.name)}</div>
                    <small class="text-muted">${fmt(f.size_bytes)}</small>
                </div>
                <div class="card-footer bg-transparent d-flex justify-content-around p-1">
                    <button class="btn btn-sm btn-link preview-btn" data-id="${f.id}" data-mime="${esc(f.mime_type||'')}" data-name="${esc(f.name)}"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-sm btn-link share-btn" data-id="${f.id}" data-name="${esc(f.name)}"><i class="bi bi-share"></i></button>
                    <button class="btn btn-sm btn-link text-danger trash-btn" data-id="${f.id}" data-name="${esc(f.name)}"><i class="bi bi-trash3"></i></button>
                </div>
            </div>
        </div>`).join('')}</div>`;
    bindTableActions();
}

function bindTableActions() {
    document.querySelectorAll('.preview-btn').forEach(btn => {
        btn.onclick = () => openPreview(btn.dataset.id, btn.dataset.mime, btn.dataset.name);
    });
    document.querySelectorAll('.download-btn').forEach(btn => {
        btn.onclick = () => { window.open(`/api/v1/files/${btn.dataset.id}/download/`, '_blank'); };
    });
    document.querySelectorAll('.share-btn').forEach(btn => {
        btn.onclick = () => openShareDialog(btn.dataset.id, btn.dataset.name);
    });
    document.querySelectorAll('.trash-btn').forEach(btn => {
        btn.onclick = () => trashFile(btn.dataset.id, btn.dataset.name);
    });
    document.querySelectorAll('.star-btn').forEach(btn => {
        btn.onclick = () => toggleStar(btn.dataset.id);
    });
}

// --- UPLOAD ---
async function uploadFiles(fileList) {
    const bar = document.getElementById('uploadProgress');
    let done = 0;
    for(const file of fileList) {
        const fd = new FormData();
        fd.append('name', file.name);
        fd.append('mime_type', file.type || 'application/octet-stream');
        fd.append('file_path', file);
        fd.append('space', 'drive');
        if(F.currentFolderId) fd.append('parent', F.currentFolderId);
        try {
            if(bar){ bar.style.display='block'; bar.style.width='0%'; }
            await axios.post('/api/v1/files/', fd, {
                headers: { Authorization: `Token ${tok()}` },
                onUploadProgress(e){ if(bar) bar.style.width=`${Math.round(e.loaded/e.total*100)}%`; }
            });
            done++;
        } catch(err){
            const msg = err.response?.data?.file_path?.[0] || err.response?.data?.detail || err.message || 'Upload failed';
            alert(`Failed to upload "${file.name}": ${msg}`);
        }
    }
    if(bar) setTimeout(()=>{ bar.style.display='none'; bar.style.width='0%'; }, 600);
    if(done > 0) { showToast(`${done} file(s) uploaded successfully`, 'success'); loadFiles(); }
}

// --- TRASH ---
async function trashFile(id, name) {
    if(!confirm(`Move "${name}" to trash?`)) return;
    try {
        await axios.post(`/api/v1/files/${id}/trash/`, {}, { headers: authHeaders() });
        showToast(`"${name}" moved to trash`, 'warning');
        loadFiles();
    } catch(err) {
        showToast('Failed to move to trash: ' + (err.response?.data?.detail || err.message), 'danger');
    }
}

// --- STAR ---
async function toggleStar(id) {
    try {
        await axios.post(`/api/v1/files/${id}/star/`, {}, { headers: authHeaders() });
        loadFiles();
    } catch(err) { showToast('Failed to update star', 'danger'); }
}

// --- CREATE FOLDER ---
async function createFolder() {
    const name = prompt('Enter folder name:');
    if(!name || !name.trim()) return;
    try {
        await axios.post('/api/v1/files/', {
            name: name.trim(), mime_type: 'folder', space: 'drive',
            ...(F.currentFolderId ? { parent: F.currentFolderId } : {})
        }, { headers: { ...authHeaders(), 'Content-Type': 'application/json' } });
        showToast(`Folder "${name}" created`, 'success');
        loadFiles();
    } catch(err) {
        showToast('Failed to create folder: ' + (err.response?.data?.detail || err.message), 'danger');
    }
}

// --- PREVIEW ---
function openPreview(id, mime, name) {
    const modal = document.getElementById('previewModal');
    const body  = document.getElementById('previewModalBody');
    const label = document.getElementById('previewModalLabel');
    if(!modal) return;
    label.textContent = name;
    const url = `/api/v1/files/${id}/preview/`;
    const headers = `Authorization: Token ${tok()}`;
    const m = (mime||'').toLowerCase();

    // Use fetch-based blob URL for auth-gated preview
    async function loadPreview() {
        body.innerHTML = '<div class="text-center py-5"><div class="spinner-border"></div></div>';
        try {
            const r = await fetch(url, { headers: { Authorization: `Token ${tok()}` } });
            if(!r.ok) {
                body.innerHTML = `<div class="text-center py-4 text-muted">
                    <i class="bi bi-file-earmark display-3 d-block mb-3"></i>
                    <p>Cannot preview this file type.</p>
                    <a class="btn btn-primary" href="/api/v1/files/${id}/download/" target="_blank"><i class="bi bi-download me-1"></i>Download</a></div>`;
                return;
            }
            const blob = await r.blob();
            const blobUrl = URL.createObjectURL(blob);
            if(m.startsWith('image/')) {
                body.innerHTML = `<img src="${blobUrl}" class="img-fluid d-block mx-auto" style="max-height:75vh" alt="${esc(name)}">`;
            } else if(m.includes('pdf')) {
                body.innerHTML = `<iframe src="${blobUrl}" style="width:100%;height:78vh;border:none"></iframe>`;
            } else if(m.startsWith('video/')) {
                body.innerHTML = `<video controls class="w-100" style="max-height:75vh"><source src="${blobUrl}" type="${mime}">Cannot play video.</video>`;
            } else if(m.startsWith('audio/')) {
                body.innerHTML = `<div class="p-4"><audio controls class="w-100"><source src="${blobUrl}" type="${mime}">Cannot play audio.</audio></div>`;
            } else if(m.startsWith('text/')||m.includes('json')||m.includes('xml')||m.includes('csv')) {
                const text = await r.clone().text().catch(()=>'');
                body.innerHTML = `<pre class="p-3 bg-light" style="max-height:70vh;overflow:auto;white-space:pre-wrap;font-size:0.85rem">${esc(text||await fetch(url,{headers:{Authorization:`Token ${tok()}`}}).then(r=>r.text()))}</pre>`;
                // Re-fetch text since we already read the blob
                try {
                    const r2 = await fetch(url,{headers:{Authorization:`Token ${tok()}`}});
                    const t = await r2.text();
                    body.innerHTML = `<pre class="p-3 bg-light" style="max-height:70vh;overflow:auto;white-space:pre-wrap;font-size:0.85rem">${esc(t)}</pre>`;
                } catch(e){}
            } else {
                body.innerHTML = `<div class="text-center py-4 text-muted">
                    <i class="bi bi-file-earmark display-3 d-block mb-3"></i>
                    <p>Cannot preview this file type.</p>
                    <a class="btn btn-primary" href="/api/v1/files/${id}/download/" target="_blank"><i class="bi bi-download me-1"></i>Download</a></div>`;
            }
        } catch(e) {
            body.innerHTML = `<div class="text-center py-4 text-danger">Failed to load preview.</div>`;
        }
    }
    loadPreview();

    // Wire download button inside modal
    const dlBtn = document.getElementById('previewDownloadBtn');
    if(dlBtn) dlBtn.onclick = () => window.open(`/api/v1/files/${id}/download/`, '_blank');

    new bootstrap.Modal(modal).show();
}

// --- SHARE ---
let shareFileId = null;
function openShareDialog(id, name) {
    shareFileId = id;
    const modal = document.getElementById('shareModal');
    const label = document.getElementById('shareModalLabel');
    const body  = document.getElementById('shareModalBody');
    if(!modal) { openShareDialogLegacy(id, name); return; }
    label.textContent = `Share: ${name}`;
    body.innerHTML = `
    <div class="mb-4">
        <h6 class="fw-bold mb-2">Share with a person</h6>
        <div class="input-group mb-2">
            <input type="email" class="form-control" id="shareEmailInput" placeholder="Enter email address">
            <select class="form-select" id="shareRoleSelect" style="max-width:140px">
                <option value="reader">Viewer</option>
                <option value="commenter">Commenter</option>
                <option value="writer">Editor</option>
            </select>
            <button class="btn btn-primary" id="addShareBtn"><i class="bi bi-plus"></i> Add</button>
        </div>
        <div id="shareMsg"></div>
    </div>
    <div>
        <h6 class="fw-bold mb-2">People with access</h6>
        <div id="sharesList"><div class="text-muted">Loading...</div></div>
    </div>`;
    loadSharesList(id);
    document.getElementById('addShareBtn').onclick = () => addShare(id);
    new bootstrap.Modal(modal).show();
}

async function loadSharesList(fileId) {
    const el = document.getElementById('sharesList');
    try {
        const r = await axios.get(`/api/v1/permissions/?file=${fileId}`, { headers: authHeaders() });
        const perms = r.data.results || r.data || [];
        if(!perms.length) { el.innerHTML = '<div class="text-muted small">Not shared with anyone yet.</div>'; return; }
        el.innerHTML = perms.map(p=>`
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <div><div class="fw-semibold small">${esc(p.grantee_email||p.grantee_user_display||'—')}</div>
            <small class="text-muted">${esc(roleLabel(p.role))}</small></div>
            <button class="btn btn-sm btn-outline-danger" onclick="removeShare('${p.id}')"><i class="bi bi-trash3"></i> Remove</button>
        </div>`).join('');
    } catch(e) { el.innerHTML = `<div class="text-danger small">Failed to load: ${esc(e.message)}</div>`; }
}

function roleLabel(r){return{reader:'Can view',commenter:'Can comment',writer:'Can edit',owner:'Owner'}[r]||r;}

async function addShare(fileId) {
    const email = (document.getElementById('shareEmailInput').value||'').trim();
    const role  = document.getElementById('shareRoleSelect').value;
    const msg   = document.getElementById('shareMsg');
    if(!email||!email.includes('@')){ msg.innerHTML='<div class="alert alert-danger p-2 mb-0">Enter a valid email.</div>'; return; }
    try {
        await axios.post('/api/v1/permissions/', { file: fileId, grantee_email: email, permission_type: 'user', role }, { headers: { ...authHeaders(), 'Content-Type':'application/json' } });
        msg.innerHTML = `<div class="alert alert-success p-2 mb-0">Shared with ${esc(email)} as ${roleLabel(role)}.</div>`;
        document.getElementById('shareEmailInput').value = '';
        loadSharesList(fileId);
    } catch(err) {
        const e = err.response?.data?.grantee_email?.[0] || err.response?.data?.detail || err.message || 'Failed';
        msg.innerHTML = `<div class="alert alert-danger p-2 mb-0">${esc(e)}</div>`;
    }
}

async function removeShare(permId) {
    if(!confirm('Remove this person\'s access?')) return;
    try {
        await axios.delete(`/api/v1/permissions/${permId}/`, { headers: authHeaders() });
        showToast('Access removed', 'success');
        if(shareFileId) loadSharesList(shareFileId);
    } catch(e) { showToast('Failed to remove access', 'danger'); }
}

// --- STORAGE BAR ---
async function loadStorageBar() {
    try {
        const r = await axios.get('/api/v1/storage/quota/', { headers: authHeaders() });
        const q = r.data;
        const bar = document.getElementById('storageBar');
        const txt = document.getElementById('storageText');
        if(bar) { bar.style.width = `${q.percent_used}%`; bar.className = 'progress-bar ' + (q.percent_used>90?'bg-danger':q.percent_used>70?'bg-warning':''); }
        if(txt) txt.textContent = `${fmt(q.usage_bytes)} / ${fmt(q.limit_bytes)}`;
    } catch(e) { /* not fatal */ }
}

// --- TOAST ---
function showToast(msg, type='success') {
    let c = document.getElementById('toastContainer');
    if(!c){ c=document.createElement('div'); c.id='toastContainer'; c.className='toast-container position-fixed top-0 end-0 p-3'; document.body.appendChild(c); }
    const id = 'toast-'+Date.now();
    c.insertAdjacentHTML('beforeend',`<div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
        <div class="d-flex"><div class="toast-body">${esc(msg)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>`);
    const el = document.getElementById(id);
    new bootstrap.Toast(el,{delay:3500}).show();
    el.addEventListener('hidden.bs.toast', ()=>el.remove());
}

// --- SEARCH ---
function setupSearch() {
    const inp = document.getElementById('fileSearchInput') || document.getElementById('searchInput');
    if(inp) inp.addEventListener('input', e => { F.searchQuery = e.target.value; loadFiles(); });
}

// --- VIEW TOGGLE ---
function setupViewToggle() {
    document.querySelectorAll('[data-view-toggle]').forEach(btn => {
        btn.addEventListener('click', () => {
            F.currentView = btn.dataset.viewToggle;
            document.querySelectorAll('[data-view-toggle]').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            const table = document.getElementById('tableViewWrap');
            const grid  = document.getElementById('gridViewWrap');
            if(table) table.style.display = F.currentView==='table' ? '' : 'none';
            if(grid)  grid.style.display  = F.currentView==='grid'  ? '' : 'none';
        });
    });
}

// --- UPLOAD WIRING ---
function setupUpload() {
    const inp = document.getElementById('fileUploadInput');
    if(inp) inp.addEventListener('change', e => { if(e.target.files.length) uploadFiles(e.target.files); });
    const btn = document.getElementById('uploadBtn');
    if(btn) btn.addEventListener('click', () => document.getElementById('fileUploadInput')?.click());

    // Drag and drop on the whole page
    const dz = document.getElementById('uploadDropzone') || document.body;
    document.addEventListener('dragover', e => e.preventDefault());
    document.addEventListener('drop', e => {
        e.preventDefault();
        if(e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
    });
}

// --- NEW FOLDER ---
function setupFolderBtn() {
    const btn = document.getElementById('createFolderBtn');
    if(btn) btn.addEventListener('click', createFolder);
}

// --- LOGOUT ---
function setupLogout() {
    const btn = document.getElementById('logoutBtn');
    if(btn) btn.addEventListener('click', e => { e.preventDefault(); logout(); });
    document.getElementById('themeToggle')?.addEventListener('click', () => {
        const dark = document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', dark?'dark':'light');
        const ic = document.getElementById('themeIcon');
        if(ic) ic.className = dark?'bi bi-sun':'bi bi-moon';
    });
}

// --- INIT ---
function initFilesPage() {
    if(!tok()){ window.location.href='/frontend/login/'; return; }
    loadFiles();
    setupSearch();
    setupViewToggle();
    setupUpload();
    setupFolderBtn();
    setupLogout();
    if(typeof loadNotifications==='function') loadNotifications();
}

if(document.readyState==='loading') {
    document.addEventListener('DOMContentLoaded', initFilesPage);
} else {
    initFilesPage();
}
