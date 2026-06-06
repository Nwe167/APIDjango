const { bootstrapShell, apiRequest, escapeHtml, formatDate } = window.CloudVault;

function riskBadge(score) {
    if (score >= 0.85) return 'text-bg-danger';
    if (score >= 0.6) return 'text-bg-warning';
    if (score >= 0.3) return 'text-bg-info';
    return 'text-bg-success';
}

async function renderSecurityTables() {
    const [auditLogs, spamFlags, dlpViolations] = await Promise.allSettled([
        apiRequest('get', '/audit-logs/'),
        Promise.resolve({ results: [] }),
        Promise.resolve({ results: [] }),
    ]);

    const auditList = auditLogs.status === 'fulfilled' ? (auditLogs.value.results || auditLogs.value || []) : [];
    const spamList = spamFlags.status === 'fulfilled' ? (spamFlags.value.results || spamFlags.value || []) : [];
    const dlpList = dlpViolations.status === 'fulfilled' ? (dlpViolations.value.results || dlpViolations.value || []) : [];

    const auditTarget = document.querySelector('#auditLogTableBody');
    if (auditTarget) {
        auditTarget.innerHTML = auditList.length ? auditList.map((item) => `
            <tr>
                <td>${escapeHtml(item.event_id)}</td>
                <td>${escapeHtml(item.actor_email || 'System')}</td>
                <td>${escapeHtml(item.file_name || '')}</td>
                <td><span class="badge text-bg-light">${escapeHtml(item.action)}</span></td>
                <td>${item.risk_score !== null && item.risk_score !== undefined ? `<span class="badge ${riskBadge(Number(item.risk_score))}">${Number(item.risk_score).toFixed(2)}</span>` : '<span class="badge text-bg-secondary">N/A</span>'}</td>
                <td>${formatDate(item.occurred_at)}</td>
            </tr>
        `).join('') : '<tr><td colspan="6"><div class="empty-state">No audit logs available.</div></td></tr>';
    }

    const spamTarget = document.querySelector('#spamTableBody');
    if (spamTarget) {
        spamTarget.innerHTML = spamList.length ? spamList.map((item) => `
            <tr>
                <td>${escapeHtml(item.file_name || '')}</td>
                <td>${escapeHtml(item.verdict)}</td>
                <td>${Number(item.confidence || 0).toFixed(2)}</td>
                <td>${escapeHtml(item.reason || '')}</td>
                <td>${formatDate(item.created_at)}</td>
            </tr>
        `).join('') : '<tr><td colspan="5"><div class="empty-state">Spam detection table is waiting for an exposed backend route.</div></td></tr>';
    }

    const dlpTarget = document.querySelector('#dlpTableBody');
    if (dlpTarget) {
        dlpTarget.innerHTML = dlpList.length ? dlpList.map((item) => `
            <tr>
                <td>${escapeHtml(item.policy_name || '')}</td>
                <td><span class="badge ${riskBadge(item.severity === 'critical' ? 1 : item.severity === 'high' ? 0.8 : item.severity === 'medium' ? 0.5 : 0.2)}">${escapeHtml(item.severity || '')}</span></td>
                <td>${escapeHtml(item.action_taken || '')}</td>
                <td>${escapeHtml(item.matched_pattern || '')}</td>
                <td>${formatDate(item.detected_at)}</td>
            </tr>
        `).join('') : '<tr><td colspan="5"><div class="empty-state">DLP violations will appear once the backend route is available.</div></td></tr>';
    }
}

async function initSecurityPage() {
    await bootstrapShell('admin-security', { sidebar: true, requireAuth: true });
    await renderSecurityTables();
}

initSecurityPage();
