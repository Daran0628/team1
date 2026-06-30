/* ──────────────────────────────────────────────────────────────
   objstorage.js  —  Object Storage Browser
   ────────────────────────────────────────────────────────────── */

// ── Auth helpers ─────────────────────────────────────────────

function getToken() {
    return sessionStorage.getItem('access_token');
}

async function apiFetch(url, options) {
    const token = getToken();
    if (!token) { window.location.replace('/login'); return null; }

    const isFormData = options && options.body instanceof FormData;
    const headers = Object.assign(
        isFormData ? {} : { 'Content-Type': 'application/json' },
        { 'Authorization': 'Bearer ' + token },
        (options && options.headers) || {}
    );

    const res = await fetch(url, Object.assign({}, options, { headers }));

    if (res.status === 401) {
        const ok = await tryRefresh();
        if (!ok) { window.location.replace('/login'); return null; }
        headers['Authorization'] = 'Bearer ' + getToken();
        return fetch(url, Object.assign({}, options, { headers }));
    }
    return res;
}

async function tryRefresh() {
    try {
        const res = await fetch('/api/auth/refresh', { method: 'GET', credentials: 'include' });
        if (!res.ok) return false;
        const json = await res.json();
        const t = json && json.result && json.result.accessToken;
        if (!t) return false;
        sessionStorage.setItem('access_token', t);
        return true;
    } catch (_) { return false; }
}

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error((json && json.message) || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

// ── State ────────────────────────────────────────────────────

let currentBucket = null;
let currentPrefix = '';
let allObjects    = [];
let shareObjectName = null;
let deleteTarget    = null;

// ── Init ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadBuckets();
});

// ── Event Listeners ──────────────────────────────────────────

function setupEventListeners() {

    // Bucket list
    document.getElementById('bucketList').addEventListener('click', e => {
        const item = e.target.closest('.bucket-item[data-name]');
        if (item) selectBucket(item.dataset.name);
    });

    // New bucket button
    document.getElementById('btnNewBucket').addEventListener('click', () => openModal('createBucketModal'));
    document.getElementById('btnSubmitBucket').addEventListener('click', createBucket);
    document.getElementById('inputBucketName').addEventListener('keydown', e => {
        if (e.key === 'Enter') createBucket();
    });

    // Toolbar
    document.getElementById('btnUpload').addEventListener('click', () => {
        document.getElementById('fileInput').click();
    });
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
    document.getElementById('btnRefresh').addEventListener('click', loadObjects);
    document.getElementById('btnCreateFolder').addEventListener('click', () => openModal('createFolderModal'));
    document.getElementById('btnSubmitFolder').addEventListener('click', createFolder);
    document.getElementById('inputFolderName').addEventListener('keydown', e => {
        if (e.key === 'Enter') createFolder();
    });

    // Search
    document.getElementById('searchInput').addEventListener('input', e => filterObjects(e.target.value));

    // Select all
    document.getElementById('checkAll').addEventListener('change', e => {
        document.querySelectorAll('.row-check:not(:disabled)').forEach(cb => {
            cb.checked = e.target.checked;
        });
        syncDeleteButton();
    });

    // Delete selected
    document.getElementById('btnDeleteSelected').addEventListener('click', deleteSelectedObjects);

    // Object table delegation (clicks + checkbox changes)
    const tbody = document.getElementById('objectBody');
    tbody.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        e.preventDefault();
        const { action, name } = btn.dataset;
        if (action === 'navigate') navigateToPrefix(name);
        else if (action === 'download') downloadObject(name);
        else if (action === 'share') openShareModal(name);
        else if (action === 'delete') confirmDelete(name);
    });
    tbody.addEventListener('change', e => {
        if (e.target.classList.contains('row-check')) syncDeleteButton();
    });

    // Breadcrumb delegation
    document.getElementById('pathBreadcrumb').addEventListener('click', e => {
        const link = e.target.closest('[data-nav]');
        if (!link) return;
        e.preventDefault();
        if (link.dataset.nav === 'bucket') selectBucket(link.dataset.bucket);
        else if (link.dataset.nav === 'prefix') navigateToPrefix(link.dataset.prefix);
    });

    // Share modal
    document.getElementById('btnGenerateShareUrl').addEventListener('click', generateShareUrl);
    document.getElementById('btnCopyShareUrl').addEventListener('click', copyShareUrl);

    // Delete confirm
    document.getElementById('btnConfirmDelete').addEventListener('click', executeDelete);

    // Close buttons (data-close-modal)
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.dataset.closeModal));
    });

    // Overlay click-to-close
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', e => {
            if (e.target === overlay) closeModal(overlay.id);
        });
    });
}

function syncDeleteButton() {
    const anyChecked = document.querySelectorAll('.row-check:checked').length > 0;
    document.getElementById('btnDeleteSelected').hidden = !anyChecked;
}

// ── Buckets ───────────────────────────────────────────────────

async function loadBuckets() {
    try {
        const buckets = await apiJSON('/api/storage/buckets');
        renderBuckets(buckets || []);
    } catch (err) {
        showToast('버킷 목록 로드 실패: ' + err.message, 'error');
        document.getElementById('bucketList').innerHTML =
            '<li class="empty-buckets">로드 실패</li>';
    }
}

function renderBuckets(buckets) {
    const list = document.getElementById('bucketList');
    if (!buckets.length) {
        list.innerHTML = '<li class="empty-buckets">버킷 없음</li>';
        return;
    }
    list.innerHTML = buckets.map(b => `
        <li class="bucket-item${currentBucket === b.bucket_name ? ' active' : ''}"
            data-name="${esc(b.bucket_name)}">
            <span class="bucket-icon">🗄</span>
            <span class="bucket-name">${esc(b.bucket_name)}</span>
        </li>
    `).join('');

    if (!currentBucket && buckets.length > 0) {
        selectBucket(buckets[0].bucket_name);
    }
}

async function selectBucket(name) {
    currentBucket = name;
    currentPrefix = '';

    document.querySelectorAll('.bucket-item').forEach(el => {
        el.classList.toggle('active', el.dataset.name === name);
    });

    document.getElementById('welcomeState').hidden = true;
    document.getElementById('objectBrowser').hidden = false;
    document.getElementById('searchInput').value = '';

    updateBreadcrumb();
    await loadObjects();
}

async function createBucket() {
    const name = document.getElementById('inputBucketName').value.trim();
    if (!name) { showToast('버킷 이름을 입력하세요.', 'error'); return; }
    try {
        await apiJSON('/api/storage/buckets', {
            method: 'POST',
            body: JSON.stringify({ bucketName: name }),
        });
        closeModal('createBucketModal');
        document.getElementById('inputBucketName').value = '';
        showToast('버킷이 생성되었습니다.', 'success');
        await loadBuckets();
        selectBucket(name);
    } catch (err) {
        showToast('버킷 생성 실패: ' + err.message, 'error');
    }
}

// ── Objects ───────────────────────────────────────────────────

async function loadObjects() {
    if (!currentBucket) return;
    const tbody = document.getElementById('objectBody');
    tbody.innerHTML = '<tr><td colspan="5" class="state-cell loading">불러오는 중...</td></tr>';

    try {
        const url = `/api/storage/buckets/${enc(currentBucket)}/objects`
            + `?prefix=${enc(currentPrefix)}&recursive=false`;
        const result = await apiJSON(url);
        allObjects = result || [];
        renderObjects(allObjects);
        updateObjectCount();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="state-cell error">로드 실패: ${esc(err.message)}</td></tr>`;
    }
}

function renderObjects(objects) {
    const tbody = document.getElementById('objectBody');
    document.getElementById('checkAll').checked = false;
    syncDeleteButton();

    if (!objects.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="state-cell">이 위치에 오브젝트가 없습니다.</td></tr>';
        return;
    }

    tbody.innerHTML = objects.map(obj => {
        const isDir = obj.is_dir;
        const displayName = getDisplayName(obj.object_name);
        const icon = isDir ? '📁' : getFileIcon(obj.object_name);
        const size = isDir ? '—' : formatSize(obj.size || 0);
        const modified = (isDir || !obj.last_modified) ? '—' : formatDate(obj.last_modified);

        const nameCell = isDir
            ? `<span class="file-icon">${icon}</span>`
              + `<a class="dir-link" href="#" data-action="navigate" data-name="${esc(obj.object_name)}">${esc(displayName)}</a>`
            : `<span class="file-icon">${icon}</span><span>${esc(displayName)}</span>`;

        const actionBtns = isDir
            ? '<span class="no-actions">—</span>'
            : `<button class="btn-action" title="다운로드" data-action="download" data-name="${esc(obj.object_name)}">⬇</button>`
              + ` <button class="btn-action btn-share" title="공유 링크" data-action="share" data-name="${esc(obj.object_name)}">🔗</button>`
              + ` <button class="btn-action btn-danger-action" title="삭제" data-action="delete" data-name="${esc(obj.object_name)}">🗑</button>`;

        return `<tr>
            <td class="col-check"><input type="checkbox" class="row-check" ${isDir ? 'disabled' : ''} data-name="${esc(obj.object_name)}"></td>
            <td><div class="col-name-cell">${nameCell}</div></td>
            <td class="col-modified">${modified}</td>
            <td class="col-size">${size}</td>
            <td class="col-obj-actions actions-cell">${actionBtns}</td>
        </tr>`;
    }).join('');
}

function filterObjects(query) {
    const q = query.trim().toLowerCase();
    renderObjects(q ? allObjects.filter(o => getDisplayName(o.object_name).toLowerCase().includes(q)) : allObjects);
}

function updateObjectCount() {
    const files = allObjects.filter(o => !o.is_dir);
    const dirs  = allObjects.filter(o => o.is_dir);
    const parts = [];
    if (dirs.length)  parts.push(`폴더 ${dirs.length}개`);
    if (files.length) parts.push(`파일 ${files.length}개`);
    document.getElementById('objectCount').textContent = parts.join(', ') || '비어있음';
}

// ── Navigation ─────────────────────────────────────────────────

function navigateToPrefix(prefix) {
    currentPrefix = prefix;
    document.getElementById('searchInput').value = '';
    updateBreadcrumb();
    loadObjects();
}

function updateBreadcrumb() {
    const nav = document.getElementById('pathBreadcrumb');
    if (!currentBucket) {
        nav.innerHTML = '<span class="bc-root">Object Storage</span>';
        return;
    }

    let html = `<a class="bc-link" href="#" data-nav="bucket" data-bucket="${esc(currentBucket)}">${esc(currentBucket)}</a>`;

    if (currentPrefix) {
        const segs = currentPrefix.replace(/\/$/, '').split('/').filter(Boolean);
        let acc = '';
        segs.forEach((seg, i) => {
            acc += seg + '/';
            html += '<span class="bc-sep">/</span>';
            if (i === segs.length - 1) {
                html += `<span class="bc-current">${esc(seg)}</span>`;
            } else {
                html += `<a class="bc-link" href="#" data-nav="prefix" data-prefix="${esc(acc)}">${esc(seg)}</a>`;
            }
        });
    }

    nav.innerHTML = html;
}

// ── Upload ────────────────────────────────────────────────────

async function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    if (!files.length || !currentBucket) return;

    const progress = document.getElementById('uploadProgress');
    progress.hidden = false;

    for (const file of files) {
        const fd = new FormData();
        fd.append('file', file);
        fd.append('objectName', currentPrefix + file.name);

        try {
            const res = await fetch(
                `/api/storage/buckets/${enc(currentBucket)}/objects`,
                { method: 'POST', headers: { 'Authorization': 'Bearer ' + getToken() }, body: fd }
            );
            const json = await res.json();
            if (!res.ok || json.isSuccess === false) throw new Error(json.message || 'upload failed');
            showToast(`${file.name} 업로드 완료`, 'success');
        } catch (err) {
            showToast(`${file.name} 업로드 실패: ${err.message}`, 'error');
        }
    }

    progress.hidden = true;
    e.target.value = '';
    await loadObjects();
}

// ── Download ──────────────────────────────────────────────────

async function downloadObject(objectName) {
    try {
        const url = `/api/storage/buckets/${enc(currentBucket)}/objects/download-url`
            + `?objectName=${enc(objectName)}&expires=3600`;
        const result = await apiJSON(url);
        if (result && result.url) window.open(result.url, '_blank');
    } catch (err) {
        showToast('다운로드 링크 생성 실패: ' + err.message, 'error');
    }
}

// ── Share ─────────────────────────────────────────────────────

function openShareModal(objectName) {
    shareObjectName = objectName;
    document.getElementById('shareFileName').textContent = getDisplayName(objectName);
    document.getElementById('shareDays').value    = '0';
    document.getElementById('shareHours').value   = '12';
    document.getElementById('shareMinutes').value = '0';
    document.getElementById('shareUrlInput').value = '';
    document.getElementById('shareExpiry').textContent = '';
    document.getElementById('shareUrlWrap').hidden = true;
    openModal('shareModal');
}

async function generateShareUrl() {
    if (!currentBucket || !shareObjectName) return;

    const days    = Math.max(0, parseInt(document.getElementById('shareDays').value)    || 0);
    const hours   = Math.max(0, parseInt(document.getElementById('shareHours').value)   || 0);
    const minutes = Math.max(0, parseInt(document.getElementById('shareMinutes').value) || 0);
    const totalSeconds = days * 86400 + hours * 3600 + minutes * 60;

    if (totalSeconds <= 0) {
        showToast('만료 시간을 설정해주세요.', 'error');
        return;
    }

    try {
        const url = `/api/storage/buckets/${enc(currentBucket)}/objects/share-url`
            + `?objectName=${enc(shareObjectName)}&days=${days}&hours=${hours}&minutes=${minutes}`;
        const result = await apiJSON(url);
        if (result && result.url) {
            document.getElementById('shareUrlInput').value = result.url;
            document.getElementById('shareUrlWrap').hidden = false;

            const expiry = new Date(Date.now() + totalSeconds * 1000);
            document.getElementById('shareExpiry').textContent =
                '만료: ' + expiry.toLocaleString('ko-KR');
        }
    } catch (err) {
        showToast('공유 링크 생성 실패: ' + err.message, 'error');
    }
}

async function copyShareUrl() {
    const url = document.getElementById('shareUrlInput').value;
    if (!url) return;
    try {
        await navigator.clipboard.writeText(url);
        showToast('링크가 클립보드에 복사되었습니다.', 'success');
    } catch (_) {
        const input = document.getElementById('shareUrlInput');
        input.select();
        document.execCommand('copy');
        showToast('링크가 복사되었습니다.', 'success');
    }
}

// ── Delete ────────────────────────────────────────────────────

function confirmDelete(objectName) {
    deleteTarget = objectName;
    document.getElementById('deleteTargetName').textContent = getDisplayName(objectName);
    openModal('deleteModal');
}

async function executeDelete() {
    if (!currentBucket || !deleteTarget) return;
    try {
        await apiJSON(
            `/api/storage/buckets/${enc(currentBucket)}/objects?objectName=${enc(deleteTarget)}`,
            { method: 'DELETE' }
        );
        closeModal('deleteModal');
        showToast('오브젝트가 삭제되었습니다.', 'success');
        await loadObjects();
    } catch (err) {
        showToast('삭제 실패: ' + err.message, 'error');
    }
    deleteTarget = null;
}

async function deleteSelectedObjects() {
    const checked = Array.from(document.querySelectorAll('.row-check:checked'))
        .map(cb => cb.dataset.name);
    if (!checked.length) return;

    let failed = 0;
    for (const name of checked) {
        try {
            await apiJSON(
                `/api/storage/buckets/${enc(currentBucket)}/objects?objectName=${enc(name)}`,
                { method: 'DELETE' }
            );
        } catch (_) { failed++; }
    }

    const ok = checked.length - failed;
    if (ok) showToast(`${ok}개 삭제 완료${failed ? `, ${failed}개 실패` : ''}`, failed ? 'error' : 'success');
    await loadObjects();
}

// ── Create Folder ─────────────────────────────────────────────

async function createFolder() {
    const raw = document.getElementById('inputFolderName').value.trim();
    if (!raw || !currentBucket) { showToast('폴더 이름을 입력하세요.', 'error'); return; }

    const folderKey = currentPrefix + raw.replace(/\/$/, '') + '/';
    const fd = new FormData();
    fd.append('objectName', folderKey + '.keep');
    fd.append('file', new Blob([], { type: 'application/octet-stream' }), '.keep');

    try {
        const res = await fetch(
            `/api/storage/buckets/${enc(currentBucket)}/objects`,
            { method: 'POST', headers: { 'Authorization': 'Bearer ' + getToken() }, body: fd }
        );
        const json = await res.json();
        if (!res.ok || json.isSuccess === false) throw new Error(json.message || 'failed');
        closeModal('createFolderModal');
        document.getElementById('inputFolderName').value = '';
        showToast('폴더가 생성되었습니다.', 'success');
        await loadObjects();
    } catch (err) {
        showToast('폴더 생성 실패: ' + err.message, 'error');
    }
}

// ── Modal helpers ─────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).hidden = false; }
function closeModal(id) { document.getElementById(id).hidden = true; }

// ── Utilities ─────────────────────────────────────────────────

function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function enc(str) { return encodeURIComponent(str); }

function getDisplayName(objectName) {
    const name = String(objectName).replace(/\/$/, '');
    const parts = name.split('/');
    return parts[parts.length - 1] || objectName;
}

function getFileIcon(name) {
    const ext = (String(name).split('.').pop() || '').toLowerCase();
    const map = {
        png:'🖼', jpg:'🖼', jpeg:'🖼', gif:'🖼', svg:'🖼', webp:'🖼', bmp:'🖼',
        pdf:'📄', doc:'📝', docx:'📝', xls:'📊', xlsx:'📊', ppt:'📑', pptx:'📑',
        txt:'📃', md:'📃', csv:'📃', json:'📃', xml:'📃', yaml:'📃', yml:'📃',
        zip:'📦', tar:'📦', gz:'📦', rar:'📦',
        mp4:'🎬', avi:'🎬', mov:'🎬', mkv:'🎬', webm:'🎬',
        mp3:'🎵', wav:'🎵', flac:'🎵',
        py:'🐍', js:'⚙', ts:'⚙', html:'🌐', css:'🎨', sh:'⚙', sql:'🗃',
    };
    return map[ext] || '📄';
}

function formatSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
    return (bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1) + ' ' + sizes[i];
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return String(dateStr);
        return d.toLocaleString('ko-KR', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit',
        });
    } catch (_) { return String(dateStr); }
}

// ── Toast ─────────────────────────────────────────────────────

function showToast(message, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
    }, 3500);
}
