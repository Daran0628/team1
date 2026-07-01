/* layout.js — 로그인 이후 공통 레이아웃 셸 (사이드바 + 상단바) 주입
 * 로드 순서: api.js → layout.js → 각 페이지 JS
 * 사용법: <div id="shellSlot"></div> 를 body 안에 두고 이 스크립트를 로드하면
 *         상단바 + 사이드바가 자동으로 그 자리에 삽입된다.
 */

const SIDEBAR_MENU = [
    { label: '대시보드',         icon: '🏠', href: '/' },
    { label: '헬프데스크(티켓)', icon: '🎧', href: null },
    { label: 'FAQ',              icon: '❓', href: null },
    { label: '공지사항',         icon: '📢', href: null },
    { label: '메일 서비스',      icon: '✉️', href: '/mail' },
    { label: 'Chatting',         icon: '💬', href: '/chat' },
    { label: '공유 스토리지',    icon: '🗂️', href: '/objstorage' },
    { label: 'VDI',              icon: '🖥️', href: '/vdi/list' },
    { label: '코딩테스트',       icon: '⌨️', href: null },
    { label: '인물 검색',        icon: '🔍', href: '/person' },
    { label: '마이페이지',       icon: '👤', href: '/mypage' },
    { label: '관리자 페이지',    icon: '⚙️', href: '/iam' },
];

function _layoutParseJwt(t) {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return {}; }
}

function _buildSidebarNav() {
    return SIDEBAR_MENU.map(item => {
        const disabled = !item.href;
        const href = item.href || '#';
        const cls = 'nav-item' + (disabled ? ' disabled' : '');
        return `<a class="${cls}" href="${href}" data-href="${item.href || ''}">` +
               `<span class="nav-icon">${item.icon}</span>` +
               `<span class="nav-label">${esc(item.label)}${disabled ? ' (준비중)' : ''}</span>` +
               `</a>`;
    }).join('');
}

function _highlightActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item[data-href]').forEach(a => {
        const target = a.getAttribute('data-href');
        if (!target) return;
        const isMatch = target === '/' ? path === '/' : path.startsWith(target);
        if (isMatch) a.classList.add('active');
    });
}

function initLayoutShell() {
    const slot = document.getElementById('shellSlot');
    if (!slot) return;

    const payload = _layoutParseJwt(getToken() || '');

    slot.innerHTML = `
        <header class="topbar">
            <div class="topbar-brand">
                <span class="brand-badge">LOGO</span>
                <span class="brand-name">NOVAworks</span>
            </div>
            <div class="topbar-user" id="topbarUser">
                <span id="topbarUserName">${esc(payload.sub || '')}</span>
                <span class="caret">⌄</span>
                <div class="user-dropdown" id="userDropdown" hidden>
                    <a href="/mypage">마이페이지</a>
                    <button id="btnShellLogout" type="button">로그아웃</button>
                </div>
            </div>
        </header>
        <aside class="sidebar">
            <nav class="sidebar-nav">${_buildSidebarNav()}</nav>
            <div class="sidebar-footer">
                <button class="nav-logout" id="btnSidebarLogout" type="button">
                    <span class="nav-icon">⎋</span><span class="nav-label">로그아웃</span>
                </button>
            </div>
        </aside>
    `;

    _highlightActiveNav();

    const topbarUser   = document.getElementById('topbarUser');
    const userDropdown = document.getElementById('userDropdown');
    topbarUser.addEventListener('click', (e) => {
        e.stopPropagation();
        userDropdown.hidden = !userDropdown.hidden;
    });
    document.addEventListener('click', () => { userDropdown.hidden = true; });

    async function doLogout() {
        try { await apiFetch('/api/auth/logout'); } catch (_) {}
        sessionStorage.removeItem('access_token');
        window.location.replace('/login');
    }
    document.getElementById('btnShellLogout').addEventListener('click', doLogout);
    document.getElementById('btnSidebarLogout').addEventListener('click', doLogout);
}

initLayoutShell();
