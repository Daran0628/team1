/* chatroom.js — 개별 채팅방 페이지
 * 의존: api.js (getToken, tryRefresh, apiFetch, showToast, esc)
 */

// ── 로컬 apiJSON: 전체 envelope { isSuccess, result } 반환 ──
async function apiJSON(url, opts) {
    const res = await apiFetch(url, opts);
    return res ? res.json() : null;
}

// ── Helpers ───────────────────────────────────────────────────
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
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    return d.toLocaleTimeString('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false });
}

function fmtDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일';
}

function fmtSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
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
let myMemberId    = null;
let currentRoom   = null;
let allRooms      = [];
let allMembers    = [];
let sseSource     = null;
let selectedType      = 'DIRECT';
let selectedMemberIds = new Set();
let lastMsgSenderId   = null;
let lastMsgDate       = null;
let inviteSelectedIds = new Set();
let inviteCandidates  = [];

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
        list.innerHTML = '<li class="sidebar-empty">채팅방 없음</li>';
        return;
    }
    list.innerHTML = rooms.map(r => {
        const isActive = r.room_id === roomId;
        const name = r.room_type === 'DIRECT'
            ? (r.members.find(m => m.account_id !== myAccountId) || r.members[0] || {}).name_ko || '?'
            : (r.room_name || '그룹 채팅');
        return `<li class="room-item${isActive ? ' active' : ''}" data-id="${r.room_id}">
            <div class="room-item-icon">${esc(name.slice(0, 1))}</div>
            <div class="room-item-body">
                <div class="room-item-name">${esc(name)}</div>
                <div class="room-item-sub">${esc(r.members.length + '명')}</div>
            </div>
        </li>`;
    }).join('');
}

// 이벤트 위임: 사이드바 방 목록
document.getElementById('sidebarRoomList').addEventListener('click', e => {
    const item = e.target.closest('.room-item');
    if (item && item.dataset.id !== roomId) window.location.href = '/chat/' + item.dataset.id;
});

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

async function fetchMissedMessages(sinceIso) {
    if (!sinceIso) return;
    const data = await apiJSON(
        '/api/chat/rooms/' + roomId + '/messages?since=' + encodeURIComponent(sinceIso) + '&limit=100'
    );
    if (!data || !data.isSuccess) return;
    (data.result || []).forEach(msg => {
        if (!document.querySelector('[data-message-id="' + msg.message_id + '"]')) appendMessage(msg);
    });
    scrollToBottom();
}

function appendMessage(rawMsg) {
    const msg = {
        message_id:   rawMsg.message_id   || rawMsg.messageId,
        sender_id:    rawMsg.sender_id     || rawMsg.senderId,
        sender_name:  rawMsg.sender_name   || rawMsg.senderName || '',
        message_type: (rawMsg.message_type || rawMsg.messageType || 'TEXT').toUpperCase(),
        content:      rawMsg.content       || '',
        created_at:   rawMsg.created_at    || rawMsg.createdAt   || new Date().toISOString(),
        files:        rawMsg.files         || [],
    };
    const area = document.getElementById('messagesArea');

    const msgDate = fmtDate(msg.created_at);
    if (msgDate !== lastMsgDate) {
        const div = document.createElement('div');
        div.className = 'date-divider';
        div.textContent = msgDate;
        area.appendChild(div);
        lastMsgDate = msgDate;
        lastMsgSenderId = null;
    }

    if (msg.message_type === 'NOTICE') {
        const notice = document.createElement('div');
        notice.className = 'notice-msg';
        notice.dataset.messageId = msg.message_id;
        notice.textContent = msg.content;
        area.appendChild(notice);
        lastMsgSenderId = null;
        return;
    }

    const mine = myMemberId ? msg.sender_id === myMemberId : false;
    const sameSender = msg.sender_id === lastMsgSenderId;
    lastMsgSenderId = msg.sender_id;

    const row = document.createElement('div');
    row.className = `msg-row${mine ? ' mine' : ''}${sameSender ? ' same-sender' : ''}`;
    row.dataset.messageId = msg.message_id;

    let bubbleHTML;
    if ((msg.message_type === 'FILE' || msg.message_type === 'IMAGE') && msg.files && msg.files.length) {
        const f = msg.files[0];
        if (f.mime_type && f.mime_type.startsWith('image/')) {
            bubbleHTML = `<div class="bubble ${mine ? 'mine' : 'other'} img-bubble"
                data-file-id="${f.file_id}" data-name="${esc(f.original_name)}">
                <div class="img-wrap"><div class="img-spinner"></div></div>
            </div>`;
        } else {
            bubbleHTML = `<div class="bubble ${mine ? 'mine' : 'other'} file-bubble" data-file-id="${f.file_id}">
                <span class="file-icon-lg">${fileEmoji(f.mime_type)}</span>
                <div class="file-info">
                    <div class="file-name">${esc(f.original_name)}</div>
                    <div class="file-size">${fmtSize(f.file_size)}</div>
                </div>
            </div>`;
        }
    } else {
        bubbleHTML = `<div class="bubble ${mine ? 'mine' : 'other'}">${esc(msg.content || '')}</div>`;
    }

    const currTime = fmtTime(msg.created_at);

    row.innerHTML = `
        <div class="msg-avatar">${esc((msg.sender_name || '?').slice(0, 1))}</div>
        <div class="msg-content">
            ${!sameSender && !mine ? `<div class="msg-sender">${esc(msg.sender_name)}</div>` : ''}
            ${bubbleHTML}
            <div class="msg-meta">${currTime}</div>
        </div>`;

    row.dataset.senderId = msg.sender_id;
    row.dataset.msgTime  = currTime;

    const prevEl = area.lastElementChild;
    if (prevEl && prevEl.classList.contains('msg-row') &&
        prevEl.dataset.senderId === msg.sender_id &&
        prevEl.dataset.msgTime  === currTime) {
        const prevMeta = prevEl.querySelector('.msg-meta');
        if (prevMeta) prevMeta.style.display = 'none';
    }

    const fileBubble = row.querySelector('.file-bubble');
    if (fileBubble) {
        fileBubble.addEventListener('click', () => openFileUrl(fileBubble.dataset.fileId));
    }

    area.appendChild(row);

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
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

function scrollToBottom() {
    const area = document.getElementById('messagesArea');
    area.scrollTop = area.scrollHeight;
}

async function markRead() {
    await apiFetch('/api/chat/rooms/' + roomId + '/read', { method: 'PUT' });
}

let _markTimer;
function scheduleMarkRead() {
    clearTimeout(_markTimer);
    _markTimer = setTimeout(markRead, 300);
}

// ── SSE ───────────────────────────────────────────────────────
let _sseDisconnectedAt = null;

function subscribeSSE() {
    if (sseSource) sseSource.close();
    sseSource = new EventSource('/stream?channel=' + encodeURIComponent('room:' + roomId));

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

            if (!myMemberId || normalized.sender_id !== myMemberId) scheduleMarkRead();
        } catch (_) {}
    });

    sseSource.addEventListener('open', () => {
        if (_sseDisconnectedAt) {
            fetchMissedMessages(_sseDisconnectedAt);
            _sseDisconnectedAt = null;
        }
    });

    sseSource.onerror = () => {
        if (!_sseDisconnectedAt) _sseDisconnectedAt = new Date().toISOString();
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
    document.getElementById('uploadBarText').textContent = `"${file.name}" 업로드 중...`;
    bar.hidden = false;

    const fd = new FormData();
    fd.append('file', file);

    const data = await apiJSON('/api/chat/rooms/' + roomId + '/files', { method: 'POST', body: fd });

    bar.hidden = true;
    if (!data || !data.isSuccess) { showToast('파일 업로드에 실패했습니다.', 'error'); }
});

// ── Members modal ─────────────────────────────────────────────
function openMembersModal() {
    if (!currentRoom) return;
    const isGroup = currentRoom.room_type === 'GROUP';
    const isAdmin = currentRoom.members.some(m => m.account_id === myAccountId && m.room_role === 'ADMIN');
    const list    = document.getElementById('membersList');

    document.getElementById('btnInviteMember').hidden = !(isGroup && isAdmin);

    list.innerHTML = currentRoom.members.map(m => {
        const isMe      = m.account_id === myAccountId;
        const roleBadge = (isGroup && m.room_role === 'ADMIN') ? '<span class="admin-badge">관리자</span>' : '';
        const kickBtn   = (isGroup && isAdmin && !isMe)
            ? `<button class="btn btn-ghost btn-kick" data-kick="${m.member_id}">추방</button>`
            : '';
        return `<div class="member-row">${roleBadge}${esc(m.name_ko)}${kickBtn}</div>`;
    }).join('');

    document.getElementById('membersModal').hidden = false;
}

// 이벤트 위임: 멤버 모달 추방 버튼
document.getElementById('membersList').addEventListener('click', e => {
    const btn = e.target.closest('[data-kick]');
    if (btn) kickMember(btn.dataset.kick);
});

document.getElementById('btnMembers').addEventListener('click', openMembersModal);

async function kickMember(targetMemberId) {
    if (!confirm('이 멤버를 추방하시겠습니까?')) return;
    const data = await apiJSON(
        '/api/chat/rooms/' + roomId + '/members/' + targetMemberId,
        { method: 'DELETE' }
    );
    if (!data || !data.isSuccess) { showToast('추방에 실패했습니다.', 'error'); return; }
    showToast('멤버를 추방했습니다.', 'success');
    const roomData = await apiJSON('/api/chat/rooms/' + roomId);
    if (roomData && roomData.isSuccess) currentRoom = roomData.result;
    openMembersModal();
}

document.getElementById('btnInviteMember').addEventListener('click', () => {
    document.getElementById('membersModal').hidden = true;
    openInviteModal();
});

async function openInviteModal() {
    if (!allMembers.length) {
        const data = await apiJSON('/api/chat/members');
        allMembers = (data && data.result) || [];
    }
    const existingIds = new Set(currentRoom.members.map(m => m.member_id));
    inviteCandidates = allMembers.filter(m => !existingIds.has(m.member_id));

    if (!inviteCandidates.length) { showToast('초대할 수 있는 멤버가 없습니다.', 'info'); return; }

    inviteSelectedIds.clear();
    document.getElementById('inviteErr').textContent = '';
    document.getElementById('inviteSearch').value = '';

    renderInvitePick('');
    document.getElementById('inviteModal').hidden = false;
}

function renderInvitePick(query) {
    const list = document.getElementById('invitePickList');
    const filtered = inviteCandidates.filter(m =>
        !query || m.name_ko.toLowerCase().includes(query) || m.account_id.toLowerCase().includes(query)
    );
    if (!filtered.length) {
        list.innerHTML = '<div class="pick-empty">멤버가 없습니다.</div>';
        return;
    }
    list.innerHTML = filtered.map(m => {
        const sel = inviteSelectedIds.has(m.member_id);
        return `<label class="member-pick-item${sel ? ' selected' : ''}">
            <input type="checkbox" name="inviteMember" value="${m.member_id}"${sel ? ' checked' : ''}>
            <div>
                <div class="member-pick-name">${esc(m.name_ko)}</div>
                <div class="member-pick-sub">${esc(m.account_id)}</div>
            </div>
        </label>`;
    }).join('');
}

// 이벤트 위임: 초대 모달 멤버 선택
document.getElementById('invitePickList').addEventListener('change', e => {
    const inp = e.target.closest('input[name="inviteMember"]');
    if (!inp) return;
    inp.checked ? inviteSelectedIds.add(inp.value) : inviteSelectedIds.delete(inp.value);
    inp.closest('label').classList.toggle('selected', inp.checked);
});

document.getElementById('inviteSearch').addEventListener('input', function() {
    renderInvitePick(this.value.trim().toLowerCase());
});

document.getElementById('btnDoInvite').addEventListener('click', async () => {
    const err = document.getElementById('inviteErr');
    err.textContent = '';
    const memberIds = [...inviteSelectedIds];
    if (!memberIds.length) { err.textContent = '멤버를 선택해주세요.'; return; }

    const btn = document.getElementById('btnDoInvite');
    btn.disabled = true;
    const data = await apiJSON('/api/chat/rooms/' + roomId + '/members', {
        method: 'POST',
        body: JSON.stringify({ memberIds }),
    });
    btn.disabled = false;

    if (!data || !data.isSuccess) {
        err.textContent = (data && data.message) || '초대에 실패했습니다.';
        return;
    }
    document.getElementById('inviteModal').hidden = true;
    showToast('멤버를 초대했습니다.', 'success');
    const roomData = await apiJSON('/api/chat/rooms/' + roomId);
    if (roomData && roomData.isSuccess) currentRoom = roomData.result;
});

// ── Create room modal (sidebar button) ───────────────────────
document.getElementById('btnNewChat').addEventListener('click', openCreateModal);

document.getElementById('btnLeaveRoom').addEventListener('click', async () => {
    if (!currentRoom) return;
    const isAdmin = currentRoom.members.some(m => m.account_id === myAccountId && m.room_role === 'ADMIN');
    const otherActive = currentRoom.members.filter(m => m.account_id !== myAccountId);

    if (isAdmin && otherActive.length > 0) {
        openTransferModal(otherActive);
    } else {
        if (!confirm('채팅방을 나가시겠습니까?')) return;
        const data = await apiJSON('/api/chat/rooms/' + roomId + '/leave', { method: 'POST' });
        if (!data || !data.isSuccess) { showToast('나가기에 실패했습니다.', 'error'); return; }
        window.location.href = '/chat';
    }
});

// ── Admin transfer modal ──────────────────────────────────────
let transferSelectedId = null;

function openTransferModal(candidates) {
    transferSelectedId = null;
    document.getElementById('transferErr').textContent = '';
    const list = document.getElementById('transferPickList');
    list.innerHTML = candidates.map(m =>
        `<label class="member-pick-item">
            <input type="radio" name="transferMember" value="${m.member_id}">
            <div>
                <div class="member-pick-name">${esc(m.name_ko)}</div>
                <div class="member-pick-sub">${esc(m.account_id)}</div>
            </div>
        </label>`
    ).join('');
    document.getElementById('transferModal').hidden = false;
}

// 이벤트 위임: 관리자 이양 모달
document.getElementById('transferPickList').addEventListener('change', e => {
    const inp = e.target.closest('input[name="transferMember"]');
    if (!inp) return;
    transferSelectedId = inp.value;
    document.getElementById('transferPickList').querySelectorAll('label').forEach(l => l.classList.remove('selected'));
    inp.closest('label').classList.add('selected');
});

document.getElementById('btnDoTransfer').addEventListener('click', async () => {
    const err = document.getElementById('transferErr');
    err.textContent = '';
    if (!transferSelectedId) { err.textContent = '새 관리자를 선택해주세요.'; return; }
    const btn = document.getElementById('btnDoTransfer');
    btn.disabled = true;
    const data = await apiJSON('/api/chat/rooms/' + roomId + '/leave', {
        method: 'POST',
        body: JSON.stringify({ newAdminId: transferSelectedId }),
    });
    btn.disabled = false;
    if (!data || !data.isSuccess) { err.textContent = (data && data.message) || '이양에 실패했습니다.'; return; }
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
        const data = await apiJSON('/api/chat/members');
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

// 이벤트 위임: 방 생성 모달 멤버 선택
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
    const btn = document.getElementById('btnCreateRoom');
    const err = document.getElementById('createErr');
    err.textContent = '';
    const memberIds = [...selectedMemberIds];
    if (!memberIds.length) { err.textContent = '멤버를 선택해주세요.'; return; }

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
    btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.close);
        if (target) target.hidden = true;
    });
});
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.hidden = true; });
});

document.addEventListener('visibilitychange', () => { if (!document.hidden) markRead(); });

// ── Init ──────────────────────────────────────────────────────
async function init() {
    await Promise.all([loadSidebarRooms(), loadRoom()]);
    await loadMessages();
    subscribeSSE();
    msgInput.focus();
}

init();
