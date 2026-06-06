const {
    bootstrapShell,
    apiRequest,
    bytesToHuman,
    formatDate,
    getFileIconClass,
    escapeHtml,
    renderToast,
    fetchAllPages,
} = window.CloudVault;

function renderFolderPage(files) {
    const treeTarget = document.querySelector('#folderTree');
    const gridTarget = document.querySelector('#folderGrid');
    const totalTarget = document.querySelector('#folderTotalCount');

    const folders = files.filter((file) => (file.mime_type || '').includes('folder') || file.mime_type === 'folder');
    if (totalTarget) totalTarget.textContent = `${folders.length} folders`;

    if (treeTarget) {
        const buildTree = (parentId) => {
            const children = folders.filter((folder) => String(folder.parent || '') === String(parentId || ''));
            if (!children.length) return '';

            return `<ul>${children.map((folder) => `
                <li class="tree-item">
                    <button type="button" data-folder-open="${folder.id}"><i class="bi bi-folder2 me-2"></i>${escapeHtml(folder.name)}</button>
                    ${buildTree(folder.id)}
                </li>
            `).join('')}</ul>`;
        };

        treeTarget.innerHTML = buildTree('') || '<div class="empty-state py-4">No folders yet.</div>';
        treeTarget.querySelectorAll('[data-folder-open]').forEach((button) => {
            button.addEventListener('click', () => {
                window.location.href = `files.html?folder=${button.getAttribute('data-folder-open')}`;
            });
        });
    }

    if (gridTarget) {
        gridTarget.innerHTML = folders.length ? folders.map((folder) => `
            <a class="folder-card p-3 d-block" href="files.html?folder=${folder.id}">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="file-icon mb-3"><i class="bi bi-folder2"></i></div>
                        <div class="fw-bold">${escapeHtml(folder.name)}</div>
                        <small class="text-secondary">${escapeHtml(folder.description || 'Folder')}</small>
                    </div>
                    <span class="badge badge-soft-primary">Folder</span>
                </div>
                <div class="d-flex justify-content-between text-secondary small mt-3">
                    <span>${bytesToHuman(folder.size_bytes || 0)}</span>
                    <span>${formatDate(folder.modified_time)}</span>
                </div>
            </a>
        `).join('') : '<div class="empty-state">No folders to display.</div>';
    }
}

function renderSharedPage(permissions, shareLinks) {
    const permissionsBody = document.querySelector('#sharedPermissionsBody');
    const linksBody = document.querySelector('#sharedLinksBody');
    if (permissionsBody) {
        permissionsBody.innerHTML = permissions.length ? permissions.map((item) => `
            <tr>
                <td>${escapeHtml(item.file_name || '')}</td>
                <td>${escapeHtml(item.grantee_name || item.grantee_email || '')}</td>
                <td><span class="badge text-bg-light">${escapeHtml(item.permission_type)}</span></td>
                <td><span class="badge badge-soft-primary">${escapeHtml(item.role)}</span></td>
                <td>${item.expiration_time ? formatDate(item.expiration_time) : 'Never'}</td>
            </tr>
        `).join('') : '<tr><td colspan="5"><div class="empty-state">No collaborators yet.</div></td></tr>';
    }

    if (linksBody) {
        linksBody.innerHTML = shareLinks.length ? shareLinks.map((item) => `
            <tr>
                <td>${escapeHtml(item.file_name || '')}</td>
                <td class="text-truncate" style="max-width:220px">${window.location.origin}/shared.html?token=${escapeHtml(item.token)}</td>
                <td>${escapeHtml(item.role)}</td>
                <td>${item.revoked_at ? '<span class="badge text-bg-secondary">Revoked</span>' : '<span class="badge text-bg-success">Active</span>'}</td>
                <td>${item.expires_at ? formatDate(item.expires_at) : 'No expiry'}</td>
            </tr>
        `).join('') : '<tr><td colspan="5"><div class="empty-state">No public share links yet.</div></td></tr>';
    }
}

function renderTrashPage(items) {
    const target = document.querySelector('#trashTableBody');
    const counter = document.querySelector('#trashTotalCount');
    if (counter) counter.textContent = `${items.length} items`;

    if (!target) return;

    target.innerHTML = items.length ? items.map((item) => `
        <tr>
            <td>${escapeHtml(item.original_name)}</td>
            <td>${escapeHtml(item.owner_email || '')}</td>
            <td>${bytesToHuman(item.size_bytes || 0)}</td>
            <td>${escapeHtml(item.state)}</td>
            <td>${formatDate(item.trashed_at)}</td>
            <td class="text-end">
                <button class="btn btn-outline-primary btn-sm" data-trash-action="restore" data-id="${item.id}">Restore</button>
                <button class="btn btn-outline-danger btn-sm" data-trash-action="purge" data-id="${item.id}">Delete forever</button>
            </td>
        </tr>
    `).join('') : '<tr><td colspan="6"><div class="empty-state">Trash is empty.</div></td></tr>';

    target.querySelectorAll('[data-trash-action]').forEach((button) => {
        button.addEventListener('click', async () => {
            const { trashAction, id } = button.dataset;
            if (trashAction === 'restore') {
                await apiRequest('post', `/trash/${id}/restore/`);
                renderToast('Item restored', 'success');
            } else {
                await apiRequest('delete', `/trash/${id}/purge/`);
                renderToast('Item deleted forever', 'warning');
            }
            await initTrashPage();
        });
    });
}

function renderActivityPage(items) {
    const target = document.querySelector('#activityFeedList');
    if (!target) return;

    const iconMap = {
        file_create: 'bi-file-earmark-plus',
        file_edit: 'bi-pencil-square',
        file_rename: 'bi-pencil-square',
        file_move: 'bi-arrows-move',
        file_copy: 'bi-files',
        file_delete: 'bi-trash3',
        file_restore: 'bi-arrow-counterclockwise',
        file_share: 'bi-share',
        comment_add: 'bi-chat-left-text',
        permission_change: 'bi-people',
    };

    target.innerHTML = items.length ? items.map((item) => `
        <div class="content-card mb-3">
            <div class="d-flex gap-3 align-items-start">
                <div class="activity-icon"><i class="bi ${iconMap[item.action] || 'bi-activity'}"></i></div>
                <div class="flex-grow-1">
                    <div class="fw-bold">${escapeHtml(item.action.replaceAll('_', ' '))}</div>
                    <div class="text-secondary">${escapeHtml(item.file_name || 'System')}</div>
                    <div class="text-secondary small">${formatDate(item.occurred_at)}</div>
                </div>
            </div>
        </div>
    `).join('') : '<div class="empty-state">No activity yet.</div>';
}

async function initFoldersPage() {
    await bootstrapShell('folders', { sidebar: true, requireAuth: true });
    const files = await fetchAllPages('/files/');
    renderFolderPage(files);
}

async function initSharedPage() {
    await bootstrapShell('shared', { sidebar: true, requireAuth: true });
    const [permissions, shareLinks] = await Promise.all([
        fetchAllPages('/permissions/'),
        fetchAllPages('/share-links/'),
    ]);
    renderSharedPage(permissions, shareLinks);
}

async function initTrashPage() {
    await bootstrapShell('trash', { sidebar: true, requireAuth: true });
    const trashItems = await fetchAllPages('/trash/');
    renderTrashPage(trashItems);

    const emptyBtn = document.querySelector('#emptyTrashBtn');
    if (emptyBtn) {
        emptyBtn.addEventListener('click', async () => {
            const trashItemsCurrent = await fetchAllPages('/trash/');
            for (const item of trashItemsCurrent) {
                await apiRequest('delete', `/trash/${item.id}/purge/`);
            }
            renderToast('Trash cleared', 'success');
            await initTrashPage();
        });
    }
}

async function initActivityPage() {
    await bootstrapShell('activity', { sidebar: true, requireAuth: true });
    const activities = await fetchAllPages('/activity/');
    renderActivityPage(activities);
}

window.CloudVaultPages = {
    initFoldersPage,
    initSharedPage,
    initTrashPage,
    initActivityPage,
};
