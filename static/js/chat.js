/* chat.js — 채팅방 목록 페이지
 * 의존: api.js (getToken, tryRefresh, apiFetch, showToast, esc)
 */

// ── 로컬 apiJSON: 전체 envelope { isSuccess, result } 반환 ──
async function apiJSON(url, opts) {
    const res = await apiFetch(url, opts);
    return res ? res.json() : null;
}

function fmtTime(iso) {
    if (!iso) return '';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    const KST = { timeZone: 'Asia/Seoul' };
    const sameDay = d.toLocaleDateString('ko-KR', KST) === new Date().toLocaleDateString('ko-KR', KST);
    if (sameDay) {
        return d.toLocaleTimeString('ko-KR', { ...KST, hour: '2-digit', minute: '2-digit', hour12: false });
    }
    return d.toLocaleDateString('ko-KR', { ...KST, month: 'numeric', day: 'numeric' })
            .replace('월 ', '/').replace('일', '').trim();
}

function getMyAccountId() {
    try {
        const token = getToken();
        if (!token) return '';
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.sub || '';
    } catch (_) { return ''; }
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
    document.getElementById('roomCount').textContent = `${rooms.length}개의 채팅방`;

    if (!rooms.length) {
        list.innerHTML = '<div class="state-cell">채팅방이 없습니다. 새 채팅을 시작해보세요.</div>';
        return;
    }

    const myId = getMyAccountId();
    list.innerHTML = rooms.map(r => {
        const initials = (r.room_name || r.members.map(m => m.name_ko).join(', ')).slice(0, 1);
        const name = r.room_type === 'DIRECT'
            ? (r.members.find(m => m.account_id !== myId) || r.members[0] || { name_ko: '?' }).name_ko
            : (r.room_name || '그룹 채팅');
        const time = fmtTime(r.last_message_at || r.created_at);
        const badge = r.unread_count > 0
            ? `<span class="unread-badge">${r.unread_count > 99 ? '99+' : r.unread_count}</span>`
            : '';
        return `<a class="room-card" href="/chat/${r.room_id}">
            <div class="room-card-icon">${esc(initials)}</div>
            <div class="room-card-body">
                <div class="room-card-name">${esc(name)}</div>
                <div class="room-card-preview">${esc(r.members.map(m => m.name_ko).join(', '))}</div>
            </div>
            <div class="room-card-right">
                <span class="room-card-time">${time}</span>
                ${badge}
            </div>
        </a>`;
    }).join('');
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
    document.getElementById('inputRoomName').value = '';
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
    const myId = getMyAccountId();
    const filtered = allMembers.filter(m =>
        m.account_id !== myId &&
        (!query || m.name_ko.toLowerCase().includes(query) || m.account_id.toLowerCase().includes(query))
    );

    if (!filtered.length) {
        list.innerHTML = '<div class="pick-empty">멤버가 없습니다.</div>';
        return;
    }

    const isGroup = selectedType === 'GROUP';
    list.innerHTML = filtered.map(m => {
        const sel = selectedMemberIds.has(m.member_id);
        return `<label class="member-pick-item${sel ? ' selected' : ''}">
            <input type="${isGroup ? 'checkbox' : 'radio'}" name="pickedMember" value="${m.member_id}"${sel ? ' checked' : ''}>
            <div>
                <div class="member-pick-name">${esc(m.name_ko)}</div>
                <div class="member-pick-sub">${esc(m.account_id)}</div>
            </div>
        </label>`;
    }).join('');
}

// 이벤트 위임: renderMemberPick 호출마다 리스너 재부착 없이 단일 리스너로 처리
document.getElementById('memberPickList').addEventListener('change', e => {
    const inp = e.target.closest('input[name="pickedMember"]');
    if (!inp) return;
    if (!inp.checked) { selectedMemberIds.delete(inp.value); return; }
    if (selectedType === 'DIRECT') selectedMemberIds.clear();
    selectedMemberIds.add(inp.value);
    renderMemberPick(document.getElementById('memberSearch').value.trim().toLowerCase());
});

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

// ── 실시간 갱신 (SSE) ────────────────────────────────────────────
let sseSource = null;
let _roomUpdateTimer;
let _sseDisconnectedAt = null;
function subscribeSSE() {
    if (sseSource) sseSource.close();
    sseSource = new EventSource('/stream?channel=' + encodeURIComponent('member:' + getMyAccountId()));
    sseSource.addEventListener('room_update', () => {
        clearTimeout(_roomUpdateTimer);
        _roomUpdateTimer = setTimeout(loadRooms, 200);
    });
    sseSource.addEventListener('open', () => {
        if (_sseDisconnectedAt) { loadRooms(); _sseDisconnectedAt = null; } // 재연결 시 놓친 변경사항 동기화
    });
    sseSource.onerror = () => {
        if (!_sseDisconnectedAt) _sseDisconnectedAt = new Date().toISOString();
    };
}

// ── Init ──────────────────────────────────────────────────────
loadRooms();
subscribeSSE();

window.addEventListener('pageshow', e => { if (e.persisted) loadRooms(); });

let _visTimer;
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { clearTimeout(_visTimer); _visTimer = setTimeout(loadRooms, 500); }
});
