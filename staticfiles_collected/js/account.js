const { bootstrapShell, apiRequest, renderAlert, renderToast, setTheme } = window.CloudVault;

async function loadProfileSettings() {
    const [profile, preferences] = await Promise.allSettled([
        apiRequest('get', '/users/profile/me/'),
        apiRequest('get', '/users/preferences/me/'),
    ]);

    const profileData = profile.status === 'fulfilled' ? profile.value : null;
    const preferenceData = preferences.status === 'fulfilled' ? preferences.value : null;

    const setValue = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) {
            element.value = value;
        }
    };

    const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) {
            element.textContent = value;
        }
    };

    if (profileData) {
        setValue('#profileFirstName', profileData.user?.first_name || '');
        setValue('#profileLastName', profileData.user?.last_name || '');
        setValue('#profileEmail', profileData.user?.email || '');
        setValue('#profileLocale', profileData.locale || 'en');
        setValue('#profilePhotoUrl', profileData.photo_url || '');
        setText('#profileQuota', profileData.storage_quota_limit_bytes ? `${profileData.storage_quota_usage_bytes || 0} / ${profileData.storage_quota_limit_bytes}` : 'Unlimited');
    }

    if (preferenceData) {
        setValue('#prefTheme', preferenceData.theme || 'system');
        setValue('#prefView', preferenceData.default_view || 'list');
        setValue('#prefSortField', preferenceData.sort_field || 'modified_time');
        setValue('#prefSortDirection', preferenceData.sort_direction || 'desc');
        setValue('#prefDensity', preferenceData.density || 'comfortable');
        const hiddenFiles = document.querySelector('#prefHiddenFiles');
        if (hiddenFiles) {
            hiddenFiles.checked = Boolean(preferenceData.show_hidden_files);
        }
    }
}

async function saveProfileSettings(event) {
    event.preventDefault();
    const getValue = (selector, fallback = '') => {
        const element = document.querySelector(selector);
        return element ? element.value : fallback;
    };

    const getChecked = (selector) => {
        const element = document.querySelector(selector);
        return element ? element.checked : false;
    };

    const profilePayload = {
        given_name: getValue('#profileFirstName').trim(),
        family_name: getValue('#profileLastName').trim(),
        locale: getValue('#profileLocale', 'en'),
        photo_url: getValue('#profilePhotoUrl').trim(),
    };

    const preferencePayload = {
        theme: getValue('#prefTheme', 'system'),
        default_view: getValue('#prefView', 'list'),
        sort_field: getValue('#prefSortField', 'modified_time'),
        sort_direction: getValue('#prefSortDirection', 'desc'),
        density: getValue('#prefDensity', 'comfortable'),
        show_hidden_files: getChecked('#prefHiddenFiles'),
    };

    try {
        await apiRequest('put', '/users/profile/me/', profilePayload);

        if (document.querySelector('#prefTheme')) {
            await apiRequest('put', '/users/preferences/me/', preferencePayload);
            setTheme(preferencePayload.theme === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : preferencePayload.theme);
        }

        renderToast('Profile settings saved', 'success');
    } catch (error) {
        renderAlert('#settingsAlert', 'Unable to save profile settings.', 'danger');
    }
}

function initFilePreview() {
    const input = document.querySelector('#avatarUpload');
    const preview = document.querySelector('#avatarPreview');
    if (!input || !preview) return;

    input.addEventListener('change', () => {
        const [file] = input.files || [];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            preview.src = reader.result;
            preview.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
    });
}

async function initSettingsPage() {
    await bootstrapShell('settings', { sidebar: true, requireAuth: true });
    await loadProfileSettings();
    initFilePreview();
    const form = document.querySelector('#settingsForm');
    if (form) form.addEventListener('submit', saveProfileSettings);
}

initSettingsPage();
