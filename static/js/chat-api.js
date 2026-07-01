/* chat-api.js — chat.js · chatroom.js 공통 유틸리티
 * getToken / tryRefresh / fmtTime 은 각 페이지 파일에서 전역 정의됨
 * 로드 순서: chat-api.js → chat.js (또는 chatroom.js)
 */

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

function showToast(msg, type) {
    const c = document.getElementById('toastContainer');
    const t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'info');
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => { t.classList.add('toast-out'); setTimeout(() => t.remove(), 300); }, 3000);
}

function esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
