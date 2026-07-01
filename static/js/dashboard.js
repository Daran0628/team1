/* dashboard.js — 대시보드 카드에 실데이터 연동 */

const WORK_TYPE_LABEL = {
    FULL_TIME: '정규직',
    PART_TIME: '파트타임',
    CONTRACT:  '계약직',
    INTERN:    '인턴',
};

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error(json.message || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

function fmtDateTime(iso) {
    if (!iso) return '-';
    try {
        const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
        return d.toLocaleString('ko-KR', {
            timeZone: 'Asia/Seoul',
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', hour12: false,
        });
    } catch { return iso; }
}

function fmtChatTime(iso) {
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

async function loadWelcomeCard() {
    try {
        const member = await apiJSON('/api/member/me');
        if (!member) return;
        document.getElementById('welcomeName').textContent = `${member.name_ko}님, 환영합니다!`;
        document.getElementById('welcomeDept').textContent = member.department_name || '-';
        document.getElementById('welcomeWorkType').textContent = WORK_TYPE_LABEL[member.work_type] || member.work_type || '-';
        document.getElementById('welcomeEmail').textContent = member.email || '-';
        document.getElementById('welcomeLastLogin').textContent = fmtDateTime(member.last_login);
    } catch (e) {
        showToast(e.message || '내 정보를 불러오지 못했습니다.', 'error');
    }
}

async function loadMailSummary() {
    try {
        const [inbox, sent] = await Promise.all([
            apiJSON('/api/mail/inbox'),
            apiJSON('/api/mail/sent'),
        ]);
        document.getElementById('mailInboxCount').textContent = (inbox || []).length;
        document.getElementById('mailSentCount').textContent = (sent || []).length;
    } catch (e) {
        document.getElementById('mailSummaryBody').innerHTML =
            '<div class="empty-note">메일 정보를 불러오지 못했습니다.</div>';
    }
}

async function loadRecentChats() {
    const body = document.getElementById('chatListBody');
    try {
        const rooms = await apiJSON('/api/chat/rooms');
        const sorted = (rooms || []).slice().sort((a, b) => {
            const ta = new Date(a.last_message_at || a.created_at).getTime();
            const tb = new Date(b.last_message_at || b.created_at).getTime();
            return tb - ta;
        }).slice(0, 4);

        if (sorted.length === 0) {
            body.innerHTML = '<div class="empty-note">참여 중인 채팅방이 없습니다.</div>';
            return;
        }

        body.innerHTML = sorted.map(r => {
            const isGroup = r.members.length > 2 || !!r.room_name;
            const name = r.room_name || r.members.map(m => m.name_ko).join(', ') || '채팅방';
            const memberNames = r.members.map(m => m.name_ko).join(', ');
            const time = fmtChatTime(r.last_message_at || r.created_at);
            const badge = r.unread_count > 0
                ? `<span class="chat-badge">${r.unread_count > 99 ? '99+' : r.unread_count}</span>`
                : '';
            return `
                <div class="chat-row">
                    <div class="chat-avatar">${isGroup ? '👥' : '👤'}</div>
                    <div class="chat-body">
                        <div class="chat-name">${esc(name)}</div>
                        <div class="chat-msg">${esc(memberNames)}</div>
                    </div>
                    <div class="chat-side"><span class="chat-time">${time}</span>${badge}</div>
                </div>`;
        }).join('');
    } catch (e) {
        body.innerHTML = '<div class="empty-note">채팅 목록을 불러오지 못했습니다.</div>';
    }
}

loadWelcomeCard();
loadMailSummary();
loadRecentChats();
