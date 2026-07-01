(async () => {
    // ── Auth ──────────────────────────────────────────────────
    if (!getToken()) {
        const ok = await tryRefresh();
        if (!ok) { window.location.replace('/login'); return; }
    }

    // ── Date ──────────────────────────────────────────────────
    const today = new Intl.DateTimeFormat('ko-KR', {
        timeZone: 'Asia/Seoul',
        year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
    }).format(new Date());
    document.getElementById('welcomeDate').textContent = today;

    // ── User info ─────────────────────────────────────────────
    try {
        const res  = await apiFetch('/api/member/me');
        const data = await res.json();
        if (data.isSuccess && data.result) {
            const name    = data.result.name_ko || data.result.account_id || '';
            const initial = name.slice(0, 1) || '?';

            document.getElementById('welcomeName').textContent  = name;
            document.getElementById('userName').textContent     = name;
            document.getElementById('topAvatar').textContent    = initial;
            document.getElementById('sidebarAvatar').textContent = initial;
            document.getElementById('sidebarName').textContent  = name;
        }
    } catch (_) {}

    // ── Stats from real APIs ───────────────────────────────────
    // 메일 미확인 (mockup — 실제 API 연동 시 교체)
    setStatMockup('statMail', 2, 'mailBadge');
    setStatMockup('statChat', 5, 'chatBadge');

    // 버킷 수 — 실제 API
    try {
        const res  = await apiFetch('/api/storage/buckets');
        const data = await res.json();
        if (data.isSuccess && Array.isArray(data.result)) {
            document.getElementById('statBuckets').textContent = data.result.length;
        }
    } catch (_) {
        document.getElementById('statBuckets').textContent = '—';
    }

    // ── Logout ────────────────────────────────────────────────
    document.getElementById('btnLogout').addEventListener('click', async () => {
        try { await apiFetch('/api/auth/logout'); } catch (_) {}
        sessionStorage.removeItem('access_token');
        window.location.replace('/login');
    });

    function setStatMockup(statId, count, badgeId) {
        document.getElementById(statId).textContent = count;
        const badge = document.getElementById(badgeId);
        if (badge && count > 0) {
            badge.textContent = count;
            badge.hidden = false;
        }
    }
})();
