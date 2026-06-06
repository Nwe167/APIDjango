const { apiRequest, escapeHtml, formatDate, renderToast } = window.CloudVault;

async function loadComments(fileId) {
    if (!fileId) return [];
    const response = await apiRequest('get', `/comments/?file_id=${encodeURIComponent(fileId)}`);
    return response.results || response || [];
}

function renderReplies(replies) {
    return replies.length ? replies.map((reply) => `
        <div class="border-start ps-3 mt-3">
            <div class="fw-bold small">${escapeHtml(reply.author_name || 'Member')}</div>
            <div>${escapeHtml(reply.content)}</div>
            <small class="text-secondary">${formatDate(reply.created_at)}</small>
        </div>
    `).join('') : '';
}

function renderComments(fileId, comments) {
    const target = document.querySelector('#commentSidebar');
    if (!target) return;

    target.innerHTML = comments.length ? comments.map((comment) => `
        <div class="content-card mb-3" data-comment-id="${comment.id}">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-bold">${escapeHtml(comment.author_name || 'Member')}</div>
                    <small class="text-secondary">${formatDate(comment.created_at)}</small>
                </div>
                <span class="badge ${comment.status === 'resolved' ? 'text-bg-success' : 'text-bg-light'}">${escapeHtml(comment.status)}</span>
            </div>
            <p class="mt-3 mb-2">${escapeHtml(comment.content)}</p>
            <div class="small text-secondary">${escapeHtml(comment.quoted_file_content || '')}</div>
            ${renderReplies(comment.replies || [])}
            <div class="d-flex gap-2 mt-3">
                <button class="btn btn-outline-primary btn-sm" data-resolve-comment="${comment.id}" ${comment.status === 'resolved' ? 'disabled' : ''}>Resolve</button>
                <button class="btn btn-outline-secondary btn-sm" data-reply-comment="${comment.id}">Reply</button>
            </div>
        </div>
    `).join('') : '<div class="empty-state">No comments yet.</div>';

    target.querySelectorAll('[data-resolve-comment]').forEach((button) => {
        button.addEventListener('click', async () => {
            await apiRequest('post', `/comments/${button.dataset.resolveComment}/resolve/`);
            renderToast('Comment resolved', 'success');
            await initializeCommentSidebar(fileId);
        });
    });

    target.querySelectorAll('[data-reply-comment]').forEach((button) => {
        button.addEventListener('click', () => {
            const commentId = button.dataset.replyComment;
            const reply = prompt('Reply to comment');
            if (!reply) return;
            apiRequest('post', '/comment-replies/', { comment: commentId, content: reply, action: 'reply' })
                .then(() => initializeCommentSidebar(fileId))
                .then(() => renderToast('Reply posted', 'success'))
                .catch(() => renderToast('Unable to post reply', 'danger'));
        });
    });
}

async function initializeCommentSidebar(fileId) {
    const comments = await loadComments(fileId);
    renderComments(fileId, comments);
}

function bindCommentComposer(fileId) {
    const form = document.querySelector('#commentForm');
    if (!form) return;

    form.onsubmit = async (event) => {
        event.preventDefault();
        const content = form.commentContent.value.trim();
        if (!content) return;

        try {
            await apiRequest('post', '/comments/', {
                file: fileId,
                content,
                status: 'open',
            });
            form.reset();
            await initializeCommentSidebar(fileId);
            renderToast('Comment added', 'success');
        } catch (error) {
            renderToast('Unable to add comment', 'danger');
        }
    };
}

window.CloudVaultComments = {
    initializeCommentSidebar,
    bindCommentComposer,
};
