/* ──────────────────────────────────────────────────────────────
   group.js  —  Group management UI
   ────────────────────────────────────────────────────────────── */

// ── Auth helpers ─────────────────────────────────────────────

function getToken() { return sessionStorage.getItem('access_token'); }

async function apiFetch(url, options) {
    let token = getToken();
    if (!token) {
        const ok = await tryRefresh();
        if (!ok) { window.location.replace('/login'); return null; }
        token = getToken();
    }
    const headers = Object.assign(
        { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
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
        const t = json && json.result && json.result.access_token;
        if (!t) return false;
        sessionStorage.setItem('access_token', t);
        return true;
    } catch (_) { return false; }
}

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) throw new Error((json && json.message) || 'API error');
    return json.result !== undefined ? json.result : json;
}

// ── State ─────────────────────────────────────────────────────

const state = {
    allGroups:       [],
    filtered:        [],
    allMembers:      [],   // {member_id, account_id, name_ko, department_id}
    pageSize:        20,
    page:            1,
    expanded:        new Set(),
    editingGroup:    null, // null=new, object=edit
    managingGroup:   null, // group being edited in members modal
    originalChecked: new Set(),  // member_ids originally in group (for delta)
    deleteGroupId:   null,
};

// ── API ───────────────────────────────────────────────────────

function fetchGroups()     { return apiJSON('/api/group',          { method: 'GET' }); }
function fetchAllMembers() { return apiJSON('/api/group/members',   { method: 'GET' }); }

function createGroup(name, desc) {
    return apiJSON('/api/group', {
        method: 'POST',
        body: JSON.stringify({ groupName: name, description: desc || null, memberIds: [] }),
    });
}
function updateGroup(id, name, desc) {
    return apiJSON('/api/group/' + encodeURIComponent(id), {
        method: 'PUT',
        body: JSON.stringify({ groupName: name, description: desc || null }),
    });
}
function deleteGroup(id) {
    return apiJSON('/api/group/' + encodeURIComponent(id), { method: 'DELETE' });
}
function addMembers(groupId, memberIds) {
    return apiJSON('/api/group/' + encodeURIComponent(groupId) + '/member', {
        method: 'POST',
        body: JSON.stringify({ memberIds: memberIds }),
    });
}
function removeMembers(groupId, memberIds) {
    return apiJSON('/api/group/' + encodeURIComponent(groupId) + '/member', {
        method: 'DELETE',
        body: JSON.stringify({ memberIds: memberIds }),
    });
}
function addMembersByDept(groupId, deptId) {
    return apiJSON('/api/group/' + encodeURIComponent(groupId) +
                   '/member/department/' + encodeURIComponent(deptId), { method: 'POST' });
}

// ── Search / filter ───────────────────────────────────────────

function applySearch() {
    const q = document.getElementById('searchInput').value.trim().toLowerCase();
    state.filtered = q
        ? state.allGroups.filter(function(g) {
            return g.group_name.toLowerCase().includes(q) ||
                   (g.description || '').toLowerCase().includes(q);
          })
        : state.allGroups.slice();
    state.page = 1;
}

function currentPage() {
    const start = (state.page - 1) * state.pageSize;
    return state.filtered.slice(start, start + state.pageSize);
}

// ── Table ─────────────────────────────────────────────────────

function renderTable() {
    const tbody  = document.getElementById('groupBody');
    const rows   = currentPage();
    const total  = state.filtered.length;
    document.getElementById('itemsCount').textContent =
        total + ' group' + (total !== 1 ? 's' : '');

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="state-cell">그룹이 없습니다.</td></tr>';
        renderPagination();
        return;
    }

    const frag = document.createDocumentFragment();
    rows.forEach(function(group, idx) {
        const isLast  = idx === rows.length - 1;
        const gid     = group.group_id;
        const isOpen  = state.expanded.has(gid);
        const members = group.members || [];

        // ── Main row
        const tr = document.createElement('tr');
        tr.className = 'role-row' + (isLast && !isOpen ? ' row-last' : '');

        // toggle cell
        const tdToggle = document.createElement('td');
        const tBtn = document.createElement('button');
        tBtn.className = 'toggle-btn' + (isOpen ? ' open' : '');
        tBtn.textContent = '▶';
        tBtn.addEventListener('click', function() { toggleExpand(gid); });
        tdToggle.appendChild(tBtn);

        // name cell
        const tdName = document.createElement('td');
        const nDiv = document.createElement('div');
        nDiv.className = 'role-name';
        nDiv.textContent = group.group_name;
        tdName.appendChild(nDiv);

        // description cell
        const tdDesc = document.createElement('td');
        tdDesc.style.color = 'var(--muted)';
        tdDesc.style.fontSize = '0.85rem';
        tdDesc.textContent = group.description || '—';

        // member count cell
        const tdCount = document.createElement('td');
        const pill = document.createElement('span');
        pill.className = 'perm-pill';
        pill.textContent = members.length;
        tdCount.appendChild(pill);

        // actions cell
        const tdActs = document.createElement('td');
        const actWrap = document.createElement('div');
        actWrap.className = 'row-actions';

        const btnMembers = document.createElement('button');
        btnMembers.className = 'act-btn';
        btnMembers.textContent = 'Manage Members';
        btnMembers.addEventListener('click', function() { openMembersModal(group); });

        const btnEdit = document.createElement('button');
        btnEdit.className = 'act-btn';
        btnEdit.textContent = 'Edit';
        btnEdit.addEventListener('click', function() { openEditModal(group); });

        const btnDel = document.createElement('button');
        btnDel.className = 'act-btn act-del';
        btnDel.textContent = 'Delete';
        btnDel.addEventListener('click', function() { openDeleteModal(group); });

        actWrap.appendChild(btnMembers);
        actWrap.appendChild(btnEdit);
        actWrap.appendChild(btnDel);
        tdActs.appendChild(actWrap);

        tr.appendChild(tdToggle);
        tr.appendChild(tdName);
        tr.appendChild(tdDesc);
        tr.appendChild(tdCount);
        tr.appendChild(tdActs);
        frag.appendChild(tr);

        // ── Expanded row
        if (isOpen) {
            const exTr = document.createElement('tr');
            exTr.className = 'expanded-row' + (isLast ? ' row-last' : '');
            const exTd = document.createElement('td');
            exTd.colSpan = 5;
            const content = document.createElement('div');
            content.className = 'expanded-content';

            const label = document.createElement('div');
            label.className = 'expanded-label';
            label.textContent = 'Members';
            content.appendChild(label);

            const tagsWrap = document.createElement('div');
            tagsWrap.className = 'perm-tags';

            if (members.length === 0) {
                const noM = document.createElement('span');
                noM.className = 'no-perms';
                noM.textContent = '멤버 없음';
                tagsWrap.appendChild(noM);
            } else {
                members.forEach(function(m) {
                    const tag = document.createElement('span');
                    tag.className = 'member-tag';
                    const nameSpan = document.createElement('span');
                    nameSpan.className = 'member-name';
                    nameSpan.textContent = m.name_ko;
                    const acctSpan = document.createElement('span');
                    acctSpan.className = 'member-acct';
                    acctSpan.textContent = m.account_id;
                    const xBtn = document.createElement('button');
                    xBtn.className = 'revoke-x';
                    xBtn.title = '그룹에서 제거';
                    xBtn.textContent = '✕';
                    xBtn.addEventListener('click', function() {
                        doRemoveMember(gid, m.member_id, group.group_name, m.name_ko);
                    });
                    tag.appendChild(nameSpan);
                    tag.appendChild(acctSpan);
                    tag.appendChild(xBtn);
                    tagsWrap.appendChild(tag);
                });
            }

            content.appendChild(tagsWrap);
            exTd.appendChild(content);
            exTr.appendChild(exTd);
            frag.appendChild(exTr);
        }
    });

    tbody.innerHTML = '';
    tbody.appendChild(frag);
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
        opt.value = n; opt.textContent = n;
        if (n === state.pageSize) opt.selected = true;
        sel.appendChild(opt);
    });
    sel.addEventListener('change', function() { state.pageSize = parseInt(sel.value, 10); state.page = 1; renderTable(); });
    sizeWrap.appendChild(sel);

    const navWrap = document.createElement('div');
    navWrap.className = 'page-nav-wrap';
    const info = document.createElement('span');
    info.textContent = start + '–' + end + ' of ' + total;
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '‹'; prevBtn.disabled = state.page <= 1;
    prevBtn.addEventListener('click', function() { state.page--; renderTable(); });
    const pageInfo = document.createElement('span');
    pageInfo.textContent = state.page + ' / ' + pages;
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '›'; nextBtn.disabled = state.page >= pages;
    nextBtn.addEventListener('click', function() { state.page++; renderTable(); });

    navWrap.appendChild(info); navWrap.appendChild(prevBtn);
    navWrap.appendChild(pageInfo); navWrap.appendChild(nextBtn);
    bar.appendChild(sizeWrap); bar.appendChild(navWrap);
}

// ── Expand ────────────────────────────────────────────────────

function toggleExpand(gid) {
    if (state.expanded.has(gid)) state.expanded.delete(gid);
    else state.expanded.add(gid);
    renderTable();
}

// ── Load ──────────────────────────────────────────────────────

async function loadGroups() {
    const tbody = document.getElementById('groupBody');
    tbody.innerHTML = '<tr><td colspan="5" class="state-cell">불러오는 중...</td></tr>';
    try {
        const [groups, members] = await Promise.all([fetchGroups(), fetchAllMembers()]);
        state.allGroups  = Array.isArray(groups)  ? groups  : [];
        state.allMembers = Array.isArray(members) ? members : [];
        applySearch();
        renderTable();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" class="state-cell">불러오기 실패: ' + e.message + '</td></tr>';
    }
}

// ── Modal helpers ─────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).removeAttribute('hidden'); }
function closeModal(id) { document.getElementById(id).setAttribute('hidden', ''); }

// ── Add / Edit Group modal ────────────────────────────────────

function openAddModal() {
    state.editingGroup = null;
    document.getElementById('groupModalTitle').textContent = 'Add Group';
    document.getElementById('inputGroupName').value = '';
    document.getElementById('inputGroupDesc').value = '';
    document.getElementById('groupModalErr').textContent = '';
    document.getElementById('btnSaveGroup').disabled = false;
    openModal('groupModal');
    document.getElementById('inputGroupName').focus();
}

function openEditModal(group) {
    state.editingGroup = group;
    document.getElementById('groupModalTitle').textContent = 'Edit Group';
    document.getElementById('inputGroupName').value = group.group_name;
    document.getElementById('inputGroupDesc').value = group.description || '';
    document.getElementById('groupModalErr').textContent = '';
    document.getElementById('btnSaveGroup').disabled = false;
    openModal('groupModal');
    document.getElementById('inputGroupName').focus();
}

async function saveGroup() {
    const name  = document.getElementById('inputGroupName').value.trim();
    const desc  = document.getElementById('inputGroupDesc').value.trim();
    const errEl = document.getElementById('groupModalErr');
    const btn   = document.getElementById('btnSaveGroup');
    errEl.textContent = '';
    if (!name) { errEl.textContent = 'Group Name은 필수입니다.'; return; }
    btn.disabled = true;
    try {
        if (state.editingGroup) await updateGroup(state.editingGroup.group_id, name, desc);
        else                    await createGroup(name, desc);
        closeModal('groupModal');
        await loadGroups();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Manage Members modal ──────────────────────────────────────

function buildDeptOptions(members) {
    const seen = new Set();
    const opts = [];
    members.forEach(function(m) {
        if (!seen.has(m.department_id)) {
            seen.add(m.department_id);
            opts.push(m.department_id);
        }
    });
    return opts.sort();
}

function renderMemberPicker() {
    const picker    = document.getElementById('memberPicker');
    const deptVal   = document.getElementById('deptFilter').value;
    const q         = document.getElementById('memberSearch').value.trim().toLowerCase();
    const quickBtn  = document.getElementById('btnQuickAddDept');

    // Show/hide quick add dept button
    if (deptVal) {
        quickBtn.removeAttribute('hidden');
        quickBtn.textContent = '＋ 이 부서 전원 추가 (' + deptVal.slice(0, 8) + '…)';
    } else {
        quickBtn.setAttribute('hidden', '');
    }

    let visible = state.allMembers;
    if (deptVal) visible = visible.filter(function(m) { return m.department_id === deptVal; });
    if (q) visible = visible.filter(function(m) {
        return m.name_ko.toLowerCase().includes(q) ||
               m.account_id.toLowerCase().includes(q);
    });

    if (visible.length === 0) {
        picker.innerHTML = '<div class="picker-empty">검색 결과가 없습니다.</div>';
        return;
    }

    picker.innerHTML = '';
    visible.forEach(function(m) {
        const inGroup = state.originalChecked.has(m.member_id);
        const item = document.createElement('label');
        item.className = 'member-item' + (inGroup ? ' is-member' : '');
        item.dataset.memberId = m.member_id;

        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = m.member_id;
        cb.checked = inGroup;

        const info = document.createElement('div');
        info.className = 'member-item-info';
        const nameDiv = document.createElement('div');
        nameDiv.className = 'member-item-name';
        nameDiv.textContent = m.name_ko;
        const subDiv = document.createElement('div');
        subDiv.className = 'member-item-sub';
        subDiv.textContent = m.account_id;
        info.appendChild(nameDiv);
        info.appendChild(subDiv);

        const badge = document.createElement('span');
        badge.className = 'dept-badge';
        badge.textContent = m.department_id.slice(0, 8) + '…';
        badge.title = m.department_id;

        item.appendChild(cb);
        item.appendChild(info);
        item.appendChild(badge);
        picker.appendChild(item);
    });
}

async function openMembersModal(group) {
    state.managingGroup  = group;
    state.originalChecked = new Set((group.members || []).map(function(m) { return m.member_id; }));

    document.getElementById('membersModalTitle').textContent =
        'Manage Members — ' + group.group_name;
    document.getElementById('membersModalErr').textContent = '';
    document.getElementById('btnSaveMembers').disabled = false;
    document.getElementById('memberSearch').value = '';

    // Build dept filter dropdown
    const sel = document.getElementById('deptFilter');
    sel.innerHTML = '<option value="">All departments</option>';
    buildDeptOptions(state.allMembers).forEach(function(deptId) {
        const opt = document.createElement('option');
        opt.value = deptId;
        opt.textContent = deptId.slice(0, 8) + '…';
        opt.title = deptId;
        sel.appendChild(opt);
    });
    sel.value = '';
    document.getElementById('btnQuickAddDept').setAttribute('hidden', '');

    openModal('membersModal');
    renderMemberPicker();
}

async function saveMemberChanges() {
    const errEl = document.getElementById('membersModalErr');
    const btn   = document.getElementById('btnSaveMembers');
    errEl.textContent = '';

    // Collect current checked state from picker checkboxes
    const checkboxes = document.querySelectorAll('#memberPicker input[type=checkbox]');
    const nowChecked = new Set();
    checkboxes.forEach(function(cb) { if (cb.checked) nowChecked.add(cb.value); });

    // All rendered members (filtered view) — only delta within rendered items
    const renderedIds = new Set();
    checkboxes.forEach(function(cb) { renderedIds.add(cb.value); });

    const toAdd    = [];
    const toRemove = [];
    renderedIds.forEach(function(mid) {
        const wasIn = state.originalChecked.has(mid);
        const isIn  = nowChecked.has(mid);
        if (!wasIn && isIn)  toAdd.push(mid);
        if (wasIn  && !isIn) toRemove.push(mid);
    });

    if (toAdd.length === 0 && toRemove.length === 0) {
        closeModal('membersModal');
        return;
    }

    btn.disabled = true;
    const gid = state.managingGroup.group_id;
    try {
        if (toAdd.length    > 0) await addMembers(gid, toAdd);
        if (toRemove.length > 0) await removeMembers(gid, toRemove);
        closeModal('membersModal');
        await loadGroups();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

async function quickAddDept() {
    const deptId = document.getElementById('deptFilter').value;
    if (!deptId || !state.managingGroup) return;
    const errEl = document.getElementById('membersModalErr');
    errEl.textContent = '';
    try {
        const updated = await addMembersByDept(state.managingGroup.group_id, deptId);
        // Update originalChecked and refresh picker with new group state
        state.originalChecked = new Set((updated.members || []).map(function(m) { return m.member_id; }));
        // Also update allGroups so expanded row stays consistent
        const idx = state.allGroups.findIndex(function(g) { return g.group_id === updated.group_id; });
        if (idx >= 0) state.allGroups[idx] = updated;
        applySearch();
        renderMemberPicker();
    } catch (e) {
        errEl.textContent = e.message;
    }
}

// ── Quick remove from expanded row ────────────────────────────

async function doRemoveMember(groupId, memberId, groupName, memberName) {
    if (!confirm('"' + groupName + '" 에서 ' + memberName + ' 을(를) 제거하시겠습니까?')) return;
    try {
        await removeMembers(groupId, [memberId]);
        await loadGroups();
    } catch (e) {
        alert('제거 실패: ' + e.message);
    }
}

// ── Delete modal ──────────────────────────────────────────────

function openDeleteModal(group) {
    state.deleteGroupId = group.group_id;
    const msg = document.getElementById('deleteGroupMsg');
    msg.textContent = '';
    const strong = document.createElement('strong');
    strong.textContent = group.group_name;
    msg.appendChild(document.createTextNode('그룹 '));
    msg.appendChild(strong);
    msg.appendChild(document.createTextNode(' 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'));
    document.getElementById('deleteGroupErr').textContent = '';
    document.getElementById('btnConfirmDeleteGroup').disabled = false;
    openModal('deleteGroupModal');
}

async function confirmDeleteGroup() {
    const errEl = document.getElementById('deleteGroupErr');
    const btn   = document.getElementById('btnConfirmDeleteGroup');
    errEl.textContent = '';
    btn.disabled = true;
    try {
        await deleteGroup(state.deleteGroupId);
        state.expanded.delete(state.deleteGroupId);
        closeModal('deleteGroupModal');
        await loadGroups();
    } catch (e) {
        errEl.textContent = e.message;
        btn.disabled = false;
    }
}

// ── Wire events ───────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('btnAddGroup').addEventListener('click', openAddModal);
    document.getElementById('btnRefresh').addEventListener('click', loadGroups);
    document.getElementById('searchInput').addEventListener('input', function() {
        applySearch(); renderTable();
    });

    // Group modal
    document.getElementById('btnSaveGroup').addEventListener('click', saveGroup);
    document.getElementById('inputGroupName').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') saveGroup();
    });

    // Members modal
    document.getElementById('btnSaveMembers').addEventListener('click', saveMemberChanges);
    document.getElementById('deptFilter').addEventListener('change', renderMemberPicker);
    document.getElementById('memberSearch').addEventListener('input', renderMemberPicker);
    document.getElementById('btnQuickAddDept').addEventListener('click', quickAddDept);

    // Delete modal
    document.getElementById('btnConfirmDeleteGroup').addEventListener('click', confirmDeleteGroup);

    // data-close buttons
    document.querySelectorAll('[data-close]').forEach(function(btn) {
        btn.addEventListener('click', function() { closeModal(btn.dataset.close); });
    });

    // Overlay click to close
    document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) overlay.setAttribute('hidden', '');
        });
    });

    // Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-overlay:not([hidden])').forEach(function(el) {
            el.setAttribute('hidden', '');
        });
    });

    loadGroups();
});
