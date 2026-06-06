// Simple files.js - minimal version for loading files
console.log('[files.js] Loading...');

const fileState = {
    view: 'table',
    page: 1,
    pageSize: 12,
    query: '',
    folderId: '',
    allFiles: [],
    selectedFile: null,
    currentFolder: null,
};

// Helper function to show input modal instead of prompt()
async function showInputModal(title, placeholder = '', defaultValue = '') {
    return new Promise((resolve) => {
        const modal = document.getElementById('inputModal');
        const titleEl = document.getElementById('inputModalLabel');
        const input = document.getElementById('inputModalValue');
        const okBtn = document.getElementById('inputModalOkBtn');
        
        if (!modal || !input) {
            console.error('Input modal elements not found');
            resolve(null);
            return;
        }
        
        titleEl.textContent = title;
        input.placeholder = placeholder;
        input.value = defaultValue;
        input.focus();
        
        // Clear previous listeners
        const newOkBtn = okBtn.cloneNode(true);
        okBtn.parentNode.replaceChild(newOkBtn, okBtn);
        
        const handleOk = () => {
            const value = input.value.trim();
            if (bsModal) bsModal.hide();
            resolve(value || null);
        };
        
        const handleCancel = () => {
            if (bsModal) bsModal.hide();
            resolve(null);
        };
        
        newOkBtn.addEventListener('click', handleOk);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleOk();
            if (e.key === 'Escape') handleCancel();
        });
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            resolve(null);
        }, { once: true });
    });
}

function parseQueryParams() {
    const params = new URLSearchParams(window.location.search);
    fileState.query = params.get('q') || '';
    fileState.folderId = params.get('folder') || '';
    fileState.selectedFile = params.get('file') || null;
}

function getVisibleFiles() {
    return fileState.allFiles.filter((file) => {
        if (fileState.query && !file.name.toLowerCase().includes(fileState.query.toLowerCase())) return false;
        if (!fileState.folderId && file.parent) return false;
        if (fileState.folderId && file.parent !== fileState.folderId) return false;
        return !file.trashed;
    });
}

function paginate(items) {
    const start = (fileState.page - 1) * fileState.pageSize;
    return items.slice(start, start + fileState.pageSize);
}

async function refreshFiles() {
    if (!window.CloudVault || !window.CloudVault.fetchAllPages) {
        console.error('CloudVault.fetchAllPages not available');
        return;
    }
    
    try {
        fileState.allFiles = await window.CloudVault.fetchAllPages('/files/');
        console.log(`✅ Loaded ${fileState.allFiles.length} files`);
        renderCurrentView();
    } catch (error) {
        console.error('Error fetching files:', error);
    }
}

function renderCurrentView() {
    const filteredFiles = getVisibleFiles();
    const pageItems = paginate(filteredFiles);
    renderFilesTable(pageItems);
    
    // Update file count
    const fileCountLabel = document.querySelector('#filesTotalCount');
    if (fileCountLabel) {
        fileCountLabel.textContent = `(${filteredFiles.length} items)`;
    }
}

function bindUploadButton() {
    const uploadBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Upload File'));
    if (uploadBtn && !uploadBtn.dataset.bound) {
        uploadBtn.dataset.bound = 'true';
        uploadBtn.addEventListener('click', () => {
            console.log('[files.js] Upload button clicked');
            const fileInput = document.querySelector('#fileUploadInput');
            if (fileInput) {
                fileInput.click();
            } else {
                alert('File input not found. Cannot upload.');
            }
        });
        console.log('[files.js] Upload button listener attached');
    }
}

function bindFolderButton() {
    const folderBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('New Folder'));
    if (folderBtn && !folderBtn.dataset.bound) {
        folderBtn.dataset.bound = 'true';
        folderBtn.addEventListener('click', handleCreateFolder);
        console.log('[files.js] Folder button listener attached');
    }
}

async function handleCreateFolder() {
    // Use modal dialog instead of prompt
    const folderName = await showInputModal('Create Folder', 'Enter folder name...');
    if (!folderName || !folderName.trim()) {
        console.log('[files.js] Folder creation cancelled');
        return;
    }

    if (!window.CloudVault || !window.CloudVault.apiRequest) {
        alert('API not available');
        return;
    }

    try {
        console.log('[files.js] Creating folder:', folderName);
        await window.CloudVault.apiRequest('post', '/files/', {
            name: folderName.trim(),
            parent: fileState.folderId || null,
            mime_type: 'folder',
            space: 'drive',
        });
        
        console.log('[files.js] Folder created successfully');
        if (window.CloudVault?.renderToast) {
            window.CloudVault.renderToast('Folder created', 'success');
        } else {
            alert('Folder created successfully');
        }
        await refreshFiles();
    } catch (error) {
        console.error('Error creating folder:', error);
        if (window.CloudVault?.renderAlert) {
            window.CloudVault.renderAlert('#filesAlert', `Error creating folder: ${error.message}`, 'danger');
        } else {
            alert(`Error creating folder: ${error.message}`);
        }
    }
}

function bindFileUploadInput() {
    const fileInput = document.querySelector('#fileUploadInput');
    if (fileInput && !fileInput.dataset.bound) {
        fileInput.dataset.bound = 'true';
        fileInput.addEventListener('change', async (e) => {
            console.log('[files.js] Files selected for upload');
            const files = Array.from(e.target.files || []);
            if (!files.length) return;

            if (!window.CloudVault || !window.CloudVault.uploadFile) {
                alert('Upload functionality not available');
                return;
            }

            for (const file of files) {
                const formData = new FormData();
                formData.append('name', file.name);
                formData.append('mime_type', file.type || 'application/octet-stream');
                formData.append('file_path', file);
                if (fileState.folderId) formData.append('parent', fileState.folderId);
                formData.append('space', 'drive');

                try {
                    await window.CloudVault.uploadFile('/files/', formData, {
                        onUploadProgress(progressEvent) {
                            const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
                            const indicator = document.querySelector('#uploadProgress');
                            if (indicator) indicator.style.width = `${percent}%`;
                        },
                    });
                } catch (error) {
                    console.error(`Upload failed for ${file.name}:`, error);
                    if (window.CloudVault?.renderToast) {
                        window.CloudVault.renderToast(`Upload failed for ${file.name}`, 'danger');
                    }
                }
            }

            if (window.CloudVault?.renderToast) {
                window.CloudVault.renderToast('Upload completed', 'success');
            }
            
            // Clear the file input
            e.target.value = '';
            
            // Refresh the file list
            await refreshFiles();
        });
        console.log('[files.js] File upload input listener attached');
    }
}

function renderFilesTable(files) {
    const target = document.querySelector('#filesTableBody');
    if (!target) return;

    if (!files || files.length === 0) {
        target.innerHTML = '<tr><td colspan="8" class="text-center py-4">No files found</td></tr>';
        return;
    }

    target.innerHTML = files.map((file) => {
        const bytesToHuman = window.CloudVault?.bytesToHuman || ((b) => (b / 1024 / 1024).toFixed(2) + ' MB');
        const formatDate = window.CloudVault?.formatDate || ((d) => new Date(d).toLocaleDateString());
        const escapeHtml = window.CloudVault?.escapeHtml || ((h) => h.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'));
        
        return `
            <tr class="file-row" data-file-id="${file.id}">
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div>${escapeHtml(file.name)}</div>
                    </div>
                </td>
                <td>${escapeHtml(file.mime_type || '')}</td>
                <td>${bytesToHuman(file.size_bytes || 0)}</td>
                <td>${escapeHtml(file.owner_email || 'Me')}</td>
                <td>${file.trashed ? 'Trashed' : 'Active'}</td>
                <td>${file.starred ? '⭐' : ''}</td>
                <td>${formatDate(file.modified_time)}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-primary" onclick="handleFileAction('${file.id}', 'preview')" title="Preview">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-info" onclick="handleFileAction('${file.id}', 'download')" title="Download">
                            <i class="bi bi-download"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="handleFileAction('${file.id}', 'rename')" title="Rename">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-outline-secondary" onclick="handleFileAction('${file.id}', 'star')" title="Star">
                            <i class="bi bi-star${file.starred ? '-fill' : ''}"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="handleFileAction('${file.id}', 'trash')" title="Trash">
                            <i class="bi bi-trash3"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function openPreviewModal(fileId) {
    const file = fileState.allFiles.find(f => f.id === fileId);
    if (!file) return;
    
    const modalTitle = document.querySelector('#previewModalLabel');
    const modalBody = document.querySelector('#previewModalBody');
    
    if (modalTitle) modalTitle.textContent = file.name;
    if (modalBody) {
        modalBody.innerHTML = `<p>Preview for ${file.name} (${file.mime_type})</p>`;
    }
    
    const modalElement = document.getElementById('previewModal');
    if (modalElement) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }
}

async function handleFileAction(fileId, action) {
    const file = fileState.allFiles.find(f => f.id === fileId);
    if (!file) {
        console.error('[files.js] File not found:', fileId);
        return;
    }

    console.log(`[files.js] File action: ${action} on ${file.name}`);

    try {
        if (action === 'preview') {
            openPreviewModal(fileId);
        } 
        else if (action === 'download') {
            handleDownloadFile(file);
        }
        else if (action === 'rename') {
            await handleRenameFile(file);
        }
        else if (action === 'star') {
            await handleStarFile(file);
        }
        else if (action === 'trash') {
            await handleTrashFile(file);
        }
    } catch (error) {
        console.error(`Error handling ${action}:`, error);
        if (window.CloudVault?.renderToast) {
            window.CloudVault.renderToast(`Action failed: ${error.message}`, 'danger');
        } else {
            alert(`Error: ${error.message}`);
        }
    }
}

function handleDownloadFile(file) {
    console.log('[files.js] Downloading file:', file.name);
    
    // Create a hidden link and trigger download
    const link = document.createElement('a');
    link.href = `/media/${file.file_path || ''}`;
    link.download = file.name;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    if (window.CloudVault?.renderToast) {
        window.CloudVault.renderToast('Download started', 'info');
    }
}

async function handleRenameFile(file) {
    const newName = await showInputModal('Rename File', 'Enter new file name...', file.name);
    if (!newName || !newName.trim() || newName === file.name) {
        return;
    }

    if (!window.CloudVault || !window.CloudVault.apiRequest) {
        alert('API not available');
        return;
    }

    console.log('[files.js] Renaming file from', file.name, 'to', newName);
    await window.CloudVault.apiRequest('patch', `/files/${file.id}/`, {
        name: newName.trim()
    });

    if (window.CloudVault?.renderToast) {
        window.CloudVault.renderToast('File renamed', 'success');
    } else {
        alert('File renamed successfully');
    }
    
    await refreshFiles();
}

async function handleStarFile(file) {
    if (!window.CloudVault || !window.CloudVault.apiRequest) {
        alert('API not available');
        return;
    }

    console.log('[files.js]', file.starred ? 'Unstarring' : 'Starring', 'file:', file.name);
    
    // Toggle star status
    const newStarred = !file.starred;
    await window.CloudVault.apiRequest('patch', `/files/${file.id}/`, {
        starred: newStarred
    });

    if (window.CloudVault?.renderToast) {
        window.CloudVault.renderToast(newStarred ? 'File starred' : 'Star removed', 'info');
    }
    
    await refreshFiles();
}

async function handleTrashFile(file) {
    if (!confirm(`Are you sure you want to trash "${file.name}"?`)) {
        return;
    }

    if (!window.CloudVault || !window.CloudVault.apiRequest) {
        alert('API not available');
        return;
    }

    console.log('[files.js] Trashing file:', file.name);
    await window.CloudVault.apiRequest('patch', `/files/${file.id}/`, {
        trashed: true
    });

    if (window.CloudVault?.renderToast) {
        window.CloudVault.renderToast('File moved to trash', 'warning');
    } else {
        alert('File moved to trash');
    }
    
    await refreshFiles();
}

async function initFilesPage() {
    try {
        console.log('Initializing files page...');
        parseQueryParams();
        await refreshFiles();
        
        // Bind button handlers
        bindUploadButton();
        bindFolderButton();
        bindFileUploadInput();
        
        console.log('✅ Files page initialized');
    } catch (error) {
        console.error('Error initializing files page:', error);
    }
}

// Initialize when DOM is ready and CloudVault is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFilesPage);
} else {
    // Wait a moment for CloudVault to load
    setTimeout(initFilesPage, 100);
}

console.log('[files.js] Loaded');
