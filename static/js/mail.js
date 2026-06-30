const API = '/api/mail';
const token = () => sessionStorage.getItem('access_token');

if (!token()) { window.location.replace('/login'); }

const mailList       = document.getElementById('mailList');
const mailDetail     = document.getElementById('mailDetail');
const mailCompose    = document.getElementById('mailCompose');
const viewEmpty      = document.getElementById('viewEmpty');
const unreadBadge    = document.getElementById('unreadBadge');
const sidebarAccount = document.getElementById('sidebarAccount');
const panelTitle     = document.getElementById('panelTitle');

let currentUid     = null;
let currentFolder  = 'inbox';
let currentMessage = null;

// ── 계정 표시 ────────────────────────────────
function parseJwt(t) {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return {}; }
}
const payload = parseJwt(token() || '');
if (payload.sub) sidebarAccount.textContent = payload.sub;

// ── 폴더 전환 ────────────────────────────────
document.querySelectorAll('.folder-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.folder-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        currentFolder  = item.dataset.folder;
        currentUid     = null;
        currentMessage = null;
        showPanel('empty');
        panelTitle.textContent = currentFolder === 'sent' ? '보낸 편지함' : '받은 편지함';
        if (currentFolder === 'sent') loadSent();
        else loadInbox();
    });
});

// ── 받은 편지함 로드 ─────────────────────────
async function loadInbox() {
    mailList.innerHTML = '<li class="mail-empty">불러오는 중...</li>';
    try {
        const res  = await fetch(`${API}/inbox`, { headers: { Authorization: `Bearer ${token()}` } });
        const data = await res.json();
        if (!res.ok) { mailList.innerHTML = `<li class="mail-empty">오류: ${data.message}</li>`; return; }

        const messages = data.result || [];
        if (messages.length === 0) { mailList.innerHTML = '<li class="mail-empty">메일이 없습니다</li>'; return; }

        const unread = messages.filter(m => !m.is_read).length;
        unreadBadge.textContent = unread > 0 ? unread : '';

        mailList.innerHTML = '';
        messages.forEach(m => {
            const li = document.createElement('li');
            li.className = `mail-item${m.is_read ? '' : ' unread'}`;
            li.dataset.uid = m.uid;
            li.innerHTML = `
                <div class="mail-item-subject">${escHtml(m.subject)}</div>
                <div class="mail-item-meta">
                    <span>${escHtml(m.from)}</span>
                    <span>${formatDate(m.date)}</span>
                </div>`;
            li.addEventListener('click', () => openMessage(m.uid, li));
            mailList.appendChild(li);
        });
    } catch {
        mailList.innerHTML = '<li class="mail-empty">불러오기 실패</li>';
    }
}

// ── 보낸 편지함 로드 ─────────────────────────
async function loadSent() {
    mailList.innerHTML = '<li class="mail-empty">불러오는 중...</li>';
    try {
        const res  = await fetch(`${API}/sent`, { headers: { Authorization: `Bearer ${token()}` } });
        const data = await res.json();
        if (!res.ok) { mailList.innerHTML = `<li class="mail-empty">오류: ${data.message}</li>`; return; }

        const messages = data.result || [];
        if (messages.length === 0) { mailList.innerHTML = '<li class="mail-empty">보낸 메일이 없습니다</li>'; return; }

        mailList.innerHTML = '';
        messages.forEach(m => {
            const li = document.createElement('li');
            li.className = 'mail-item';
            li.dataset.uid = m.uid;
            li.innerHTML = `
                <div class="mail-item-subject">${escHtml(m.subject)}</div>
                <div class="mail-item-meta">
                    <span>To: ${escHtml(m.to)}</span>
                    <span>${formatDate(m.date)}</span>
                </div>`;
            li.addEventListener('click', () => openMessage(m.uid, li));
            mailList.appendChild(li);
        });
    } catch {
        mailList.innerHTML = '<li class="mail-empty">불러오기 실패</li>';
    }
}

// ── 메일 열기 ─────────────────────────────────
async function openMessage(uid, el) {
    document.querySelectorAll('.mail-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');
    if (currentFolder === 'inbox') el.classList.remove('unread');
    currentUid = uid;

    showPanel('detail');
    document.getElementById('detailSubject').textContent = '불러오는 중...';
    document.getElementById('detailBody').textContent    = '';

    const endpoint = currentFolder === 'sent'
        ? `${API}/sent/${uid}`
        : `${API}/message/${uid}`;

    try {
        const res  = await fetch(endpoint, { headers: { Authorization: `Bearer ${token()}` } });
        const data = await res.json();
        if (!res.ok) return;

        const m = data.result;
        currentMessage = m;

        document.getElementById('detailSubject').textContent = m.subject;
        document.getElementById('detailFrom').textContent    = currentFolder === 'sent'
            ? `받는 사람: ${m.to}`
            : `보낸 사람: ${m.from}`;
        document.getElementById('detailDate').textContent    = formatDate(m.date);
        document.getElementById('detailBody').textContent    = m.body;

        document.getElementById('btnReply').style.display = currentFolder === 'inbox' ? '' : 'none';

        if (currentFolder === 'inbox') updateUnread();
    } catch {}
}

// ── 답장 ──────────────────────────────────────
document.getElementById('btnReply').addEventListener('click', () => {
    if (!currentMessage) return;
    const fromRaw    = currentMessage.from || '';
    const emailMatch = fromRaw.match(/<(.+?)>/) || [null, fromRaw];
    const replyTo    = (emailMatch[1] || fromRaw).trim();
    const subject    = currentMessage.subject.startsWith('Re:')
        ? currentMessage.subject
        : `Re: ${currentMessage.subject}`;
    const quoted     = currentMessage.body
        ? `\n\n---\n${fromRaw} 작성:\n${currentMessage.body}`
        : '';

    document.getElementById('composeTo').value        = replyTo;
    document.getElementById('composeSubject').value   = subject;
    document.getElementById('composeBody').value      = quoted;
    document.getElementById('composeMsg').textContent = '';
    showPanel('compose');
});

// ── 메일 삭제 ─────────────────────────────────
document.getElementById('btnDelete').addEventListener('click', async () => {
    if (!currentUid || !confirm('이 메일을 삭제할까요?')) return;
    const endpoint = currentFolder === 'sent'
        ? `${API}/sent/${currentUid}`
        : `${API}/message/${currentUid}`;
    const res = await fetch(endpoint, {
        method:  'DELETE',
        headers: { Authorization: `Bearer ${token()}` },
    });
    if (res.ok) {
        showPanel('empty');
        currentUid     = null;
        currentMessage = null;
        if (currentFolder === 'sent') loadSent();
        else loadInbox();
    }
});

// ── 편지 쓰기 ─────────────────────────────────
document.getElementById('btnCompose').addEventListener('click', () => {
    document.getElementById('composeTo').value        = '';
    document.getElementById('composeSubject').value   = '';
    document.getElementById('composeBody').value      = '';
    document.getElementById('composeMsg').textContent = '';
    showPanel('compose');
});

document.getElementById('btnCloseCompose').addEventListener('click', () => showPanel('empty'));

document.getElementById('btnSend').addEventListener('click', async () => {
    const to      = document.getElementById('composeTo').value.trim();
    const subject = document.getElementById('composeSubject').value.trim();
    const body    = document.getElementById('composeBody').value;
    const msgEl   = document.getElementById('composeMsg');
    const btnSend = document.getElementById('btnSend');

    if (!to || !subject) { setMsg(msgEl, '받는 사람과 제목을 입력하세요.', 'error'); return; }

    btnSend.disabled = true;
    setMsg(msgEl, '발송 중...', '');

    try {
        const res  = await fetch(`${API}/send`, {
            method:  'POST',
            headers: { Authorization: `Bearer ${token()}`, 'Content-Type': 'application/json' },
            body:    JSON.stringify({ to, subject, body }),
        });
        const data = await res.json();
        if (res.ok) {
            setMsg(msgEl, '발송 완료!', 'success');
            setTimeout(() => showPanel('empty'), 1500);
        } else {
            setMsg(msgEl, `발송 실패: ${data.message}`, 'error');
        }
    } catch {
        setMsg(msgEl, '네트워크 오류', 'error');
    } finally {
        btnSend.disabled = false;
    }
});

// ── 새로고침 ──────────────────────────────────
document.getElementById('btnRefresh').addEventListener('click', () => {
    if (currentFolder === 'sent') loadSent();
    else loadInbox();
});

// ── 유틸 ──────────────────────────────────────
function showPanel(type) {
    viewEmpty.hidden   = type !== 'empty';
    mailDetail.hidden  = type !== 'detail';
    mailCompose.hidden = type !== 'compose';
}

function updateUnread() {
    const count = document.querySelectorAll('.mail-item.unread').length;
    unreadBadge.textContent = count > 0 ? count : '';
}

function escHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch { return dateStr; }
}

function setMsg(el, text, cls) {
    el.textContent = text;
    el.className   = `compose-msg ${cls}`;
}

// 초기 로드
loadInbox();
