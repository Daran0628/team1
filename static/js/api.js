/* api.js — 사이트 전역 인증·유틸리티 공유 모듈
 * 로드 순서: api.js → 각 페이지 JS (rbac.js, group.js, permission.js, objstorage.js, iam.js, chat.js, chatroom.js)
 * apiJSON 은 페이지별 동작이 달라 각 파일에서 별도 정의
 */

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

function showToast(msg, type) {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => { t.classList.add('toast-out'); setTimeout(() => t.remove(), 300); }, 3000);
}

function esc(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const escText = esc;
