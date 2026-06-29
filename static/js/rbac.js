/* ──────────────────────────────────────────────────────────────
   rbac.js  —  Teleport-style RBAC management UI
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
        // Try token refresh
        const refreshed = await tryRefresh();
        if (!refreshed) { window.location.replace('/login'); return null; }
        const newToken = getToken();
        headers['Authorization'] = 'Bearer ' + newToken;
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
    if (!res.ok || (json.isSuccess === false)) {
        throw new Error((json && json.message) || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

// ── State ─────────────────────────────────────────────────────

const state = {
    allRoles:    [],   // raw from API
    filtered:    [],   // after search
    pageSize:    20,
    page:        1,
    expanded:    new Set(),   // role IDs with open detail row
    allPerms:    [],   // all permissions (for assign modal)
    editingRole: null, // { id, name, description } or null for new
    assignRoleId: null,
    deleteRoleId: null,
};

// ── API calls ─────────────────────────────────────────────────

async function fetchRoles() {
    return apiJSON('/api/rbac/role', { method: 'GET' });
}

async function fetchPermissions(resource) {
    const qs = resource ? '?resource=' + encodeURIComponent(resource) : '';
    return apiJSON('/api/rbac/permission' + qs, { method: 'GET' });
}

async function createRole(name, desc) {
    return apiJSON('/api/rbac/role', {
        method: 'POST',
        body: JSON.stringify({ roleName: name, description: desc || null }),
    });
}

async function updateRole(id, name, desc) {
    return apiJSON('/api/rbac/role/' + encodeURIComponent(id), {
        method: 'PUT',
        body: JSON.stringify({ roleName: name, description: desc || null }),
    });
}

async function deleteRole(id) {
    return apiJSON('/api/rbac/role/' + encodeURIComponent(id), { method: 'DELETE' });
}


async function assignPermissions(roleId, permissionIds) {
    return apiJSON('/api/rbac/permission/assign', {
        method: 'POST',
        body: JSON.stringify({ roleId: roleId, permissionIds: permissionIds }),
    });
}

async function revokePermission(roleId, permissionId) {
    const qs = '?roleId='       + encodeURIComponent(roleId) +
               '&permissionId=' + encodeURIComponent(permissionId);
    return apiJSON('/api/rbac/permission/assign' + qs, { method: 'DELETE' });
}

// ── Render helpers ────────────────────────────────────────────

function escText(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function renderBadge(resource) {
    const cls = 'badge badge-' + escText(resource);
    const span = document.createElement('span');
    span.className = cls;
    span.textContent = resource;
    return span.outerHTML;
}

// ── Table rendering ───────────────────────────────────────────

function applySearch() {
    const q = document.getElementById('searchInput').value.trim().toLowerCase();
    state.filtered = q
        ? state.allRoles.filter(function(r) {
            return r.role_name.toLowerCase().includes(q) ||
                   (r.description || '').toLowerCase().includes(q);
          })
        : state.allRoles.slice();
    state.page = 1;
}

function currentPage() {
    const start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

function renderTable() {
    const tbody = document.getElementById('rolesBody');
    const rows  = currentPage();
    const total = state.filtered.length;

    // update count
    const countEl = document.getElementById('itemsCount');
    countEl.textContent = total + ' role' + (total !== 1 ? 's' : '');

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">역할이 없습니다.</td></tr>';
        renderPagination();
        return;
    }

    const fragment = document.createDocumentFragment();
    rows.forEach(function(role, idx) {
        const isLast = idx === rows.length - 1;
        const rid    = role.role_id;
        const isOpen = state.expanded.has(rid);
        const perms  = role.permissions || [];

        // ── Main row
        const tr = document.createElement('tr');
        tr.className = 'role-row' + (isLast && !isOpen ? ' row-last' : '');
        tr.dataset.id = rid;

        const tdToggle = document.createElement('td');
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'toggle-btn' + (isOpen ? ' open' : '');
        toggleBtn.title = isOpen ? '접기' : '펼치기';
        toggleBtn.textContent = '▶';
        toggleBtn.addEventListener('click', function() { toggleExpand(rid); });
        tdToggle.appendChild(toggleBtn);

        const tdName = document.createElement('td');
        const nameDiv = document.createElement('div');
        nameDiv.className = 'role-name';
        nameDiv.textContent = role.role_name;
        tdName.appendChild(nameDiv);
        if (role.description) {
            const descDiv = document.createElement('div');
            descDiv.className = 'role-desc';
            descDiv.textContent = role.description;
            tdName.appendChild(descDiv);
        }

        const tdPerms = document.createElement('td');
        const pill = document.createElement('span');
        pill.className = 'perm-pill';
        pill.textContent = perms.length;
        tdPerms.appendChild(pill);

        const tdActs = document.createElement('td');
        const actWrap = document.createElement('div');
        actWrap.className = 'row-actions';

        const btnAssign = document.createElement('button');
        btnAssign.className = 'act-btn';
        btnAssign.textContent = 'Assign Permissions';
        btnAssign.addEventListener('click', function() { openAssignModal(role); });

        const btnEdit = document.createElement('button');
        btnEdit.className = 'act-btn';
        btnEdit.textContent = 'Edit';
        btnEdit.addEventListener('click', function() { openEditModal(role); });

        const btnDel = document.createElement('button');
        btnDel.className = 'act-btn act-del';
        btnDel.textContent = 'Delete';
        btnDel.addEventListener('click', function() { openDeleteModal(role); });


        actWrap.appendChild(btnAssign);
        actWrap.appendChild(btnEdit);
        actWrap.appendChild(btnDel);
        tdActs.appendChild(actWrap);

        tr.appendChild(tdToggle);
        tr.appendChild(tdName);
        tr.appendChild(tdPerms);
        tr.appendChild(tdActs);
        fragment.appendChild(tr);

        // ── Expanded detail row
        if (isOpen) {
            const exTr = document.createElement('tr');
            exTr.className = 'expanded-row' + (isLast ? ' row-last' : '');


            const exTd = document.createElement('td');
            exTd.colSpan = 4;

            const content = document.createElement('div');
            content.className = 'expanded-content';

            const label = document.createElement('div');
            label.className = 'expanded-label';
            label.textContent = 'Permissions';
            content.appendChild(label);

            const tagsWrap = document.createElement('div');
            tagsWrap.className = 'perm-tags';

            if (perms.length === 0) {
                const noP = document.createElement('span');
                noP.className = 'no-perms';
                noP.textContent = '권한 없음';
                tagsWrap.appendChild(noP);
            } else {
                perms.forEach(function(p) {
                    const tag = document.createElement('span');
                    tag.className = 'perm-tag';
                    tag.innerHTML = renderBadge(p.resource) + ' ';
                    const txt = document.createTextNode(p.action);
                    tag.appendChild(txt);

                    const xBtn = document.createElement('button');
                    xBtn.className = 'revoke-x';
                    xBtn.title = '권한 해제';
                    xBtn.textContent = '✕';
                    xBtn.addEventListener('click', function() { doRevoke(rid, p.permission_id, role.role_name, p); });
                    tag.appendChild(xBtn);

                    tagsWrap.appendChild(tag);
                });
            }

            content.appendChild(tagsWrap);
            exTd.appendChild(content);
            exTr.appendChild(exTd);
            fragment.appendChild(exTr);
        }
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
    sizeWrap.innerHTML = 'Page size: ';
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

// ── Expand / collapse ─────────────────────────────────────────

function toggleExpand(roleId) {
    if (state.expanded.has(roleId)) {
        state.expanded.delete(roleId);
    } else {
        state.expanded.add(roleId);
    }
    renderTable();
}

// ── Load data ─────────────────────────────────────────────────

async function loadRoles() {
    const tbody = document.getElementById('rolesBody');
    tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오는 중...</td></tr>';
    try {
        const data = await fetchRoles();
        state.allRoles = Array.isArray(data) ? data : [];
        applySearch();
        renderTable();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오기 실패: ' + escText(e.message) + '</td></tr>';
    }
}

// ── Modal helpers ─────────────────────────────────────────────

function openModal(id) {
    document.getElementById(id).removeAttribute('hidden');
}

function closeModal(id) {
    document.getElementById(id).setAttribute('hidden', '');
}

// ── Add / Edit Role modal ─────────────────────────────────────

function openAddModal() {
    state.editingRole = null;
    document.getElementById('roleModalTitle').textContent = 'Add Role';
    document.getElementById('inputRoleName').value = '';
    document.getElementById('inputRoleDesc').value = '';
    document.getElementById('roleModalErr').textContent = '';
    document.getElementById('btnSaveRole').disabled = false;
    openModal('roleModal');
    document.getElementById('inputRoleName').focus();
}

function openEditModal(role) {
    state.editingRole = role;
    document.getElementById('roleModalTitle').textContent = 'Edit Role';
    document.getElementById('inputRoleName').value = role.role_name;
    document.getElementById('inputRoleDesc').value = role.description || '';
    document.getElementById('roleModalErr').textContent = '';
    document.getElementById('btnSaveRole').disabled = false;
    openModal('roleModal');
    document.getElementById('inputRoleName').focus();
}

async function saveRole() {
    const name = document.getElementById('inputRoleName').value.trim();
    const desc = document.getElementById('inputRoleDesc').value.trim();
    const errEl = document.getElementById('roleModalErr');
    const btn   = document.getElementById('btnSaveRole');

    errEl.textContent = '';
    if (!name) { errEl.textContent = 'Role Name은 필수입니다.'; return; }

    btn.disabled = true;
    try {
        if (state.editingRole) {
            await updateRole(state.editingRole.role_id, name, desc);
        } else {
            await createRole(name, desc);
        }
        closeModal('roleModal');
        await loadRoles();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Assign Permissions modal ──────────────────────────────────

async function openAssignModal(role) {
    state.assignRoleId = role.role_id;
    document.getElementById('assignModalTitle').textContent = 'Assign Permissions — ' + role.role_name;
    document.getElementById('assignModalErr').textContent = '';
    document.getElementById('permResourceFilter').value = '';
    document.getElementById('btnAssignConfirm').disabled = false;
    openModal('assignModal');
    await loadPermGrid(role);
}

async function loadPermGrid(role) {
    const grid   = document.getElementById('permGrid');
    const filter = document.getElementById('permResourceFilter').value;
    grid.textContent = '불러오는 중...';

    try {
        const allPerms = await fetchPermissions(filter || null);
        state.allPerms = Array.isArray(allPerms) ? allPerms : [];

        const assigned = new Set((role.permissions || []).map(function(p) { return p.permission_id; }));

        if (state.allPerms.length === 0) {
            grid.textContent = '등록된 권한이 없습니다.';
            return;
        }

        grid.innerHTML = '';
        state.allPerms.forEach(function(p) {
            const item = document.createElement('label');
            item.className = 'perm-item';

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = p.permission_id;
            cb.checked = assigned.has(p.permission_id);
            if (assigned.has(p.permission_id)) cb.dataset.alreadyAssigned = '1';

            const info = document.createElement('div');
            info.className = 'perm-item-info';

            const strong = document.createElement('strong');
            strong.textContent = p.action;
            const span = document.createElement('span');
            span.textContent = p.resource;

            const badge = document.createElement('span');
            badge.className = 'badge badge-' + p.resource;
            badge.textContent = p.resource;

            info.appendChild(badge);
            info.appendChild(document.createTextNode(' '));
            info.appendChild(strong);
            info.appendChild(span);
            item.appendChild(cb);
            item.appendChild(info);
            grid.appendChild(item);
        });
    } catch (e) {
        grid.textContent = '불러오기 실패: ' + e.message;
    }
}

async function confirmAssign() {
    const errEl = document.getElementById('assignModalErr');
    const btn   = document.getElementById('btnAssignConfirm');
    errEl.textContent = '';

    const checkboxes = document.querySelectorAll('#permGrid input[type=checkbox]');
    const toAssign   = [];
    checkboxes.forEach(function(cb) {
        if (cb.checked && !cb.dataset.alreadyAssigned) {
            toAssign.push(cb.value);
        }
    });

    if (toAssign.length === 0) {
        closeModal('assignModal');
        return;
    }

    btn.disabled = true;
    try {
        await assignPermissions(state.assignRoleId, toAssign);
        closeModal('assignModal');
        await loadRoles();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Revoke (from expanded row) ────────────────────────────────

async function doRevoke(roleId, permId, roleName, perm) {
    const label = perm.resource + ':' + perm.action;
    if (!confirm('"' + roleName + '" 에서 [' + label + '] 권한을 해제하시겠습니까?')) return;
    try {
        await revokePermission(roleId, permId);
        await loadRoles();
    } catch (e) {
        alert('해제 실패: ' + e.message);
    }
}

// ── Delete modal ──────────────────────────────────────────────

function openDeleteModal(role) {
    state.deleteRoleId = role.role_id;
    const msg = document.getElementById('deleteModalMsg');
    msg.textContent = '';
    const strong = document.createElement('strong');
    strong.textContent = role.role_name;
    msg.appendChild(document.createTextNode('역할 '));
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'));
    document.getElementById('deleteModalErr').textContent = '';
    document.getElementById('btnConfirmDelete').disabled = false;
    openModal('deleteModal');
}

async function confirmDelete() {
    const errEl = document.getElementById('deleteModalErr');
    const btn   = document.getElementById('btnConfirmDelete');
    errEl.textContent = '';
    btn.disabled = true;
    try {
        await deleteRole(state.deleteRoleId);
        closeModal('deleteModal');
        state.expanded.delete(state.deleteRoleId);

        await loadRoles();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Wire up events ────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    // Toolbar
    document.getElementById('btnAddRole').addEventListener('click', openAddModal);
    document.getElementById('btnRefresh').addEventListener('click', loadRoles);
    document.getElementById('searchInput').addEventListener('input', function() {
        applySearch();
        renderTable();
    });

    // Role modal
    document.getElementById('btnSaveRole').addEventListener('click', saveRole);
    document.getElementById('inputRoleName').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') saveRole();
    });

    // Assign modal
    document.getElementById('btnAssignConfirm').addEventListener('click', confirmAssign);
    document.getElementById('permResourceFilter').addEventListener('change', function() {
        // re-load grid with current role
        const role = state.allRoles.find(function(r) { return r.role_id === state.assignRoleId; });
        if (role) loadPermGrid(role);
    });

    // Delete modal
    document.getElementById('btnConfirmDelete').addEventListener('click', confirmDelete);

    // Close buttons (data-close attribute)
    document.querySelectorAll('[data-close]').forEach(function(btn) {
        btn.addEventListener('click', function() { closeModal(btn.dataset.close); });
    });

    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                overlay.setAttribute('hidden', '');
            }
        });
    });

    // Escape key closes any open modal
    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-overlay:not([hidden])').forEach(function(el) {
            el.setAttribute('hidden', '');
        });
    });

    // Initial load
    loadRoles();
});
