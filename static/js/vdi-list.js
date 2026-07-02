/* vdi-list.js — VDI 목록 관리 UI */

// Docker 리포지토리 이름 규칙: 소문자 영숫자 + '.' '_' '-' 구분자만 허용
var SNAPSHOT_NAME_RE = /^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$/;

// ── Auth helpers ──────────────────────────────────────────────

function getToken() {
    return sessionStorage.getItem('access_token');
}

async function tryRefresh() {
    try {
        var res = await fetch('/api/auth/refresh', { method: 'GET', credentials: 'include' });
        if (!res.ok) return false;
        var json = await res.json();
        var t = json && json.result && json.result.access_token;
        if (!t) return false;
        sessionStorage.setItem('access_token', t);
        return true;
    } catch (_) { return false; }
}

async function apiFetch(url, options) {
    var token = getToken();
    if (!token) {
        var ok = await tryRefresh();
        if (!ok) { window.location.replace('/login'); return null; }
        token = getToken();
    }
    var headers = Object.assign(
        { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        (options && options.headers) || {}
    );
    var res = await fetch(url, Object.assign({}, options, { headers: headers }));
    if (res.status === 401) {
        var ok2 = await tryRefresh();
        if (!ok2) { window.location.replace('/login'); return null; }
        headers['Authorization'] = 'Bearer ' + getToken();
        res = await fetch(url, Object.assign({}, options, { headers: headers }));
    }
    return res;
}

async function apiJSON(url, options) {
    var res = await apiFetch(url, options);
    if (!res) return null;
    var json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error((json && json.message) || 'API 오류');
    }
    return json.result !== undefined ? json.result : json;
}

// ── 권한 체크 ─────────────────────────────────────────────────

function getJwtPayload() {
    var token = getToken();
    if (!token) return {};
    try {
        var part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(part)) || {};
    } catch (_) { return {}; }
}

function isAdmin() {
    var role = (getJwtPayload().role || '').toUpperCase();
    return role === 'ADMIN' || role === 'SUPERADMIN';
}

// ── Toast ─────────────────────────────────────────────────────

var _toastTimer;
function toast(msg, type) {
    var el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'vdi-toast show toast-' + (type || 'info');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function() { el.className = 'vdi-toast'; }, 3000);
}

// ── 상태 ──────────────────────────────────────────────────────

var state = {
    vdis:        [],
    filtered:    [],
    members:     {},   // member_id → { name, accountId }
    pageSize:    20,
    page:        1,
    snapVdiId:   null,
    deleteVdiId: null,
};

// ── 멤버 목록 로드 ─────────────────────────────────────────────

async function loadMembers() {
    try {
        var list = await apiJSON('/api/group/members', { method: 'GET' });
        state.members = {};
        (list || []).forEach(function(m) {
            state.members[m.member_id] = { name: m.name_ko || m.account_id, accountId: m.account_id };
        });
    } catch (_) {}
}

function memberLabel(memberId) {
    var m = state.members[memberId];
    if (!m) return memberId || '—';
    return m.name + (m.accountId ? ' (' + m.accountId + ')' : '');
}

// ── VDI 목록 로드 ─────────────────────────────────────────────

async function loadVdis() {
    var url = isAdmin() ? '/api/vdi/instances' : '/api/vdi/instances/me';
    try {
        var vdis = await apiJSON(url, { method: 'GET' });
        state.vdis = vdis || [];
        applyFilter();
    } catch (e) {
        document.getElementById('vdiBody').innerHTML =
            '<tr><td colspan="6" class="state-cell">' + esc(e.message) + '</td></tr>';
    }
}

// ── 필터 & 렌더 ───────────────────────────────────────────────

function applyFilter() {
    var search = document.getElementById('searchInput').value.toLowerCase();
    var status = document.getElementById('statusFilter').value;
    state.filtered = state.vdis.filter(function(v) {
        return (!search || v.containerName.toLowerCase().includes(search)) &&
               (!status || v.status === status);
    });
    state.page = 1;
    renderTable();
    renderPagination();
}

function renderTable() {
    var tbody = document.getElementById('vdiBody');
    var start = (state.page - 1) * state.pageSize;
    var page  = state.filtered.slice(start, start + state.pageSize);
    var admin = isAdmin();

    document.getElementById('itemsCount').textContent = state.filtered.length + ' VDIs';

    if (!page.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="state-cell">VDI가 없습니다.</td></tr>';
        return;
    }

    tbody.innerHTML = page.map(function(v, idx) {
        var isLast   = idx === page.length - 1;
        var sc       = v.status.toLowerCase();
        var running  = v.status === 'RUNNING';
        var stopped  = !running;
        var date     = v.createdAt ? v.createdAt.slice(0, 10) : '';
        var member   = memberLabel(v.assignedTo);

        return '<tr class="role-row' + (isLast ? ' row-last' : '') + '">' +
            '<td><span class="role-name">' + esc(v.containerName) + '</span></td>' +
            '<td><span class="role-desc" style="font-size:0.82rem;">' + esc(v.image) + '</span></td>' +
            '<td><span class="vdi-status ' + sc + '">' + esc(v.status) + '</span></td>' +
            '<td><div class="member-cell"><div class="member-name">' + esc(member) + '</div></div></td>' +
            '<td><span class="role-desc">' + esc(date) + '</span></td>' +
            '<td><div class="row-actions">' +
                (stopped ? '<button class="act-btn act-start" data-action="start" data-id="' + v.vdiId + '">▶ 시작</button>' : '') +
                (running ? '<button class="act-btn act-stop"  data-action="stop"  data-id="' + v.vdiId + '">■ 중지</button>' : '') +
                (running ? '<button class="act-btn act-terminal" data-action="terminal" data-id="' + v.vdiId + '">⌨ 터미널</button>' : '') +
                '<button class="act-btn act-snap" data-action="snap" data-id="' + v.vdiId + '"' + (!running ? ' disabled' : '') + '>📷 스냅샷</button>' +
                (admin ? '<button class="act-btn act-del" data-action="delete" data-id="' + v.vdiId + '">삭제</button>' : '') +
            '</div></td>' +
        '</tr>';
    }).join('');
}

function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderPagination() {
    var bar   = document.getElementById('paginationBar');
    var total = state.filtered.length;
    var pages = Math.ceil(total / state.pageSize) || 1;
    if (pages <= 1) { bar.innerHTML = ''; return; }

    bar.innerHTML =
        '<div class="page-nav-wrap">' +
        '<button id="btnPrev"' + (state.page <= 1 ? ' disabled' : '') + '>‹</button>' +
        '<span>' + state.page + ' / ' + pages + '</span>' +
        '<button id="btnNext"' + (state.page >= pages ? ' disabled' : '') + '>›</button>' +
        '</div>';

    document.getElementById('btnPrev').onclick = function() {
        state.page--; renderTable(); renderPagination();
    };
    document.getElementById('btnNext').onclick = function() {
        state.page++; renderTable(); renderPagination();
    };
}

// ── 테이블 이벤트 위임 ─────────────────────────────────────────

document.getElementById('vdiBody').addEventListener('click', async function(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    var action = btn.dataset.action;
    var vdiId  = btn.dataset.id;

    if (action === 'start' || action === 'stop') {
        await powerAction(vdiId, action);
    } else if (action === 'terminal') {
        window.location.href = '/vdi?id=' + encodeURIComponent(vdiId);
    } else if (action === 'snap') {
        state.snapVdiId = vdiId;
        document.getElementById('snapName').value = '';
        document.getElementById('snapErr').textContent = '';
        document.getElementById('snapModal').hidden = false;
        loadSnapshotList();
    } else if (action === 'delete') {
        state.deleteVdiId = vdiId;
        var vdi = state.vdis.find(function(v) { return v.vdiId === vdiId; });
        document.getElementById('deleteMsg').textContent =
            '"' + (vdi ? vdi.containerName : vdiId) + '" VDI를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.';
        document.getElementById('deleteErr').textContent = '';
        document.getElementById('deleteModal').hidden = false;
    }
});

// ── 전원 제어 ─────────────────────────────────────────────────

async function powerAction(vdiId, action) {
    try {
        var updated = await apiJSON('/api/vdi/instances/' + vdiId + '/' + action, { method: 'POST' });
        var idx = state.vdis.findIndex(function(v) { return v.vdiId === vdiId; });
        if (idx >= 0 && updated) state.vdis[idx] = updated;
        applyFilter();
        toast(action === 'start' ? 'VDI를 시작했습니다.' : 'VDI를 중지했습니다.', 'success');
    } catch (e) {
        toast(e.message, 'error');
    }
}

// ── VDI 생성 ──────────────────────────────────────────────────

function populateMemberSelect(sel) {
    sel.innerHTML = '<option value="">멤버 선택...</option>';
    Object.entries(state.members).forEach(function(entry) {
        var id = entry[0], m = entry[1];
        var opt = document.createElement('option');
        opt.value = id;
        opt.textContent = m.name + (m.accountId ? ' (' + m.accountId + ')' : '');
        sel.appendChild(opt);
    });
}

document.getElementById('btnCreate').addEventListener('click', async function() {
    document.getElementById('inputContainerName').value = '';
    document.getElementById('inputImage').value = '';
    document.getElementById('createErr').textContent = '';

    var sel = document.getElementById('inputAssignedTo');
    sel.innerHTML = '<option value="">멤버 로딩 중...</option>';
    document.getElementById('createModal').hidden = false;

    await loadMembers();
    populateMemberSelect(sel);
});

document.getElementById('btnSaveCreate').addEventListener('click', async function() {
    var name       = document.getElementById('inputContainerName').value.trim();
    var image      = document.getElementById('inputImage').value.trim();
    var assignedTo = document.getElementById('inputAssignedTo').value;
    var errEl      = document.getElementById('createErr');

    if (!name || !image || !assignedTo) {
        errEl.textContent = '모든 필드를 입력하세요.';
        return;
    }
    try {
        await apiJSON('/api/vdi/instances', {
            method: 'POST',
            body: JSON.stringify({ containerName: name, image: image, assignedTo: assignedTo }),
        });
        document.getElementById('createModal').hidden = true;
        toast('VDI가 생성되었습니다.', 'success');
        await loadVdis();
    } catch (e) {
        errEl.textContent = e.message;
    }
});

// ── 스냅샷 ────────────────────────────────────────────────────

function fmtSnapDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    return d.getFullYear() + '.' + (d.getMonth() + 1) + '.' + d.getDate() + ' ' +
        String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

async function loadSnapshotList() {
    var listEl = document.getElementById('snapList');
    listEl.innerHTML = '<div class="snap-empty">불러오는 중...</div>';
    try {
        var snaps = await apiJSON('/api/vdi/instances/' + state.snapVdiId + '/snapshots');
        if (!snaps || !snaps.length) {
            listEl.innerHTML = '<div class="snap-empty">스냅샷이 없습니다.</div>';
            return;
        }
        listEl.innerHTML = snaps.map(function(s) {
            return '<div class="snap-row" data-snapshot-id="' + s.snapshotId + '">' +
                '<div class="snap-info">' +
                    '<div class="snap-name">' + esc(s.snapshotName) + '</div>' +
                    '<div class="snap-date">' + esc(fmtSnapDate(s.createdAt)) + '</div>' +
                '</div>' +
                '<button class="act-btn" data-snap-action="create-vdi">새 VDI로 생성</button>' +
                '<button class="act-btn act-stop" data-snap-action="restore">복원</button>' +
                '<button class="act-btn act-del" data-snap-action="delete">삭제</button>' +
            '</div>';
        }).join('');
    } catch (e) {
        listEl.innerHTML = '<div class="snap-empty">스냅샷 목록을 불러오지 못했습니다.</div>';
    }
}

document.getElementById('btnSnapConfirm').addEventListener('click', async function() {
    var name  = document.getElementById('snapName').value.trim();
    var errEl = document.getElementById('snapErr');
    if (!name) { errEl.textContent = '스냅샷 이름을 입력하세요.'; return; }
    if (!SNAPSHOT_NAME_RE.test(name)) {
        errEl.textContent = "스냅샷 이름은 영문 소문자, 숫자, '.', '_', '-'만 사용할 수 있습니다.";
        return;
    }
    try {
        await apiJSON('/api/vdi/instances/' + state.snapVdiId + '/snapshots', {
            method: 'POST',
            body: JSON.stringify({ snapshotName: name }),
        });
        errEl.textContent = '';
        document.getElementById('snapName').value = '';
        toast('스냅샷이 생성되었습니다.', 'success');
        loadSnapshotList();
    } catch (e) {
        errEl.textContent = e.message;
    }
});

// ── 스냅샷 목록 행 액션 (새 VDI 생성 / 복원 / 삭제) ────────────────

document.getElementById('snapList').addEventListener('click', async function(e) {
    var btn = e.target.closest('[data-snap-action]');
    if (!btn) return;
    var row = btn.closest('.snap-row');
    var snapshotId = row.dataset.snapshotId;

    if (btn.dataset.snapAction === 'create-vdi') {
        document.getElementById('snapCreateVdiName').value = '';
        document.getElementById('snapCreateVdiErr').textContent = '';
        document.getElementById('snapCreateVdiModal').dataset.snapshotId = snapshotId;
        var sel = document.getElementById('snapCreateVdiAssignedTo');
        sel.innerHTML = '<option value="">멤버 로딩 중...</option>';
        document.getElementById('snapCreateVdiModal').hidden = false;
        await loadMembers();
        populateMemberSelect(sel);
    } else if (btn.dataset.snapAction === 'restore') {
        if (!confirm('이 VDI를 해당 스냅샷 시점으로 복원하시겠습니까?\n현재 컨테이너는 삭제되고 스냅샷 이미지로 다시 생성됩니다. 이 작업은 되돌릴 수 없습니다.')) return;
        try {
            await apiJSON('/api/vdi/instances/' + state.snapVdiId + '/restore', {
                method: 'POST',
                body: JSON.stringify({ snapshotId: snapshotId }),
            });
            toast('VDI가 복원되었습니다.', 'success');
            document.getElementById('snapModal').hidden = true;
            await loadVdis();
        } catch (e) {
            toast(e.message, 'error');
        }
    } else if (btn.dataset.snapAction === 'delete') {
        if (!confirm('이 스냅샷을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
        try {
            await apiJSON('/api/vdi/instances/' + state.snapVdiId + '/snapshots/' + snapshotId, { method: 'DELETE' });
            toast('스냅샷이 삭제되었습니다.', 'success');
            loadSnapshotList();
        } catch (e) {
            toast(e.message, 'error');
        }
    }
});

// ── 스냅샷으로 새 VDI 생성 모달 ────────────────────────────────

document.getElementById('btnSnapCreateVdiConfirm').addEventListener('click', async function() {
    var modal         = document.getElementById('snapCreateVdiModal');
    var snapshotId    = modal.dataset.snapshotId;
    var containerName = document.getElementById('snapCreateVdiName').value.trim();
    var assignedTo    = document.getElementById('snapCreateVdiAssignedTo').value;
    var errEl         = document.getElementById('snapCreateVdiErr');

    if (!containerName || !assignedTo) {
        errEl.textContent = '모든 필드를 입력하세요.';
        return;
    }
    try {
        await apiJSON('/api/vdi/instances/from-snapshot', {
            method: 'POST',
            body: JSON.stringify({
                snapshotId: snapshotId,
                containerName: containerName,
                assignedTo: assignedTo,
            }),
        });
        modal.hidden = true;
        toast('스냅샷으로 새 VDI가 생성되었습니다.', 'success');
        await loadVdis();
    } catch (e) {
        errEl.textContent = e.message;
    }
});

// ── VDI 삭제 ──────────────────────────────────────────────────

document.getElementById('btnDeleteConfirm').addEventListener('click', async function() {
    var errEl = document.getElementById('deleteErr');
    try {
        await apiJSON('/api/vdi/instances/' + state.deleteVdiId, { method: 'DELETE' });
        document.getElementById('deleteModal').hidden = true;
        toast('VDI가 삭제되었습니다.', 'success');
        await loadVdis();
    } catch (e) {
        errEl.textContent = e.message;
    }
});

// ── 새로고침 / 필터 ───────────────────────────────────────────

document.getElementById('btnRefresh').addEventListener('click', loadVdis);
document.getElementById('searchInput').addEventListener('input', applyFilter);
document.getElementById('statusFilter').addEventListener('change', applyFilter);

// ── 모달 닫기 ─────────────────────────────────────────────────

document.querySelectorAll('[data-close]').forEach(function(btn) {
    btn.addEventListener('click', function() {
        document.getElementById(btn.dataset.close).hidden = true;
    });
});

['createModal', 'snapModal', 'snapCreateVdiModal', 'deleteModal'].forEach(function(id) {
    document.getElementById(id).addEventListener('click', function(e) {
        if (e.target === e.currentTarget) e.currentTarget.hidden = true;
    });
});

// ── 초기화 ────────────────────────────────────────────────────

if (isAdmin()) {
    document.getElementById('btnCreate').style.display = '';
}

loadMembers().then(loadVdis);
