/* ──────────────────────────────────────────────────────────────
   permission.js  —  Permission management UI
   ────────────────────────────────────────────────────────────── */

// ── Auth helpers ─────────────────────────────────────────────

function getToken() {
    return sessionStorage.getItem('access_token');
}

async function apiFetch(url, options) {
    var token = getToken();
    if (!token) { window.location.replace('/login'); return null; }

    var headers = Object.assign({ 'Content-Type': 'application/json',
                                   'Authorization': 'Bearer ' + token },
                                  (options && options.headers) || {});
    var res = await fetch(url, Object.assign({}, options, { headers: headers }));

    if (res.status === 401) {
        var refreshed = await tryRefresh();
        if (!refreshed) { window.location.replace('/login'); return null; }
        headers['Authorization'] = 'Bearer ' + getToken();
        return fetch(url, Object.assign({}, options, { headers: headers }));
    }
    return res;
}

async function tryRefresh() {
    try {
        var res = await fetch('/api/auth/refresh', { method: 'GET', credentials: 'include' });
        if (!res.ok) return false;
        var json = await res.json();
        var token = json && json.result && json.result.accessToken;
        if (!token) return false;
        sessionStorage.setItem('access_token', token);
        return true;
    } catch (_) { return false; }
}

async function apiJSON(url, options) {
    var res = await apiFetch(url, options);
    if (!res) return null;
    var json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error((json && json.message) || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

// ── Action definitions per type ───────────────────────────────

var ACTIONS_BY_TYPE = {
    STORAGE: ['READ', 'DOWNLOAD', 'UPLOAD', 'DELETE', 'RENAME', 'MOVE', 'SHARE', 'MANAGE'],
    VDI:     ['CONNECT', 'DISCONNECT', 'POWER_ON', 'POWER_OFF', 'REBOOT', 'SNAPSHOT', 'RESTORE', 'ASSIGN', 'REVOKE', 'MONITOR', 'MANAGE'],
    RBAC:    ['READ', 'MANAGE'],
};

// ── State ─────────────────────────────────────────────────────

var state = {
    allPerms:    [],
    filtered:    [],
    pageSize:    20,
    page:        1,
    deleteId:    null,
    pendingResIds: [],   // resource UUIDs staged in the add modal
};

// ── API calls ─────────────────────────────────────────────────

async function fetchPermissions(type_) {
    var qs = type_ ? '?type=' + encodeURIComponent(type_) : '';
    return apiJSON('/api/rbac/permission' + qs, { method: 'GET' });
}

async function createPermission(type_, actions, resourceIds) {
    return apiJSON('/api/rbac/permission', {
        method: 'POST',
        body: JSON.stringify({ type: type_, actions: actions, resourceIds: resourceIds }),
    });
}

async function deletePermission(id) {
    return apiJSON('/api/rbac/permission/' + encodeURIComponent(id), { method: 'DELETE' });
}

// ── Search / filter ───────────────────────────────────────────

function applyFilter() {
    var q    = document.getElementById('searchInput').value.trim().toLowerCase();
    var type = document.getElementById('typeFilter').value;
    state.filtered = state.allPerms.filter(function(p) {
        var matchType = !type || p.type === type;
        var matchQ    = !q || p.action.toLowerCase().includes(q) ||
                        p.type.toLowerCase().includes(q);
        return matchType && matchQ;
    });
    state.page = 1;
}

function currentPage() {
    var start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

// ── Render ────────────────────────────────────────────────────

function escText(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function renderTable() {
    var tbody = document.getElementById('permBody');
    var rows  = currentPage();
    var total = state.filtered.length;

    var countEl = document.getElementById('itemsCount');
    countEl.textContent = total + ' permission' + (total !== 1 ? 's' : '');

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">권한이 없습니다.</td></tr>';
        renderPagination();
        return;
    }

    var fragment = document.createDocumentFragment();
    rows.forEach(function(p, idx) {
        var isLast = idx === rows.length - 1;

        var tr = document.createElement('tr');
        tr.className = 'role-row' + (isLast ? ' row-last' : '');

        // Type badge
        var tdType = document.createElement('td');
        var badge = document.createElement('span');
        badge.className = 'badge badge-' + p.type;
        badge.textContent = p.type;
        tdType.appendChild(badge);

        // Action
        var tdAction = document.createElement('td');
        var nameDiv = document.createElement('div');
        nameDiv.className = 'role-name';
        nameDiv.textContent = p.action;
        tdAction.appendChild(nameDiv);

        // Resource IDs
        var tdRes = document.createElement('td');
        if (p.type === 'RBAC' || !p.resource_ids || p.resource_ids.length === 0) {
            var noRes = document.createElement('span');
            noRes.className = 'no-perms';
            noRes.textContent = p.type === 'RBAC' ? '—' : '없음';
            tdRes.appendChild(noRes);
        } else {
            var resWrap = document.createElement('div');
            resWrap.className = 'perm-tags';
            var showCount = Math.min(p.resource_ids.length, 3);
            for (var i = 0; i < showCount; i++) {
                var chip = document.createElement('span');
                chip.className = 'perm-tag';
                chip.title = p.resource_ids[i];
                chip.textContent = p.resource_ids[i].slice(0, 8) + '…';
                resWrap.appendChild(chip);
            }
            if (p.resource_ids.length > 3) {
                var more = document.createElement('span');
                more.className = 'perm-tag';
                more.style.color = 'var(--muted)';
                more.textContent = '+' + (p.resource_ids.length - 3) + ' more';
                resWrap.appendChild(more);
            }
            tdRes.appendChild(resWrap);
        }

        // Delete action
        var tdActs = document.createElement('td');
        var actWrap = document.createElement('div');
        actWrap.className = 'row-actions';
        var btnDel = document.createElement('button');
        btnDel.className = 'act-btn act-del';
        btnDel.textContent = 'Delete';
        btnDel.addEventListener('click', function() { openDeleteModal(p); });
        actWrap.appendChild(btnDel);
        tdActs.appendChild(actWrap);

        tr.appendChild(tdType);
        tr.appendChild(tdAction);
        tr.appendChild(tdRes);
        tr.appendChild(tdActs);
        fragment.appendChild(tr);
    });

    tbody.innerHTML = '';
    tbody.appendChild(fragment);
    renderPagination();
}

function renderPagination() {
    var bar   = document.getElementById('paginationBar');
    var total = state.filtered.length;
    var pages = Math.max(1, Math.ceil(total / state.pageSize));

    if (total === 0) { bar.innerHTML = ''; return; }

    var start = (state.page - 1) * state.pageSize + 1;
    var end   = Math.min(state.page * state.pageSize, total);

    bar.innerHTML = '';

    var sizeWrap = document.createElement('div');
    sizeWrap.className = 'page-size-wrap';
    sizeWrap.textContent = 'Page size: ';
    var sel = document.createElement('select');
    [10, 20, 50].forEach(function(n) {
        var opt = document.createElement('option');
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

    var navWrap = document.createElement('div');
    navWrap.className = 'page-nav-wrap';

    var info = document.createElement('span');
    info.textContent = start + '–' + end + ' of ' + total;

    var prevBtn = document.createElement('button');
    prevBtn.textContent = '‹';
    prevBtn.disabled = state.page <= 1;
    prevBtn.addEventListener('click', function() { state.page--; renderTable(); });

    var pageInfo = document.createElement('span');
    pageInfo.textContent = state.page + ' / ' + pages;

    var nextBtn = document.createElement('button');
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
    var tbody = document.getElementById('permBody');
    tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오는 중...</td></tr>';
    try {
        var data = await fetchPermissions(null);
        state.allPerms = Array.isArray(data) ? data : [];
        applyFilter();
        renderTable();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오기 실패: ' + escText(e.message) + '</td></tr>';
    }
}

// ── Modal helpers ─────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).removeAttribute('hidden'); }
function closeModal(id) { document.getElementById(id).setAttribute('hidden', ''); }

// ── Add Permission modal ──────────────────────────────────────

function updateActionGrid() {
    var type       = document.getElementById('inputType').value;
    var grid       = document.getElementById('actionGrid');
    var resSection = document.getElementById('resourceIdsSection');

    grid.innerHTML = '';
    if (!type) {
        var placeholder = document.createElement('span');
        placeholder.className = 'no-perms';
        placeholder.textContent = 'Type을 먼저 선택하세요';
        grid.appendChild(placeholder);
        resSection.hidden = true;
        return;
    }

    var actions = ACTIONS_BY_TYPE[type] || [];

    // ── "* 전체" 체크박스 ─────────────────────────────────────
    var allLbl = document.createElement('label');
    allLbl.className = 'action-item action-item-all';

    var allCb = document.createElement('input');
    allCb.type = 'checkbox';
    allCb.addEventListener('change', function() {
        var checked = allCb.checked;
        allLbl.classList.toggle('is-checked', checked);
        grid.querySelectorAll('input[name=actionCheck]').forEach(function(cb) {
            cb.checked = checked;
            cb.closest('label').classList.toggle('is-checked', checked);
        });
    });

    var allSpan = document.createElement('span');
    allSpan.textContent = '* 전체';
    allLbl.appendChild(allCb);
    allLbl.appendChild(allSpan);
    grid.appendChild(allLbl);

    // ── 개별 action 체크박스 ──────────────────────────────────
    actions.forEach(function(a) {
        var lbl = document.createElement('label');
        lbl.className = 'action-item';

        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = a;
        cb.name = 'actionCheck';
        cb.addEventListener('change', function() {
            lbl.classList.toggle('is-checked', cb.checked);
            // 전체 체크박스 동기화
            var all     = grid.querySelectorAll('input[name=actionCheck]');
            var cnt     = grid.querySelectorAll('input[name=actionCheck]:checked').length;
            allCb.checked       = (cnt === all.length);
            allCb.indeterminate = (cnt > 0 && cnt < all.length);
            allLbl.classList.toggle('is-checked', allCb.checked);
        });

        var span = document.createElement('span');
        span.textContent = a;

        lbl.appendChild(cb);
        lbl.appendChild(span);
        grid.appendChild(lbl);
    });

    resSection.hidden = (type === 'RBAC');
}

function renderResIdList() {
    var list = document.getElementById('resIdList');
    list.innerHTML = '';
    state.pendingResIds.forEach(function(rid, idx) {
        var chip = document.createElement('span');
        chip.className = 'res-id-chip';
        chip.title = rid;
        chip.textContent = rid.slice(0, 16) + '…';

        var xBtn = document.createElement('button');
        xBtn.type = 'button';
        xBtn.className = 'revoke-x';
        xBtn.textContent = '✕';
        xBtn.addEventListener('click', function() {
            state.pendingResIds.splice(idx, 1);
            renderResIdList();
        });
        chip.appendChild(xBtn);
        list.appendChild(chip);
    });
}

function addResId() {
    var input = document.getElementById('inputResId');
    var rid   = input.value.trim();
    if (!rid) return;
    if (state.pendingResIds.includes(rid)) {
        document.getElementById('addPermModalErr').textContent = '이미 추가된 Resource ID입니다.';
        return;
    }
    state.pendingResIds.push(rid);
    input.value = '';
    document.getElementById('addPermModalErr').textContent = '';
    renderResIdList();
}

function openAddModal() {
    state.pendingResIds = [];
    document.getElementById('inputType').value  = '';
    document.getElementById('inputResId').value = '';
    document.getElementById('addPermModalErr').textContent = '';
    document.getElementById('btnSavePerm').disabled = false;
    updateActionGrid();
    renderResIdList();
    openModal('addPermModal');
    document.getElementById('inputType').focus();
}

async function savePerm() {
    var type_   = document.getElementById('inputType').value;
    var checked = document.querySelectorAll('#actionGrid input[type=checkbox]:checked');
    var actions = [];
    checked.forEach(function(cb) { actions.push(cb.value); });

    var errEl = document.getElementById('addPermModalErr');
    var btn   = document.getElementById('btnSavePerm');

    errEl.textContent = '';
    if (!type_)           { errEl.textContent = 'Type을 선택하세요.'; return; }
    if (actions.length === 0) { errEl.textContent = 'Action을 하나 이상 선택하세요.'; return; }

    btn.disabled = true;
    try {
        await createPermission(type_, actions, state.pendingResIds.slice());
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
    var msg = document.getElementById('deletePermMsg');
    msg.textContent = '';
    var strong = document.createElement('strong');
    strong.textContent = perm.type + ':' + perm.action;
    msg.appendChild(document.createTextNode('권한 '));
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'));
    document.getElementById('deletePermErr').textContent = '';
    document.getElementById('btnConfirmDeletePerm').disabled = false;
    openModal('deletePermModal');
}

async function confirmDelete() {
    var errEl = document.getElementById('deletePermErr');
    var btn   = document.getElementById('btnConfirmDeletePerm');
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
    document.getElementById('typeFilter').addEventListener('change', function() {
        applyFilter();
        renderTable();
    });

    // Modal: type change → update action checkbox grid
    document.getElementById('inputType').addEventListener('change', function() {
        updateActionGrid();
    });

    // Resource ID add
    document.getElementById('btnAddResId').addEventListener('click', addResId);
    document.getElementById('inputResId').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); addResId(); }
    });

    document.getElementById('btnSavePerm').addEventListener('click', savePerm);
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
