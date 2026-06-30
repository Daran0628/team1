/* chatroom.js — 개별 채팅방 페이지 */

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
    const isFormData = options && options.body instanceof FormData;
    const headers = Object.assign(
        isFormData ? {} : { 'Content-Type': 'application/json' },
        { 'Authorization': 'Bearer ' + token },
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
    setTimeout(() => { t.classList.add('toast-out'); setTimeout(() => t.remove(), 300); }, 3000);
}

// ── Helpers ───────────────────────────────────────────────────
function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
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
    return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
}

function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.getFullYear() + '년 ' + (d.getMonth()+1) + '월 ' + d.getDate() + '일';
}

function fmtSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
    return (bytes/1048576).toFixed(1) + ' MB';
}

function fileEmoji(mime) {
    if (!mime) return '📄';
    if (mime.startsWith('image/')) return '🖼️';
    if (mime.includes('pdf')) return '📕';
    if (mime.includes('word') || mime.includes('document')) return '📝';
    if (mime.includes('excel') || mime.includes('sheet')) return '📊';
    if (mime.includes('zip') || mime.includes('compressed')) return '🗜️';
    return '📄';
}

// ── State ─────────────────────────────────────────────────────
const roomId      = location.pathname.split('/').filter(Boolean).pop();
const myAccountId = getMyAccountId();
let myMemberId    = null;  // UUID, populated after loadRoom()
let currentRoom   = null;
let allRooms    = [];
let allMembers  = [];
let sseSource   = null;
let selectedType     = 'DIRECT';
let selectedMemberIds = new Set();
let lastMsgSenderId  = null;
let lastMsgDate      = null;

// ── Sidebar rooms ─────────────────────────────────────────────
async function loadSidebarRooms() {
    const data = await apiJSON('/api/chat/rooms');
    if (!data || !data.isSuccess) return;
    allRooms = data.result || [];
    renderSidebar(allRooms);
}

function renderSidebar(rooms) {
    const list = document.getElementById('sidebarRoomList');
    if (!rooms.length) {
        list.innerHTML = '<li style="padding:.75rem 1rem;font-size:.8rem;color:var(--muted)">채팅방 없음</li>';
        return;
    }
    list.innerHTML = rooms.map(r => {
        const isActive = r.room_id === roomId;
        const name = r.room_type === 'DIRECT'
            ? (r.members.find(m => m.account_id !== myAccountId) || r.members[0] || {}).name_ko || '?'
            : (r.room_name || '그룹 채팅');
        const initials = name.slice(0,1);
        return '<li class="room-item' + (isActive ? ' active' : '') + '" data-id="' + r.room_id + '">' +
            '<div class="room-item-icon">' + initials + '</div>' +
            '<div class="room-item-body">' +
                '<div class="room-item-name">' + esc(name) + '</div>' +
                '<div class="room-item-sub">' + esc(r.members.length + '명') + '</div>' +
            '</div>' +
        '</li>';
    }).join('');

    list.querySelectorAll('.room-item').forEach(item => {
        item.addEventListener('click', () => {
            if (item.dataset.id !== roomId) window.location.href = '/chat/' + item.dataset.id;
        });
    });
}

document.getElementById('sidebarSearch').addEventListener('input', function() {
    const q = this.value.trim().toLowerCase();
    renderSidebar(allRooms.filter(r => {
        const n = r.room_name || r.members.map(m => m.name_ko).join(' ');
        return n.toLowerCase().includes(q);
    }));
});

// ── Room info ─────────────────────────────────────────────────
async function loadRoom() {
    const data = await apiJSON('/api/chat/rooms/' + roomId);
    if (!data || !data.isSuccess) { showToast('채팅방을 불러오지 못했습니다.', 'error'); return; }
    currentRoom = data.result;

    // 내 UUID를 account_id 기준으로 한 번만 추출
    const me = currentRoom.members.find(m => m.account_id === myAccountId);
    if (me) myMemberId = me.member_id;

    const name = currentRoom.room_type === 'DIRECT'
        ? (currentRoom.members.find(m => m.account_id !== myAccountId) || currentRoom.members[0] || {}).name_ko || '?'
        : (currentRoom.room_name || '그룹 채팅');

    document.title = name + ' — 채팅';
    document.getElementById('roomName').textContent = name;
    document.getElementById('roomIcon').textContent = currentRoom.room_type === 'DIRECT' ? '👤' : '#';
    document.getElementById('roomMeta').textContent = currentRoom.members.length + '명';
    document.getElementById('btnLeaveRoom').hidden = currentRoom.room_type !== 'GROUP';
}

// ── Messages ──────────────────────────────────────────────────
async function loadMessages() {
    const area = document.getElementById('messagesArea');

    // 항상 최신 50개를 불러온다. 서비스가 DESC→reverse로 시간순 반환
    const data = await apiJSON('/api/chat/rooms/' + roomId + '/messages?limit=50');
    if (!data || !data.isSuccess) {
        area.innerHTML = '<div class="state-cell">메시지를 불러오지 못했습니다.</div>';
        return;
    }

    area.innerHTML = '';
    lastMsgSenderId = null;
    lastMsgDate     = null;
    (data.result || []).forEach(appendMessage);
    scrollToBottom();
    markRead();
}

// SSE 재연결 후 놓친 메시지를 DB에서 보완
async function fetchMissedMessages(sinceIso) {
    if (!sinceIso) return;
    const data = await apiJSON(
        '/api/chat/rooms/' + roomId + '/messages?since=' + encodeURIComponent(sinceIso) + '&limit=100'
    );
    if (!data || !data.isSuccess) return;
    (data.result || []).forEach(msg => {
        if (!document.querySelector('[data-message-id="' + msg.message_id + '"]')) {
            appendMessage(msg);
        }
    });
    scrollToBottom();
}

function appendMessage(msg) {
    const area = document.getElementById('messagesArea');
    const mine = myMemberId ? msg.sender_id === myMemberId : false;

    // 날짜 구분선
    const msgDate = fmtDate(msg.created_at);
    if (msgDate !== lastMsgDate) {
        const div = document.createElement('div');
        div.className = 'date-divider';
        div.textContent = msgDate;
        area.appendChild(div);
        lastMsgDate = msgDate;
        lastMsgSenderId = null;
    }

    const sameSender = msg.sender_id === lastMsgSenderId;
    lastMsgSenderId = msg.sender_id;

    const row = document.createElement('div');
    row.className = 'msg-row' + (mine ? ' mine' : '') + (sameSender ? ' same-sender' : '');
    row.dataset.messageId = msg.message_id;

    const initials = (msg.sender_name || '?').slice(0,1);

    // 파일/이미지 버블
    let bubbleHTML;
    if ((msg.message_type === 'FILE' || msg.message_type === 'IMAGE') && msg.files && msg.files.length) {
        const f = msg.files[0];
        const isImage = f.mime_type && f.mime_type.startsWith('image/');
        if (isImage) {
            bubbleHTML = '<div class="bubble ' + (mine ? 'mine' : 'other') + ' img-bubble"' +
                ' data-file-id="' + f.file_id + '" data-name="' + esc(f.original_name) + '">' +
                '<div class="img-wrap"><div class="img-spinner"></div></div>' +
            '</div>';
        } else {
            bubbleHTML = '<div class="bubble ' + (mine ? 'mine' : 'other') + ' file-bubble" data-file-id="' + f.file_id + '">' +
                '<span class="file-icon-lg">' + fileEmoji(f.mime_type) + '</span>' +
                '<div class="file-info">' +
                    '<div class="file-name">' + esc(f.original_name) + '</div>' +
                    '<div class="file-size">' + fmtSize(f.file_size) + '</div>' +
                '</div>' +
            '</div>';
        }
    } else {
        bubbleHTML = '<div class="bubble ' + (mine ? 'mine' : 'other') + '">' + esc(msg.content || '') + '</div>';
    }

    row.innerHTML =
        '<div class="msg-avatar">' + initials + '</div>' +
        '<div class="msg-content">' +
            (!sameSender && !mine ? '<div class="msg-sender">' + esc(msg.sender_name) + '</div>' : '') +
            bubbleHTML +
            '<div class="msg-meta">' + fmtTime(msg.created_at) + '</div>' +
        '</div>';

    // 파일 클릭 → presigned URL 새 탭
    const fileBubble = row.querySelector('.file-bubble');
    if (fileBubble) {
        fileBubble.addEventListener('click', () => openFileUrl(fileBubble.dataset.fileId));
    }

    area.appendChild(row);

    // 이미지 비동기 로드 (DOM에 붙인 뒤 큐를 통해 순차 실행)
    const imgBubble = row.querySelector('.img-bubble');
    if (imgBubble) enqueueImageLoad(imgBubble);
}

async function openFileUrl(fileId) {
    const data = await apiJSON('/api/chat/rooms/' + roomId + '/files/' + fileId + '/url');
    if (!data || !data.isSuccess || !data.result) { showToast('파일 URL을 가져오지 못했습니다.', 'error'); return; }
    window.open(data.result.url, '_blank', 'noopener');
}

// ── 이미지 동시 로드 제한 (브라우저 connection stall 방지) ───────
const _imgQueue = [];
let _imgActive = 0;
const IMG_CONCURRENCY = 4;

function enqueueImageLoad(bubble) {
    _imgQueue.push(bubble);
    _drainImgQueue();
}

function _drainImgQueue() {
    while (_imgActive < IMG_CONCURRENCY && _imgQueue.length) {
        const b = _imgQueue.shift();
        _imgActive++;
        loadChatImage(b).finally(() => { _imgActive--; _drainImgQueue(); });
    }
}

async function loadChatImage(bubble) {
    const fileId = bubble.dataset.fileId;
    const name   = bubble.dataset.name || '';
    const wrap   = bubble.querySelector('.img-wrap');

    const data = await apiJSON('/api/chat/rooms/' + roomId + '/files/' + fileId + '/url');
    if (!data || !data.isSuccess || !data.result) {
        wrap.innerHTML = '<span class="img-error">이미지를 불러올 수 없습니다.</span>';
        return;
    }
    const url = data.result.url;
    const img = document.createElement('img');
    img.className = 'chat-img';
    img.alt = name;
    img.src = url;
    img.addEventListener('click', e => { e.stopPropagation(); openLightbox(url, name); });
    wrap.innerHTML = '';
    wrap.appendChild(img);
}

function openLightbox(src, name) {
    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightboxName').textContent = name;
    document.getElementById('lightbox').hidden = false;
}

function closeLightbox() {
    document.getElementById('lightbox').hidden = true;
    document.getElementById('lightboxImg').src = '';
}

document.getElementById('lightboxClose').addEventListener('click', closeLightbox);
document.getElementById('lightbox').addEventListener('click', e => {
    if (e.target === document.getElementById('lightbox')) closeLightbox();
});
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeLightbox();
});

function scrollToBottom() {
    const area = document.getElementById('messagesArea');
    area.scrollTop = area.scrollHeight;
}

async function markRead() {
    await apiFetch('/api/chat/rooms/' + roomId + '/read', { method: 'PUT' });
}

// ── SSE ───────────────────────────────────────────────────────
let _sseDisconnectedAt = null;

function subscribeSSE() {
    if (sseSource) sseSource.close();
    sseSource = new EventSource('/stream?channel=room:' + roomId);

    sseSource.addEventListener('message', e => {
        try {
            const msg = JSON.parse(e.data);
            const normalized = {
                message_id:   msg.messageId   || msg.message_id,
                room_id:      msg.roomId       || msg.room_id,
                sender_id:    msg.senderId     || msg.sender_id,
                sender_name:  msg.senderName   || msg.sender_name || '',
                message_type: msg.messageType  || msg.message_type || 'TEXT',
                content:      msg.content,
                is_deleted:   false,
                created_at:   msg.createdAt    || msg.created_at || new Date().toISOString(),
                files: msg.fileId ? [{
                    file_id:       msg.fileId,
                    original_name: msg.originalName || msg.content || 'file',
                    file_size:     0,
                    mime_type:     msg.mimeType || '',
                    created_at:    msg.createdAt || new Date().toISOString(),
                }] : [],
            };

            if (normalized.message_id &&
                document.querySelector('[data-message-id="' + normalized.message_id + '"]')) return;

            appendMessage(normalized);
            scrollToBottom();

            if (!myMemberId || normalized.sender_id !== myMemberId) markRead();
        } catch (_) {}
    });

    sseSource.addEventListener('open', () => {
        // 재연결 시 끊겼던 동안 놓친 메시지를 DB에서 보완
        if (_sseDisconnectedAt) {
            fetchMissedMessages(_sseDisconnectedAt);
            _sseDisconnectedAt = null;
        }
    });

    sseSource.onerror = () => {
        // 끊긴 시각 기록 — 재연결 후 fetchMissedMessages에서 사용
        if (!_sseDisconnectedAt) {
            _sseDisconnectedAt = new Date().toISOString();
        }
    };
}

// ── Send message ──────────────────────────────────────────────
const msgInput = document.getElementById('msgInput');
const btnSend  = document.getElementById('btnSend');

msgInput.addEventListener('input', function() {
    btnSend.disabled = !this.value.trim();
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

msgInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!btnSend.disabled) sendMessage();
    }
});

btnSend.addEventListener('click', sendMessage);

async function sendMessage() {
    const content = msgInput.value.trim();
    if (!content) return;

    msgInput.value = '';
    msgInput.style.height = 'auto';
    btnSend.disabled = true;

    const data = await apiJSON('/api/chat/rooms/' + roomId + '/messages', {
        method: 'POST',
        body: JSON.stringify({ messageType: 'TEXT', content }),
    });

    if (!data || !data.isSuccess) { showToast('메시지 전송에 실패했습니다.', 'error'); }
}

// ── File upload ───────────────────────────────────────────────
document.getElementById('btnAttach').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', async function() {
    const file = this.files[0];
    if (!file) return;
    this.value = '';

    const bar = document.getElementById('uploadBar');
    document.getElementById('uploadBarText').textContent = '"' + file.name + '" 업로드 중...';
    bar.hidden = false;

    const fd = new FormData();
    fd.append('file', file);

    const data = await apiJSON('/api/chat/rooms/' + roomId + '/files', {
        method: 'POST',
        body: fd,
    });

    bar.hidden = true;
    if (!data || !data.isSuccess) { showToast('파일 업로드에 실패했습니다.', 'error'); }
});

// ── Members modal ─────────────────────────────────────────────
function openMembersModal() {
    if (!currentRoom) return;
    const isGroup  = currentRoom.room_type === 'GROUP';
    const isAdmin  = currentRoom.members.some(
        m => m.account_id === myAccountId && m.room_role === 'ADMIN'
    );
    const list     = document.getElementById('membersList');
    const btnInvite = document.getElementById('btnInviteMember');

    // 초대 버튼: 그룹 + 관리자만 표시
    btnInvite.hidden = !(isGroup && isAdmin);

    list.innerHTML = currentRoom.members.map(m => {
        const isMe = m.account_id === myAccountId;
        const roleBadge = (isGroup && m.room_role === 'ADMIN')
            ? '<span style="font-size:.7rem;color:var(--primary);font-weight:600;margin-left:.3rem">관리자</span>'
            : '';
        const kickBtn = (isGroup && isAdmin && !isMe)
            ? '<button class="btn btn-ghost" style="margin-left:auto;font-size:.75rem;color:var(--danger);padding:.15rem .5rem" data-kick="' + m.member_id + '">추방</button>'
            : '';
        return '<div style="display:flex;align-items:center;padding:.3rem 0;font-size:.875rem">' +
            esc(m.name_ko) + roleBadge + kickBtn +
        '</div>';
    }).join('');

    // 추방 버튼 이벤트
    list.querySelectorAll('[data-kick]').forEach(btn => {
        btn.addEventListener('click', () => kickMember(btn.dataset.kick));
    });

    document.getElementById('membersModal').hidden = false;
}

document.getElementById('btnMembers').addEventListener('click', openMembersModal);

async function kickMember(targetMemberId) {
    if (!confirm('이 멤버를 추방하시겠습니까?')) return;
    const data = await apiJSON(
        '/api/chat/rooms/' + roomId + '/members/' + targetMemberId,
        { method: 'DELETE' }
    );
    if (!data || !data.isSuccess) { showToast('추방에 실패했습니다.', 'error'); return; }
    showToast('멤버를 추방했습니다.', 'success');
    // 방 정보 갱신 후 모달 다시 렌더
    const roomData = await apiJSON('/api/chat/rooms/' + roomId);
    if (roomData && roomData.isSuccess) currentRoom = roomData.result;
    openMembersModal();
}

// 초대 버튼 → 멤버 모달 닫고 초대 피커 열기
document.getElementById('btnInviteMember').addEventListener('click', () => {
    document.getElementById('membersModal').hidden = true;
    openInviteModal();
});

async function openInviteModal() {
    if (!allMembers.length) {
        const data = await apiJSON('/api/group/members');
        allMembers = (data && data.result) || [];
    }
    // 이미 멤버인 사람 제외
    const existingIds = new Set(currentRoom.members.map(m => m.member_id));
    const candidates = allMembers.filter(m => !existingIds.has(m.member_id));

    if (!candidates.length) { showToast('초대할 수 있는 멤버가 없습니다.', 'info'); return; }

    selectedMemberIds.clear();
    selectedType = 'GROUP';
    document.getElementById('groupNameField').hidden = true;
    document.getElementById('createErr').textContent = '';

    const list = document.getElementById('memberPickList');
    list.innerHTML = candidates.map(m => {
        return '<label class="member-pick-item">' +
            '<input type="checkbox" name="pickedMember" value="' + m.member_id + '">' +
            '<div><div class="member-pick-name">' + esc(m.name_ko) + '</div>' +
            '<div class="member-pick-sub">' + esc(m.account_id) + '</div></div>' +
        '</label>';
    }).join('');

    list.querySelectorAll('input').forEach(inp => {
        inp.addEventListener('change', () => {
            inp.checked ? selectedMemberIds.add(inp.value) : selectedMemberIds.delete(inp.value);
            inp.closest('label').classList.toggle('selected', inp.checked);
        });
    });

    // 만들기 버튼을 "초대" 용도로 임시 교체
    const btnCreate = document.getElementById('btnCreateRoom');
    btnCreate.textContent = '초대';
    btnCreate._inviteMode = true;

    document.getElementById('createModal').hidden = false;
}


// ── Create room modal (sidebar button) ───────────────────────
document.getElementById('btnNewChat').addEventListener('click', openCreateModal);

document.getElementById('btnLeaveRoom').addEventListener('click', async () => {
    if (!confirm('채팅방을 나가시겠습니까?')) return;
    const data = await apiJSON('/api/chat/rooms/' + roomId + '/leave', { method: 'POST' });
    if (!data || !data.isSuccess) { showToast('나가기에 실패했습니다.', 'error'); return; }
    window.location.href = '/chat';
});

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
        const data = await apiJSON('/api/group/members');
        allMembers = (data && data.result) || [];
    }
    renderMemberPick('');
}

function renderMemberPick(query) {
    const list = document.getElementById('memberPickList');
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
    const btn = document.getElementById('btnCreateRoom');
    const err = document.getElementById('createErr');
    err.textContent = '';
    const memberIds = [...selectedMemberIds];
    if (!memberIds.length) { err.textContent = '멤버를 선택해주세요.'; return; }

    // 초대 모드: 기존 방에 멤버 추가
    if (btn._inviteMode) {
        btn.disabled = true;
        const data = await apiJSON('/api/chat/rooms/' + roomId + '/members', {
            method: 'POST',
            body: JSON.stringify({ memberIds }),
        });
        btn.disabled = false;
        btn._inviteMode = false;
        btn.textContent = '만들기';
        document.getElementById('createModal').hidden = true;
        if (!data || !data.isSuccess) { showToast('초대에 실패했습니다.', 'error'); return; }
        showToast('멤버를 초대했습니다.', 'success');
        const roomData = await apiJSON('/api/chat/rooms/' + roomId);
        if (roomData && roomData.isSuccess) currentRoom = roomData.result;
        return;
    }

    // 일반 방 생성 모드
    const body = { roomType: selectedType, memberIds };
    if (selectedType === 'GROUP') {
        const name = document.getElementById('inputRoomName').value.trim();
        if (!name) { err.textContent = '채팅방 이름을 입력해주세요.'; return; }
        body.roomName = name;
    }
    btn.disabled = true;
    const data = await apiJSON('/api/chat/rooms', { method: 'POST', body: JSON.stringify(body) });
    btn.disabled = false;
    if (!data || !data.isSuccess) { err.textContent = (data && data.message) || '생성 실패'; return; }
    document.getElementById('createModal').hidden = true;
    window.location.href = '/chat/' + data.result.room_id;
});

// ── Modal helpers ─────────────────────────────────────────────
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => { document.getElementById(btn.dataset.close).hidden = true; });
});
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.hidden = true; });
});

// 페이지 포커스 시 읽음 처리
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) markRead();
});

// ── Init ──────────────────────────────────────────────────────
async function init() {
    await Promise.all([loadSidebarRooms(), loadRoom()]);
    await loadMessages();
    subscribeSSE();
    msgInput.focus();
}

init();
