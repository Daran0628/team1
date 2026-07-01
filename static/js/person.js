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
const deptFilter = document.getElementById('deptFilter');
const personBody = document.getElementById('personBody');
const itemsCount = document.getElementById('itemsCount');

let debounceTimer = null;

async function loadDepartments() {
    try {
        const departments = await apiJSON('/api/member/departments');
        deptFilter.innerHTML = '<option value="">전체 부서</option>' +
            departments.map(d => `<option value="${esc(d.department_id)}">${esc(d.department_name)}</option>`).join('');
    } catch (e) {
        showToast(e.message || '부서 목록을 불러오지 못했습니다.', 'error');
    }
}

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
    const departmentId = deptFilter.value;

    if (!keyword && !departmentId) {
        personBody.innerHTML = '<tr><td colspan="4" class="state-cell">이름을 입력하거나 부서를 선택해 검색하세요.</td></tr>';
        itemsCount.textContent = '';
        return;
    }

    personBody.innerHTML = '<tr><td colspan="4" class="state-cell">검색 중...</td></tr>';

    const params = new URLSearchParams();
    if (keyword) params.set('keyword', keyword);
    if (departmentId) params.set('department_id', departmentId);

    try {
        const results = await apiJSON(`/api/member/search?${params.toString()}`);
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

deptFilter.addEventListener('change', runSearch);

loadDepartments();
