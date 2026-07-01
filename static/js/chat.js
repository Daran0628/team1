/* chat.js — 채팅방 목록 페이지 */

// ── Auth helpers ─────────────────────────────────────────────
function getToken() { return sessionStorage.getItem('access_token'); }

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
    if (res && res.status === 401) {
        const ok = await tryRefresh();
        if (!ok) { window.location.replace('/login'); return null; }
        headers['Authorization'] = 'Bearer ' + getToken();
        return fetch(url, Object.assign({}, options, { headers }));
    }
    return res;
}

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    return res ? res.json() : null;
}

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg, type) {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => {
        t.classList.add('toast-out');
        setTimeout(() => t.remove(), 300);
    }, 3000);
}

// ── State ─────────────────────────────────────────────────────
let allRooms = [];
let allMembers = [];
let selectedType = 'DIRECT';
let selectedMemberIds = new Set();

// ── Room list ─────────────────────────────────────────────────
async function loadRooms() {
    const data = await apiJSON('/api/chat/rooms');
    if (!data || !data.isSuccess) { showToast('채팅방 목록을 불러오지 못했습니다.', 'error'); return; }
    allRooms = data.result || [];
    renderRooms(allRooms);
}

function renderRooms(rooms) {
    const list = document.getElementById('roomList');
    document.getElementById('roomCount').textContent = rooms.length + '개의 채팅방';

    if (!rooms.length) {
        list.innerHTML = '<div class="state-cell">채팅방이 없습니다. 새 채팅을 시작해보세요.</div>';
        return;
    }

    list.innerHTML = rooms.map(r => {
        const initials = (r.room_name || r.members.map(m => m.name_ko).join(', ')).slice(0, 1);
        const name = r.room_type === 'DIRECT'
            ? (r.members.find(m => m.account_id !== getMyAccountId()) || r.members[0] || {name_ko: '?'}).name_ko
            : (r.room_name || '그룹 채팅');
        const time = r.created_at ? fmtTime(r.created_at) : '';
        return '<a class="room-card" href="/chat/' + r.room_id + '">' +
            '<div class="room-card-icon">' + initials + '</div>' +
            '<div class="room-card-body">' +
                '<div class="room-card-name">' + esc(name) + '</div>' +
                '<div class="room-card-preview">' + esc(r.members.map(m => m.name_ko).join(', ')) + '</div>' +
            '</div>' +
            '<div class="room-card-right">' +
                '<span class="room-card-time">' + time + '</span>' +
                (r.unread_count > 0 ? '<span class="unread-badge">' + (r.unread_count > 99 ? '99+' : r.unread_count) + '</span>' : '') +
            '</div>' +
        '</a>';
    }).join('');
}

function getMyAccountId() {
    try {
        const token = getToken();
        if (!token) return '';
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.sub || '';
    } catch (_) { return ''; }
}

function fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    if (d.toDateString() === now.toDateString()) {
        return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
    }
    return (d.getMonth()+1) + '/' + d.getDate();
}

function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Search ────────────────────────────────────────────────────
document.getElementById('searchInput').addEventListener('input', function() {
    const q = this.value.trim().toLowerCase();
    renderRooms(allRooms.filter(r => {
        const name = r.room_name || r.members.map(m => m.name_ko).join(' ');
        return name.toLowerCase().includes(q);
    }));
});

document.getElementById('btnRefresh').addEventListener('click', loadRooms);

// ── Modal helpers ─────────────────────────────────────────────
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById(btn.dataset.close).hidden = true;
    });
});
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.hidden = true;
    });
});

// ── Create room modal ─────────────────────────────────────────
document.getElementById('btnNewRoom').addEventListener('click', openCreateModal);

async function openCreateModal() {
    selectedMemberIds.clear();
    selectedType = 'DIRECT';
    document.getElementById('createErr').textContent = '';
    document.getElementById('inputRoomName') && (document.getElementById('inputRoomName').value = '');
    document.getElementById('groupNameField').hidden = true;
    document.querySelectorAll('.create-room-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.type === 'DIRECT');
    });
    document.getElementById('createModal').hidden = false;

    if (!allMembers.length) {
        const data = await apiJSON('/api/chat/members');
        allMembers = (data && data.result) || [];
    }
    renderMemberPick('');
}

function renderMemberPick(query) {
    const list = document.getElementById('memberPickList');
    const myAccountId = getMyAccountId();
    const filtered = allMembers.filter(m =>
        m.account_id !== myAccountId &&
        (!query || m.name_ko.toLowerCase().includes(query) || m.account_id.toLowerCase().includes(query))
    );

    if (!filtered.length) {
        list.innerHTML = '<div style="text-align:center;padding:1rem;color:var(--muted);font-size:.85rem">멤버가 없습니다.</div>';
        return;
    }

    const isGroup = selectedType === 'GROUP';
    list.innerHTML = filtered.map(m => {
        const sel = selectedMemberIds.has(m.member_id);
        return '<label class="member-pick-item' + (sel ? ' selected' : '') + '">' +
            '<input type="' + (isGroup ? 'checkbox' : 'radio') + '" name="pickedMember" value="' + m.member_id + '"' + (sel ? ' checked' : '') + '>' +
            '<div><div class="member-pick-name">' + esc(m.name_ko) + '</div>' +
            '<div class="member-pick-sub">' + esc(m.account_id) + '</div></div>' +
        '</label>';
    }).join('');

    list.querySelectorAll('input').forEach(inp => {
        inp.addEventListener('change', () => {
            if (!inp.checked) { selectedMemberIds.delete(inp.value); return; }
            if (selectedType === 'DIRECT') selectedMemberIds.clear();
            selectedMemberIds.add(inp.value);
            renderMemberPick(document.getElementById('memberSearch').value.trim().toLowerCase());
        });
    });
}

document.querySelectorAll('.create-room-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        selectedType = tab.dataset.type;
        selectedMemberIds.clear();
        document.querySelectorAll('.create-room-tab').forEach(t => t.classList.toggle('active', t === tab));
        document.getElementById('groupNameField').hidden = selectedType !== 'GROUP';
        renderMemberPick(document.getElementById('memberSearch').value.trim().toLowerCase());
    });
});

document.getElementById('memberSearch').addEventListener('input', function() {
    renderMemberPick(this.value.trim().toLowerCase());
});

document.getElementById('btnCreateRoom').addEventListener('click', async () => {
    const err = document.getElementById('createErr');
    err.textContent = '';

    const memberIds = [...selectedMemberIds];
    if (!memberIds.length) { err.textContent = '멤버를 선택해주세요.'; return; }
    if (selectedType === 'DIRECT' && memberIds.length !== 1) { err.textContent = '1:1 채팅은 1명만 선택하세요.'; return; }

    const body = { roomType: selectedType, memberIds };
    if (selectedType === 'GROUP') {
        const name = document.getElementById('inputRoomName').value.trim();
        if (!name) { err.textContent = '채팅방 이름을 입력해주세요.'; return; }
        body.roomName = name;
    }

    const btn = document.getElementById('btnCreateRoom');
    btn.disabled = true;
    const data = await apiJSON('/api/chat/rooms', { method: 'POST', body: JSON.stringify(body) });
    btn.disabled = false;

    if (!data || !data.isSuccess) {
        err.textContent = (data && data.message) || '채팅방 생성에 실패했습니다.';
        return;
    }
    document.getElementById('createModal').hidden = true;
    window.location.href = '/chat/' + data.result.room_id;
});

// ── Init ──────────────────────────────────────────────────────
loadRooms();
