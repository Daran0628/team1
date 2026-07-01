/* person.js — 인물 검색 페이지 로직 */

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error(json.message || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

const searchInput = document.getElementById('searchInput');
const personBody = document.getElementById('personBody');
const itemsCount = document.getElementById('itemsCount');

let debounceTimer = null;

function renderTable(results) {
    if (!results || results.length === 0) {
        personBody.innerHTML = '<tr><td colspan="4" class="state-cell">검색 결과가 없습니다.</td></tr>';
        itemsCount.textContent = '';
        return;
    }

    personBody.innerHTML = results.map(p => `
        <tr>
            <td>${esc(p.name_ko)}</td>
            <td>${esc(p.department_name)}</td>
            <td>${esc(p.email)}</td>
            <td>${esc(p.department_phone || '-')}</td>
        </tr>
    `).join('');

    itemsCount.textContent = `${results.length}건`;
}

async function runSearch() {
    const keyword = searchInput.value.trim();

    if (!keyword) {
        personBody.innerHTML = '<tr><td colspan="4" class="state-cell">이름을 입력해 검색하세요.</td></tr>';
        itemsCount.textContent = '';
        return;
    }

    personBody.innerHTML = '<tr><td colspan="4" class="state-cell">검색 중...</td></tr>';

    try {
        const results = await apiJSON(`/api/member/search?keyword=${encodeURIComponent(keyword)}`);
        renderTable(results);
    } catch (e) {
        personBody.innerHTML = '<tr><td colspan="4" class="state-cell">검색 중 오류가 발생했습니다.</td></tr>';
        showToast(e.message || '검색 실패', 'error');
    }
}

searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 300);
});
