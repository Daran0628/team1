(function () {
    function getToken() { return sessionStorage.getItem('access_token'); }

    async function tryRefresh() {
        try {
            var res = await fetch('/api/auth/refresh', { method: 'GET', credentials: 'include' });
            if (!res.ok) return false;
            var json = await res.json();
            var t = json && json.result && json.result.access_token;
            if (!t) return false;
            sessionStorage.setItem('access_token', t);
            return true;
        } catch (_) { return false; }
    }

    async function apiFetch(url) {
        var token = getToken();
        if (!token) {
            var ok = await tryRefresh();
            if (!ok) { window.location.replace('/login'); return null; }
            token = getToken();
        }
        var res = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
        });
        if (res.status === 401) {
            var ok2 = await tryRefresh();
            if (!ok2) { window.location.replace('/login'); return null; }
            res = await fetch(url, {
                headers: { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json' }
            });
        }
        if (!res.ok) return null;
        var json = await res.json();
        return json.result;
    }

    function setStat(id, count) {
        var el = document.getElementById(id);
        if (!el) return;
        el.textContent = count !== null ? count : '?';
        el.classList.remove('stat-loading');
    }

    async function loadStats() {
        var results = await Promise.allSettled([
            apiFetch('/api/rbac/role'),
            apiFetch('/api/group'),
            apiFetch('/api/rbac/permission'),
        ]);

        var roles  = results[0].status === 'fulfilled' && Array.isArray(results[0].value)
            ? results[0].value.length : null;
        var groups = results[1].status === 'fulfilled' && Array.isArray(results[1].value)
            ? results[1].value.length : null;
        var perms  = results[2].status === 'fulfilled' && Array.isArray(results[2].value)
            ? results[2].value.length : null;

        setStat('statRoles',  roles);
        setStat('statGroups', groups);
        setStat('statPerms',  perms);
    }

    document.addEventListener('DOMContentLoaded', loadStats);
}());
