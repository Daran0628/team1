/* ──────────────────────────────────────────────────────────────
   permission.js  —  Permission management UI
   ────────────────────────────────────────────────────────────── */

// ── Auth helpers ─────────────────────────────────────────────

function getToken() {
    return sessionStorage.getItem('access_token');
}

async function apiFetch(url, options) {
    const token = getToken();
    if (!token) { window.location.replace('/login'); return null; }

    const headers = Object.assign({ 'Content-Type': 'application/json',
                                    'Authorization': 'Bearer ' + token },
                                   (options && options.headers) || {});
    const res = await fetch(url, Object.assign({}, options, { headers }));

    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (!refreshed) { window.location.replace('/login'); return null; }
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
        const token = json && json.result && json.result.accessToken;
        if (!token) return false;
        sessionStorage.setItem('access_token', token);
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

// ── State ─────────────────────────────────────────────────────

const state = {
    allPerms:  [],
    filtered:  [],
    pageSize:  20,
    page:      1,
    deleteId:  null,
};

// ── API calls ─────────────────────────────────────────────────

async function fetchPermissions(resource) {
    const qs = resource ? '?resource=' + encodeURIComponent(resource) : '';
    return apiJSON('/api/rbac/permission' + qs, { method: 'GET' });
}

async function createPermission(resource, action) {
    return apiJSON('/api/rbac/permission', {
        method: 'POST',
        body: JSON.stringify({ resource: resource, action: action }),
    });
}

async function deletePermission(id) {
    return apiJSON('/api/rbac/permission/' + encodeURIComponent(id), { method: 'DELETE' });
}

// ── Search / filter ───────────────────────────────────────────

function applyFilter() {
    const q        = document.getElementById('searchInput').value.trim().toLowerCase();
    const resource = document.getElementById('resourceFilter').value;
    state.filtered = state.allPerms.filter(function(p) {
        const matchResource = !resource || p.resource === resource;
        const matchQ        = !q || p.action.toLowerCase().includes(q) ||
                              p.resource.toLowerCase().includes(q);
        return matchResource && matchQ;
    });
    state.page = 1;
}

function currentPage() {
    const start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

// ── Render ────────────────────────────────────────────────────

function renderTable() {
    const tbody = document.getElementById('permBody');
    const rows  = currentPage();
    const total = state.filtered.length;

    const countEl = document.getElementById('itemsCount');
    countEl.textContent = total + ' permission' + (total !== 1 ? 's' : '');

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="state-cell">권한이 없습니다.</td></tr>';
        renderPagination();
        return;
    }

    const fragment = document.createDocumentFragment();
    rows.forEach(function(p, idx) {
        const isLast = idx === rows.length - 1;

        const tr = document.createElement('tr');
        tr.className = 'role-row' + (isLast ? ' row-last' : '');

        const tdResource = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = 'badge badge-' + p.resource;
        badge.textContent = p.resource;
        tdResource.appendChild(badge);

        const tdAction = document.createElement('td');
        const nameDiv = document.createElement('div');
        nameDiv.className = 'role-name';
        nameDiv.textContent = p.action;
        tdAction.appendChild(nameDiv);

        const tdActs = document.createElement('td');
        const actWrap = document.createElement('div');
        actWrap.className = 'row-actions';

        const btnDel = document.createElement('button');
        btnDel.className = 'act-btn act-del';
        btnDel.textContent = 'Delete';
        btnDel.addEventListener('click', function() { openDeleteModal(p); });

        actWrap.appendChild(btnDel);
        tdActs.appendChild(actWrap);

        tr.appendChild(tdResource);
        tr.appendChild(tdAction);
        tr.appendChild(tdActs);
        fragment.appendChild(tr);
    });

    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    renderPagination();
}

function renderPagination() {
    const bar   = document.getElementById('paginationBar');
    const total = state.filtered.length;
    const pages = Math.max(1, Math.ceil(total / state.pageSize));

    if (total === 0) { bar.innerHTML = ''; return; }

    const start = (state.page - 1) * state.pageSize + 1;
    const end   = Math.min(state.page * state.pageSize, total);

    bar.innerHTML = '';

    const sizeWrap = document.createElement('div');
    sizeWrap.className = 'page-size-wrap';
    sizeWrap.textContent = 'Page size: ';
    const sel = document.createElement('select');
    [10, 20, 50].forEach(function(n) {
        const opt = document.createElement('option');
        opt.value = n;
        opt.textContent = n;
        if (n === state.pageSize) opt.selected = true;
        sel.appendChild(opt);
    });
    sel.addEventListener('change', function() {
        state.pageSize = parseInt(sel.value, 10);
        state.page = 1;
        renderTable();
    });
    sizeWrap.appendChild(sel);

    const navWrap = document.createElement('div');
    navWrap.className = 'page-nav-wrap';

    const info = document.createElement('span');
    info.textContent = start + '–' + end + ' of ' + total;

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '‹';
    prevBtn.disabled = state.page <= 1;
    prevBtn.addEventListener('click', function() { state.page--; renderTable(); });

    const pageInfo = document.createElement('span');
    pageInfo.textContent = state.page + ' / ' + pages;

    const nextBtn = document.createElement('button');
    nextBtn.textContent = '›';
    nextBtn.disabled = state.page >= pages;
    nextBtn.addEventListener('click', function() { state.page++; renderTable(); });

    navWrap.appendChild(info);
    navWrap.appendChild(prevBtn);
    navWrap.appendChild(pageInfo);
    navWrap.appendChild(nextBtn);

    bar.appendChild(sizeWrap);
    bar.appendChild(navWrap);
}

// ── Load ──────────────────────────────────────────────────────

async function loadPermissions() {
    const tbody = document.getElementById('permBody');
    tbody.innerHTML = '<tr><td colspan="3" class="state-cell">불러오는 중...</td></tr>';
    try {
        const data = await fetchPermissions(null);
        state.allPerms = Array.isArray(data) ? data : [];
        applyFilter();
        renderTable();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="state-cell">불러오기 실패: ' + e.message + '</td></tr>';
    }
}

// ── Modal helpers ─────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).removeAttribute('hidden'); }
function closeModal(id) { document.getElementById(id).setAttribute('hidden', ''); }

// ── Add Permission modal ──────────────────────────────────────

function openAddModal() {
    document.getElementById('inputResource').value = '';
    document.getElementById('inputAction').value   = '';
    document.getElementById('addPermModalErr').textContent = '';
    document.getElementById('btnSavePerm').disabled = false;
    openModal('addPermModal');
    document.getElementById('inputResource').focus();
}

async function savePerm() {
    const resource = document.getElementById('inputResource').value;
    const action   = document.getElementById('inputAction').value.trim();
    const errEl    = document.getElementById('addPermModalErr');
    const btn      = document.getElementById('btnSavePerm');

    errEl.textContent = '';
    if (!resource) { errEl.textContent = 'Resource를 선택하세요.'; return; }
    if (!action)   { errEl.textContent = 'Action은 필수입니다.'; return; }

    btn.disabled = true;
    try {
        await createPermission(resource, action);
        closeModal('addPermModal');
        await loadPermissions();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Delete modal ──────────────────────────────────────────────

function openDeleteModal(perm) {
    state.deleteId = perm.permission_id;
    const msg = document.getElementById('deletePermMsg');
    msg.textContent = '';
    const strong = document.createElement('strong');
    strong.textContent = perm.resource + ':' + perm.action;
    msg.appendChild(document.createTextNode('권한 '));
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'));
    document.getElementById('deletePermErr').textContent = '';
    document.getElementById('btnConfirmDeletePerm').disabled = false;
    openModal('deletePermModal');
}

async function confirmDelete() {
    const errEl = document.getElementById('deletePermErr');
    const btn   = document.getElementById('btnConfirmDeletePerm');
    errEl.textContent = '';
    btn.disabled = true;
    try {
        await deletePermission(state.deleteId);
        closeModal('deletePermModal');
        await loadPermissions();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Wire up events ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('btnAddPerm').addEventListener('click', openAddModal);
    document.getElementById('btnRefresh').addEventListener('click', loadPermissions);

    document.getElementById('searchInput').addEventListener('input', function() {
        applyFilter();
        renderTable();
    });
    document.getElementById('resourceFilter').addEventListener('change', function() {
        applyFilter();
        renderTable();
    });

    document.getElementById('btnSavePerm').addEventListener('click', savePerm);
    document.getElementById('inputAction').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') savePerm();
    });

    document.getElementById('btnConfirmDeletePerm').addEventListener('click', confirmDelete);

    document.querySelectorAll('[data-close]').forEach(function(btn) {
        btn.addEventListener('click', function() { closeModal(btn.dataset.close); });
    });

    document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) overlay.setAttribute('hidden', '');
        });
    });

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-overlay:not([hidden])').forEach(function(el) {
            el.setAttribute('hidden', '');
        });
    });

    loadPermissions();
});
