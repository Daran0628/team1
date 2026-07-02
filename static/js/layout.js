/* layout.js — 로그인 이후 공통 레이아웃 셸 (사이드바 + 상단바) 주입
 * 로드 순서: api.js → layout.js → 각 페이지 JS
 * 사용법: <div id="shellSlot"></div> 를 body 안에 두고 이 스크립트를 로드하면
 *         상단바 + 사이드바가 자동으로 그 자리에 삽입된다.
 */

const SIDEBAR_MENU = [
    { label: '대시보드',         icon: 'fa-solid fa-house',            href: '/' },
    { label: '헬프데스크(티켓)', icon: 'fa-solid fa-headset',          href: null },
    { label: 'FAQ',              icon: 'fa-solid fa-circle-question',  href: null },
    { label: '공지사항',         icon: 'fa-solid fa-bullhorn',         href: null },
    { label: '메일 서비스',      icon: 'fa-solid fa-envelope',         href: '/mail' },
    { label: 'Chatting',         icon: 'fa-solid fa-comment-dots',     href: '/chat' },
    { label: '공유 스토리지',    icon: 'fa-solid fa-box-archive',      href: '/objstorage' },
    { label: 'VDI',              icon: 'fa-solid fa-display',          href: '/vdi/list' },
    { label: '코딩테스트',       icon: 'fa-solid fa-code',             href: null },
    { label: '인물 검색',        icon: 'fa-solid fa-magnifying-glass', href: '/person' },
    { label: '마이페이지',       icon: 'fa-solid fa-user',             href: '/mypage' },
    { label: '관리자 페이지',    icon: 'fa-solid fa-gear',             href: '/iam' },
];

function _layoutParseJwt(t) {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return {}; }
}

function _applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

// FOUC 방지를 위해 셸을 그리기 전, 스크립트 로드 시점에 바로 적용
_applyTheme(localStorage.getItem('theme') === 'dark' ? 'dark' : 'light');

function _buildSidebarNav() {
    return SIDEBAR_MENU.map(item => {
        const disabled = !item.href;
        const href = item.href || '#';
        const cls = 'nav-item' + (disabled ? ' disabled' : '');
        return `<a class="${cls}" href="${href}" data-href="${item.href || ''}">` +
               `<span class="nav-icon"><i class="${item.icon}"></i></span>` +
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
            <div class="topbar-right">
                <button class="theme-toggle" id="themeToggle" type="button" title="라이트/다크 모드 전환"></button>
                <div class="topbar-user" id="topbarUser">
                    <span id="topbarUserName">${esc(payload.sub || '')}</span>
                    <span class="caret"><i class="fa-solid fa-chevron-down"></i></span>
                    <div class="user-dropdown" id="userDropdown" hidden>
                        <a href="/mypage">마이페이지</a>
                        <button id="btnShellLogout" type="button">로그아웃</button>
                    </div>
                </div>
            </div>
        </header>
        <aside class="sidebar">
            <nav class="sidebar-nav">${_buildSidebarNav()}</nav>
            <div class="sidebar-footer">
                <button class="nav-logout" id="btnSidebarLogout" type="button">
                    <span class="nav-icon"><i class="fa-solid fa-right-from-bracket"></i></span><span class="nav-label">로그아웃</span>
                </button>
            </div>
        </aside>
    `;

    _highlightActiveNav();

    const themeToggle = document.getElementById('themeToggle');
    function _renderThemeToggleIcon() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        themeToggle.innerHTML = `<i class="fa-solid ${isDark ? 'fa-sun' : 'fa-moon'}"></i>`;
    }
    _renderThemeToggleIcon();
    themeToggle.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        _applyTheme(isDark ? 'light' : 'dark');
        _renderThemeToggleIcon();
    });

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
