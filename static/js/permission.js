/* ──────────────────────────────────────────────────────────────
   permission.js  —  Permission management UI
   ────────────────────────────────────────────────────────────── */

// ── Auth helpers: api.js 참조 (getToken, tryRefresh, apiFetch) ─

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
    VDI:     ['CONNECT', 'DISCONNECT', 'POWER_ON', 'POWER_OFF', 'REBOOT', 'SNAPSHOT', 'RESTORE', 'ASSIGN', 'REVOKE', 'MONITOR', 'MANAGE'],
    STORAGE: ['READ', 'DOWNLOAD', 'SHARE', 'UPLOAD', 'DELETE', 'MANAGE'],
    RBAC:    ['READ', 'MANAGE'],
    BOARD:   ['CREATE', 'UPDATE', 'DELETE', 'READ', 'APPROVE', 'MANAGE'],
    POST:    ['UPDATE', 'DELETE', 'MANAGE'],
};

// ── State ─────────────────────────────────────────────────────

var state = {
    allPerms:      [],
    filtered:      [],
    pageSize:      20,
    page:          1,
    deleteId:      null,
    storageBuckets: [],
    storageObjects: [],
};

// ── API calls ─────────────────────────────────────────────────

async function fetchPermissions(type_) {
    var qs = type_ ? '?type=' + encodeURIComponent(type_) : '';
    return apiJSON('/api/rbac/permission' + qs, { method: 'GET' });
}

async function createPermission(type_, actions, resources, description) {
    return apiJSON('/api/rbac/permission', {
        method: 'POST',
        body: JSON.stringify({ type: type_, actions: actions, resources: resources, description: description || null }),
    });
}

async function deletePermission(id) {
    return apiJSON('/api/rbac/permission/' + encodeURIComponent(id), { method: 'DELETE' });
}

async function fetchBucketsMeta() {
    return apiJSON('/api/storage/buckets-meta', { method: 'GET' });
}

async function fetchDbResources(bucketName) {
    var qs = bucketName ? '?bucketName=' + encodeURIComponent(bucketName) : '';
    return apiJSON('/api/storage/resources' + qs, { method: 'GET' });
}

// ── Search / filter ───────────────────────────────────────────

function applyFilter() {
    var q    = document.getElementById('searchInput').value.trim().toLowerCase();
    var type = document.getElementById('typeFilter').value;
    state.filtered = state.allPerms.filter(function(p) {
        var matchType = !type || p.type === type;
        var actions   = (p.actions || []).join(' ').toLowerCase();
        var desc      = (p.description || '').toLowerCase();
        var matchQ    = !q || actions.includes(q) || p.type.toLowerCase().includes(q) || desc.includes(q);
        return matchType && matchQ;
    });
    state.page = 1;
}

function currentPage() {
    var start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

// ── Render ────────────────────────────────────────────────────
// escText: api.js 전역 alias 사용

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

        // Actions + Description
        var tdAction = document.createElement('td');
        var actionsWrap = document.createElement('div');
        actionsWrap.className = 'perm-action-badges';
        (p.actions || []).forEach(function(a) {
            var badge = document.createElement('span');
            badge.className = 'perm-action-badge';
            badge.textContent = a;
            actionsWrap.appendChild(badge);
        });
        tdAction.appendChild(actionsWrap);
        if (p.description) {
            var descDiv = document.createElement('div');
            descDiv.className = 'role-desc';
            descDiv.textContent = p.description;
            tdAction.appendChild(descDiv);
        }

        // Resources column
        var tdRes = document.createElement('td');
        var resources = p.resources || [];
        if (p.type === 'RBAC') {
            var dash = document.createElement('span');
            dash.className = 'no-perms';
            dash.textContent = '—';
            tdRes.appendChild(dash);
        } else if (resources.length === 0) {
            var allSpan = document.createElement('span');
            allSpan.className = 'no-perms';
            allSpan.textContent = '전체';
            tdRes.appendChild(allSpan);
        } else {
            var resWrap = document.createElement('div');
            resWrap.className = 'perm-tags';
            resources.forEach(function(r) {
                var chip = document.createElement('span');
                chip.className = 'perm-tag';
                if (r.resourceType === 'BUCKET') {
                    chip.style.background = '#dbeafe';
                    chip.style.color = '#1d4ed8';
                    chip.textContent = '🪣 ' + (r.resourceName || resolveBucketName(r.resourceId));
                    chip.title = r.resourceId;
                } else {
                    chip.style.background = '#dcfce7';
                    chip.style.color = '#15803d';
                    chip.textContent = '📄 ' + (r.resourceName || resolveObjectName(r.resourceId));
                    chip.title = r.resourceId;
                }
                resWrap.appendChild(chip);
            });
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
        var results = await Promise.allSettled([
            fetchPermissions(null),
            fetchBucketsMeta(),
            fetchDbResources(''),
        ]);
        state.allPerms      = Array.isArray(results[0].value) ? results[0].value : [];
        state.storageBuckets = Array.isArray(results[1].value) ? results[1].value : [];
        state.storageObjects = Array.isArray(results[2].value) ? results[2].value : [];
        applyFilter();
        renderTable();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오기 실패: ' + escText(e.message) + '</td></tr>';
    }
}

function resolveBucketName(bucketId) {
    var b = state.storageBuckets.find(function(b) { return b.bucketId === bucketId; });
    return b ? b.bucketName : bucketId.slice(0, 8) + '…';
}

function resolveObjectName(resourceId) {
    var r = state.storageObjects.find(function(r) { return r.resourceId === resourceId; });
    return r ? r.resourceName + ' (' + r.bucketName + ')' : resourceId.slice(0, 8) + '…';
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

    // "* 전체" 체크박스
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

    actions.forEach(function(a) {
        var lbl = document.createElement('label');
        lbl.className = 'action-item';

        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = a;
        cb.name = 'actionCheck';
        cb.addEventListener('change', function() {
            lbl.classList.toggle('is-checked', cb.checked);
            var all = grid.querySelectorAll('input[name=actionCheck]');
            var cnt = grid.querySelectorAll('input[name=actionCheck]:checked').length;
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

    // STORAGE만 리소스 선택 가능
    resSection.hidden = (type !== 'STORAGE');
    if (type === 'STORAGE') {
        loadPermBucketList();
        loadPermObjectList('');
    }
}

async function loadPermBucketList() {
    var listEl    = document.getElementById('permBucketList');
    var filterSel = document.getElementById('permBucketFilter');
    listEl.textContent = '불러오는 중...';
    try {
        var buckets = await fetchBucketsMeta();
        state.storageBuckets = Array.isArray(buckets) ? buckets : [];

        filterSel.innerHTML = '<option value="">모든 버킷</option>';
        state.storageBuckets.forEach(function(b) {
            var opt = document.createElement('option');
            opt.value = b.bucketName;
            opt.textContent = b.bucketName;
            filterSel.appendChild(opt);
        });

        listEl.innerHTML = '';
        if (state.storageBuckets.length === 0) {
            listEl.innerHTML = '<span style="color:var(--muted);font-size:13px">버킷이 없습니다.</span>';
            return;
        }
        state.storageBuckets.forEach(function(b) {
            var label = document.createElement('label');
            label.className = 'perm-item';
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = b.bucketId;
            var info = document.createElement('div');
            info.className = 'perm-item-info';
            var strong = document.createElement('strong');
            strong.textContent = b.bucketName;
            var sub = document.createElement('div');
            sub.style.cssText = 'font-size:11px;color:var(--muted)';
            sub.textContent = b.bucketId;
            info.appendChild(strong);
            info.appendChild(sub);
            label.appendChild(cb);
            label.appendChild(info);
            listEl.appendChild(label);
        });
    } catch (e) {
        listEl.textContent = '불러오기 실패: ' + e.message;
    }
}

async function loadPermObjectList(bucketName) {
    var listEl = document.getElementById('permObjectList');
    listEl.textContent = '불러오는 중...';
    try {
        var objects = await fetchDbResources(bucketName || '');
        state.storageObjects = Array.isArray(objects) ? objects : [];

        listEl.innerHTML = '';
        if (state.storageObjects.length === 0) {
            listEl.innerHTML = '<span style="color:var(--muted);font-size:13px">오브젝트가 없습니다.</span>';
            return;
        }
        state.storageObjects.forEach(function(r) {
            var label = document.createElement('label');
            label.className = 'perm-item';
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = r.resourceId;
            var info = document.createElement('div');
            info.className = 'perm-item-info';
            var strong = document.createElement('strong');
            strong.textContent = r.resourceName;
            var sub = document.createElement('div');
            sub.style.cssText = 'font-size:11px;color:var(--muted)';
            sub.textContent = r.bucketName + ' / ' + r.s3Key;
            info.appendChild(strong);
            info.appendChild(sub);
            label.appendChild(cb);
            label.appendChild(info);
            listEl.appendChild(label);
        });
    } catch (e) {
        listEl.textContent = '불러오기 실패: ' + e.message;
    }
}

function openAddModal() {
    document.getElementById('inputType').value = '';
    document.getElementById('inputPermDesc').value = '';
    document.getElementById('addPermModalErr').textContent = '';
    document.getElementById('btnSavePerm').disabled = false;
    document.getElementById('permBucketList').innerHTML = '';
    document.getElementById('permObjectList').innerHTML = '';
    document.getElementById('permBucketFilter').innerHTML = '<option value="">모든 버킷</option>';
    updateActionGrid();
    openModal('addPermModal');
    document.getElementById('inputType').focus();
}

async function savePerm() {
    var type_   = document.getElementById('inputType').value;
    var desc    = document.getElementById('inputPermDesc').value.trim();
    var checked = document.querySelectorAll('#actionGrid input[name=actionCheck]:checked');
    var actions = [];
    checked.forEach(function(cb) { actions.push(cb.value); });

    var errEl = document.getElementById('addPermModalErr');
    var btn   = document.getElementById('btnSavePerm');

    errEl.textContent = '';
    if (!type_)               { errEl.textContent = 'Type을 선택하세요.'; return; }
    if (actions.length === 0) { errEl.textContent = 'Action을 하나 이상 선택하세요.'; return; }

    var resources = [];
    if (type_ === 'STORAGE') {
        document.querySelectorAll('#permBucketList input:checked').forEach(function(cb) {
            resources.push({ resourceType: 'BUCKET', resourceId: cb.value });
        });
        document.querySelectorAll('#permObjectList input:checked').forEach(function(cb) {
            resources.push({ resourceType: 'OBJECT', resourceId: cb.value });
        });
    }

    btn.disabled = true;
    try {
        await createPermission(type_, actions, resources, desc || null);
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
    var label = perm.type + ':' + (perm.actions || []).join('+');
    if (perm.description) label += ' (' + perm.description + ')';
    strong.textContent = label;
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

    document.getElementById('inputType').addEventListener('change', updateActionGrid);

    document.getElementById('permBucketFilter').addEventListener('change', function() {
        loadPermObjectList(this.value);
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
