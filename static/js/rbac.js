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
    const res = await fetch(url, Object.assign({}, options, { headers: headers }));

    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (!refreshed) { window.location.replace('/login'); return null; }
        const newToken = getToken();
        headers['Authorization'] = 'Bearer ' + newToken;
        return fetch(url, Object.assign({}, options, { headers: headers }));
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

var state = {
    allRoles:    [],
    filtered:    [],
    pageSize:    20,
    page:        1,
    expanded:    new Set(),
    allPerms:    [],
    allMembers:  [],           // GroupMemberDTO[] from /api/group/members
    allGroups:   [],           // GroupResponseDTO[] from /api/group
    bindingsByRole: {},        // role_id → { members:[], teams:[], departments:[] }
    editingRole:        null,
    assignRoleId:       null,
    bindingRoleId:      null,
    bindingSubjectType: 'MEMBER',
    bindingSelectedId:  null,
    deleteRoleId:       null,
};

// ── API calls ─────────────────────────────────────────────────

async function fetchRoles() {
    return apiJSON('/api/rbac/role', { method: 'GET' });
}

async function fetchAllBindings() {
    return apiJSON('/api/rbac/rolebinding', { method: 'GET' });
}

async function fetchAllMembers() {
    return apiJSON('/api/group/members', { method: 'GET' });
}

async function fetchAllGroups() {
    return apiJSON('/api/group', { method: 'GET' });
}

async function fetchPermissions(type_) {
    var qs = type_ ? '?type=' + encodeURIComponent(type_) : '';
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
    var qs = '?roleId='       + encodeURIComponent(roleId) +
             '&permissionId=' + encodeURIComponent(permissionId);
    return apiJSON('/api/rbac/permission/assign' + qs, { method: 'DELETE' });
}

async function createBinding(roleId, subjectType, subjectId, resourceType, resourceId) {
    return apiJSON('/api/rbac/rolebinding', {
        method: 'POST',
        body: JSON.stringify({
            roleId:       roleId,
            subjectType:  subjectType,
            subjectId:    subjectId,
            resourceType: resourceType,
            resourceId:   resourceId,
        }),
    });
}

async function revokeBinding(subjectType, subjectId, resourceType, resourceId) {
    var qs = '?subjectType='  + encodeURIComponent(subjectType)  +
             '&subjectId='    + encodeURIComponent(subjectId)    +
             '&resourceType=' + encodeURIComponent(resourceType) +
             '&resourceId='   + encodeURIComponent(resourceId);
    return apiJSON('/api/rbac/rolebinding' + qs, { method: 'DELETE' });
}

// ── Render helpers ────────────────────────────────────────────

function escText(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function renderBadge(resource) {
    var span = document.createElement('span');
    span.className = 'badge badge-' + resource;
    span.textContent = resource;
    return span.outerHTML;
}

function resolveSubjectName(binding) {
    if (binding.subject_type === 'MEMBER') {
        var m = state.allMembers.find(function(m) { return m.member_id === binding.subject_id; });
        return m ? m.name_ko + ' (' + m.account_id + ')' : binding.subject_id.slice(0, 8) + '…';
    }
    if (binding.subject_type === 'TEAM') {
        var g = state.allGroups.find(function(g) { return g.group_id === binding.subject_id; });
        return g ? g.group_name : binding.subject_id.slice(0, 8) + '…';
    }
    // DEPARTMENT
    return binding.subject_id;
}

function resourceShort(binding) {
    return binding.resource_type + ':' + binding.resource_id.slice(0, 8) + '…';
}

// ── Table rendering ───────────────────────────────────────────

function applySearch() {
    var q = document.getElementById('searchInput').value.trim().toLowerCase();
    state.filtered = q
        ? state.allRoles.filter(function(r) {
            return r.role_name.toLowerCase().includes(q) ||
                   (r.description || '').toLowerCase().includes(q);
          })
        : state.allRoles.slice();
    state.page = 1;
}

function currentPage() {
    var start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

function renderTable() {
    var tbody = document.getElementById('rolesBody');
    var rows  = currentPage();
    var total = state.filtered.length;

    var countEl = document.getElementById('itemsCount');
    countEl.textContent = total + ' role' + (total !== 1 ? 's' : '');

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="state-cell">역할이 없습니다.</td></tr>';
        renderPagination();
        return;
    }

    var fragment = document.createDocumentFragment();

    rows.forEach(function(role, idx) {
        var isLast = idx === rows.length - 1;
        var rid    = role.role_id;
        var isOpen = state.expanded.has(rid);
        var perms  = role.permissions || [];

        // ── Main row
        var tr = document.createElement('tr');
        tr.className = 'role-row' + (isLast && !isOpen ? ' row-last' : '');
        tr.dataset.id = rid;

        var tdToggle = document.createElement('td');
        var toggleBtn = document.createElement('button');
        toggleBtn.className = 'toggle-btn' + (isOpen ? ' open' : '');
        toggleBtn.title = isOpen ? '접기' : '펼치기';
        toggleBtn.textContent = '▶';
        toggleBtn.addEventListener('click', function() { toggleExpand(rid); });
        tdToggle.appendChild(toggleBtn);

        var tdName = document.createElement('td');
        var nameDiv = document.createElement('div');
        nameDiv.className = 'role-name';
        nameDiv.textContent = role.role_name;
        tdName.appendChild(nameDiv);
        if (role.description) {
            var descDiv = document.createElement('div');
            descDiv.className = 'role-desc';
            descDiv.textContent = role.description;
            tdName.appendChild(descDiv);
        }

        var tdPerms = document.createElement('td');
        var pill = document.createElement('span');
        pill.className = 'perm-pill';
        pill.textContent = perms.length;
        tdPerms.appendChild(pill);

        var tdActs = document.createElement('td');
        var actWrap = document.createElement('div');
        actWrap.className = 'row-actions';

        var btnAssign = document.createElement('button');
        btnAssign.className = 'act-btn';
        btnAssign.textContent = 'Assign Perms';
        btnAssign.addEventListener('click', function() { openAssignModal(role); });

        var btnEdit = document.createElement('button');
        btnEdit.className = 'act-btn';
        btnEdit.textContent = 'Edit';
        btnEdit.addEventListener('click', function() { openEditModal(role); });

        var btnDel = document.createElement('button');
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
            var exTr = document.createElement('tr');
            exTr.className = 'expanded-row' + (isLast ? ' row-last' : '');

            var exTd = document.createElement('td');
            exTd.colSpan = 4;

            var content = document.createElement('div');
            content.className = 'expanded-content';

            // ── Permissions section
            var permLabel = document.createElement('div');
            permLabel.className = 'expanded-label';
            permLabel.textContent = 'Permissions';
            content.appendChild(permLabel);

            var tagsWrap = document.createElement('div');
            tagsWrap.className = 'perm-tags';

            if (perms.length === 0) {
                var noP = document.createElement('span');
                noP.className = 'no-perms';
                noP.textContent = '권한 없음';
                tagsWrap.appendChild(noP);
            } else {
                perms.forEach(function(p) {
                    var tag = document.createElement('span');
                    tag.className = 'perm-tag';
                    tag.innerHTML = renderBadge(p.type) + ' ';
                    tag.appendChild(document.createTextNode(p.action));
                    var xBtn = document.createElement('button');
                    xBtn.className = 'revoke-x';
                    xBtn.title = '권한 해제';
                    xBtn.textContent = '✕';
                    xBtn.addEventListener('click', function() { doRevoke(rid, p.permission_id, role.role_name, p); });
                    tag.appendChild(xBtn);
                    tagsWrap.appendChild(tag);
                });
            }
            content.appendChild(tagsWrap);

            // ── Binding sections (MEMBER / TEAM / DEPARTMENT)
            var bindings = state.bindingsByRole[rid] || { members: [], teams: [], departments: [] };

            function makeBindingSection(labelText, list) {
                if (list.length === 0) return null;
                var section = document.createElement('div');
                section.className = 'binding-section';
                var sLabel = document.createElement('div');
                sLabel.className = 'binding-section-label';
                sLabel.textContent = labelText;
                section.appendChild(sLabel);
                var tags = document.createElement('div');
                tags.className = 'binding-tags';
                list.forEach(function(b) {
                    var tag = document.createElement('span');
                    tag.className = 'binding-tag';

                    var subjectSpan = document.createElement('span');
                    subjectSpan.className = 'binding-subject';
                    subjectSpan.textContent = resolveSubjectName(b);

                    var arrow = document.createTextNode(' → ');

                    var resSpan = document.createElement('span');
                    resSpan.className = 'binding-resource';
                    resSpan.textContent = resourceShort(b);

                    var xBtn = document.createElement('button');
                    xBtn.className = 'revoke-x';
                    xBtn.title = '바인딩 해제';
                    xBtn.textContent = '✕';
                    xBtn.addEventListener('click', function() { doRevokeBinding(b, role.role_name); });

                    tag.appendChild(subjectSpan);
                    tag.appendChild(arrow);
                    tag.appendChild(resSpan);
                    tag.appendChild(xBtn);
                    tags.appendChild(tag);
                });
                section.appendChild(tags);
                return section;
            }

            var memberSec = makeBindingSection('Member Bindings', bindings.members);
            var teamSec   = makeBindingSection('Group Bindings',  bindings.teams);
            var deptSec   = makeBindingSection('Dept Bindings',   bindings.departments);
            if (memberSec) content.appendChild(memberSec);
            if (teamSec)   content.appendChild(teamSec);
            if (deptSec)   content.appendChild(deptSec);

            // ── Add Binding button
            var addBindBtn = document.createElement('button');
            addBindBtn.className = 'btn-add-binding';
            addBindBtn.textContent = '＋ Add Binding';
            addBindBtn.addEventListener('click', function() { openBindingModal(role); });
            content.appendChild(addBindBtn);

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
    var bar   = document.getElementById('paginationBar');
    var total = state.filtered.length;
    var pages = Math.max(1, Math.ceil(total / state.pageSize));

    if (total === 0) { bar.innerHTML = ''; return; }

    var start = (state.page - 1) * state.pageSize + 1;
    var end   = Math.min(state.page * state.pageSize, total);

    bar.innerHTML = '';

    var sizeWrap = document.createElement('div');
    sizeWrap.className = 'page-size-wrap';
    sizeWrap.innerHTML = 'Page size: ';
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
    var tbody = document.getElementById('rolesBody');
    tbody.innerHTML = '<tr><td colspan="4" class="state-cell">불러오는 중...</td></tr>';
    try {
        var results = await Promise.all([
            fetchRoles(),
            fetchAllBindings().catch(function() { return []; }),
            fetchAllMembers().catch(function() { return []; }),
            fetchAllGroups().catch(function() { return []; }),
        ]);
        var rolesData    = results[0];
        var bindingsData = results[1];
        var membersData  = results[2];
        var groupsData   = results[3];

        state.allRoles   = Array.isArray(rolesData)   ? rolesData   : [];
        state.allMembers = Array.isArray(membersData)  ? membersData : [];
        state.allGroups  = Array.isArray(groupsData)   ? groupsData  : [];

        // Group bindings by role_id
        state.bindingsByRole = {};
        (Array.isArray(bindingsData) ? bindingsData : []).forEach(function(b) {
            if (!state.bindingsByRole[b.role_id]) {
                state.bindingsByRole[b.role_id] = { members: [], teams: [], departments: [] };
            }
            if (b.subject_type === 'MEMBER') {
                state.bindingsByRole[b.role_id].members.push(b);
            } else if (b.subject_type === 'TEAM') {
                state.bindingsByRole[b.role_id].teams.push(b);
            } else {
                state.bindingsByRole[b.role_id].departments.push(b);
            }
        });

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
    var name  = document.getElementById('inputRoleName').value.trim();
    var desc  = document.getElementById('inputRoleDesc').value.trim();
    var errEl = document.getElementById('roleModalErr');
    var btn   = document.getElementById('btnSaveRole');

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
    document.getElementById('permTypeFilter').value = '';
    document.getElementById('btnAssignConfirm').disabled = false;
    openModal('assignModal');
    await loadPermGrid(role);
}

async function loadPermGrid(role) {
    var grid   = document.getElementById('permGrid');
    var filter = document.getElementById('permTypeFilter').value;
    grid.textContent = '불러오는 중...';

    try {
        var allPerms = await fetchPermissions(filter || null);
        state.allPerms = Array.isArray(allPerms) ? allPerms : [];

        var assigned = new Set((role.permissions || []).map(function(p) { return p.permission_id; }));

        if (state.allPerms.length === 0) {
            grid.textContent = '등록된 권한이 없습니다.';
            return;
        }

        grid.innerHTML = '';
        state.allPerms.forEach(function(p) {
            var item = document.createElement('label');
            item.className = 'perm-item';

            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.value = p.permission_id;
            cb.checked = assigned.has(p.permission_id);
            if (assigned.has(p.permission_id)) cb.dataset.alreadyAssigned = '1';

            var info = document.createElement('div');
            info.className = 'perm-item-info';

            var strong = document.createElement('strong');
            strong.textContent = p.action;

            var badge = document.createElement('span');
            badge.className = 'badge badge-' + p.type;
            badge.textContent = p.type;

            info.appendChild(badge);
            info.appendChild(document.createTextNode(' '));
            info.appendChild(strong);
            item.appendChild(cb);
            item.appendChild(info);
            grid.appendChild(item);
        });
    } catch (e) {
        grid.textContent = '불러오기 실패: ' + e.message;
    }
}

async function confirmAssign() {
    var errEl = document.getElementById('assignModalErr');
    var btn   = document.getElementById('btnAssignConfirm');
    errEl.textContent = '';

    var checkboxes = document.querySelectorAll('#permGrid input[type=checkbox]');
    var toAssign   = [];
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

// ── Revoke permission (expanded row) ─────────────────────────

async function doRevoke(roleId, permId, roleName, perm) {
    var label = perm.resource + ':' + perm.action;
    if (!confirm('"' + roleName + '" 에서 [' + label + '] 권한을 해제하시겠습니까?')) return;
    try {
        await revokePermission(roleId, permId);
        await loadRoles();
    } catch (e) {
        alert('해제 실패: ' + e.message);
    }
}

// ── Binding modal ─────────────────────────────────────────────

function openBindingModal(role) {
    state.bindingRoleId      = role.role_id;
    state.bindingSubjectType = 'MEMBER';
    state.bindingSelectedId  = null;

    document.getElementById('bindingModalTitle').textContent = 'Add Binding — ' + role.role_name;
    document.getElementById('bindingModalErr').textContent = '';
    document.getElementById('bindResourceType').value = '';
    document.getElementById('bindResourceId').value   = '';
    document.getElementById('bindDeptId').value       = '';
    document.getElementById('bindMemberSearch').value = '';
    document.getElementById('bindGroupSearch').value  = '';
    document.getElementById('btnSaveBinding').disabled = false;

    // Reset tabs to MEMBER
    document.querySelectorAll('#subjectTypeTabs .tab-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.type === 'MEMBER');
    });
    showSubjectSection('MEMBER');
    renderBindingMemberList();
    openModal('bindingModal');
}

function showSubjectSection(type) {
    document.getElementById('memberPickSection').hidden = (type !== 'MEMBER');
    document.getElementById('groupPickSection').hidden  = (type !== 'TEAM');
    document.getElementById('deptPickSection').hidden   = (type !== 'DEPARTMENT');
}

function renderBindingMemberList() {
    var list   = document.getElementById('bindMemberList');
    var search = document.getElementById('bindMemberSearch').value.trim().toLowerCase();
    var items  = state.allMembers.filter(function(m) {
        if (!search) return true;
        return (m.name_ko    || '').toLowerCase().includes(search) ||
               (m.account_id || '').toLowerCase().includes(search);
    });

    list.innerHTML = '';
    if (items.length === 0) {
        list.innerHTML = '<div class="subject-empty">검색 결과가 없습니다.</div>';
        return;
    }
    items.forEach(function(m) {
        var item = document.createElement('label');
        item.className = 'subject-item' + (state.bindingSelectedId === m.member_id ? ' selected' : '');

        var radio = document.createElement('input');
        radio.type  = 'radio';
        radio.name  = 'bindSubject';
        radio.value = m.member_id;
        radio.checked = (state.bindingSelectedId === m.member_id);
        radio.addEventListener('change', function() {
            state.bindingSelectedId = m.member_id;
            list.querySelectorAll('.subject-item').forEach(function(el) { el.classList.remove('selected'); });
            item.classList.add('selected');
        });

        var info = document.createElement('div');
        var nameDiv = document.createElement('div');
        nameDiv.className = 'subject-item-main';
        nameDiv.textContent = m.name_ko;
        var subDiv = document.createElement('div');
        subDiv.className = 'subject-item-sub';
        subDiv.textContent = m.account_id;
        if (m.department_id) subDiv.textContent += ' · dept:' + m.department_id.slice(0, 8);
        info.appendChild(nameDiv);
        info.appendChild(subDiv);

        item.appendChild(radio);
        item.appendChild(info);
        list.appendChild(item);
    });
}

function renderBindingGroupList() {
    var list   = document.getElementById('bindGroupList');
    var search = document.getElementById('bindGroupSearch').value.trim().toLowerCase();
    var items  = state.allGroups.filter(function(g) {
        if (!search) return true;
        return (g.group_name  || '').toLowerCase().includes(search) ||
               (g.description || '').toLowerCase().includes(search);
    });

    list.innerHTML = '';
    if (items.length === 0) {
        list.innerHTML = '<div class="subject-empty">그룹이 없습니다.</div>';
        return;
    }
    items.forEach(function(g) {
        var item = document.createElement('label');
        item.className = 'subject-item' + (state.bindingSelectedId === g.group_id ? ' selected' : '');

        var radio = document.createElement('input');
        radio.type  = 'radio';
        radio.name  = 'bindSubject';
        radio.value = g.group_id;
        radio.checked = (state.bindingSelectedId === g.group_id);
        radio.addEventListener('change', function() {
            state.bindingSelectedId = g.group_id;
            list.querySelectorAll('.subject-item').forEach(function(el) { el.classList.remove('selected'); });
            item.classList.add('selected');
        });

        var info = document.createElement('div');
        var nameDiv = document.createElement('div');
        nameDiv.className = 'subject-item-main';
        nameDiv.textContent = g.group_name;
        var subDiv = document.createElement('div');
        subDiv.className = 'subject-item-sub';
        var memberCount = (g.members || []).length;
        subDiv.textContent = (g.description || '') + (g.description ? ' · ' : '') + memberCount + '명';
        info.appendChild(nameDiv);
        info.appendChild(subDiv);

        item.appendChild(radio);
        item.appendChild(info);
        list.appendChild(item);
    });
}

async function saveBinding() {
    var errEl = document.getElementById('bindingModalErr');
    var btn   = document.getElementById('btnSaveBinding');
    errEl.textContent = '';

    var resourceType = document.getElementById('bindResourceType').value;
    var resourceId   = document.getElementById('bindResourceId').value.trim();

    var subjectId = state.bindingSelectedId;
    if (state.bindingSubjectType === 'DEPARTMENT') {
        subjectId = document.getElementById('bindDeptId').value.trim();
    }

    if (!subjectId)    { errEl.textContent = 'Subject를 선택하세요.'; return; }
    if (!resourceType) { errEl.textContent = 'Resource Type을 선택하세요.'; return; }
    if (!resourceId)   { errEl.textContent = 'Resource ID를 입력하세요.'; return; }

    btn.disabled = true;
    try {
        await createBinding(state.bindingRoleId, state.bindingSubjectType, subjectId, resourceType, resourceId);
        closeModal('bindingModal');
        await loadRoles();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

async function doRevokeBinding(binding, roleName) {
    var label = resolveSubjectName(binding) + ' → ' + resourceShort(binding);
    if (!confirm('"' + roleName + '" 에서 [' + label + '] 바인딩을 해제하시겠습니까?')) return;
    try {
        await revokeBinding(binding.subject_type, binding.subject_id, binding.resource_type, binding.resource_id);
        await loadRoles();
    } catch (e) {
        alert('해제 실패: ' + e.message);
    }
}

// ── Delete modal ──────────────────────────────────────────────

function openDeleteModal(role) {
    state.deleteRoleId = role.role_id;
    var msg = document.getElementById('deleteModalMsg');
    msg.textContent = '';
    var strong = document.createElement('strong');
    strong.textContent = role.role_name;
    msg.appendChild(document.createTextNode('역할 '));
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'));
    document.getElementById('deleteModalErr').textContent = '';
    document.getElementById('btnConfirmDelete').disabled = false;
    openModal('deleteModal');
}

async function confirmDelete() {
    var errEl = document.getElementById('deleteModalErr');
    var btn   = document.getElementById('btnConfirmDelete');
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
    document.getElementById('permTypeFilter').addEventListener('change', function() {
        var role = state.allRoles.find(function(r) { return r.role_id === state.assignRoleId; });
        if (role) loadPermGrid(role);
    });

    // Binding modal — subject type tabs
    document.querySelectorAll('#subjectTypeTabs .tab-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            state.bindingSubjectType = btn.dataset.type;
            state.bindingSelectedId  = null;
            document.querySelectorAll('#subjectTypeTabs .tab-btn').forEach(function(b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            showSubjectSection(btn.dataset.type);
            if (btn.dataset.type === 'MEMBER')     renderBindingMemberList();
            else if (btn.dataset.type === 'TEAM')  renderBindingGroupList();
        });
    });
    document.getElementById('bindMemberSearch').addEventListener('input', renderBindingMemberList);
    document.getElementById('bindGroupSearch').addEventListener('input', renderBindingGroupList);
    document.getElementById('btnSaveBinding').addEventListener('click', saveBinding);

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

    // Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-overlay:not([hidden])').forEach(function(el) {
            el.setAttribute('hidden', '');
        });
    });

    loadRoles();
});
