/* codingtest.js — 코딩테스트 문제 목록 페이지 */

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error(json.message || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

function parseJwt(t) {
    try { return JSON.parse(atob(t.split('.')[1])); } catch { return {}; }
}

const DIFFICULTY_LABEL = {
    BEGINNER: '입문',
    BASIC: '초급',
    INTERMEDIATE: '중급',
    ADVANCED: '고급',
};

const state = {
    problems: [],
    filtered: [],
    difficulty: '',
};

const problemBody     = document.getElementById('problemBody');
const searchInput     = document.getElementById('searchInput');
const itemsCount      = document.getElementById('itemsCount');
const btnCreate       = document.getElementById('btnCreateProblem');
const difficultyTabs  = document.getElementById('difficultyTabs');

function isAdmin() {
    const payload = parseJwt(getToken() || '');
    return payload.role === 'ADMIN' || payload.role === 'SUPERADMIN';
}

function formatDate(iso) {
    if (!iso) return '-';
    try {
        return new Date(iso.endsWith('Z') ? iso : iso + 'Z')
            .toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
    } catch { return iso; }
}

function renderTable() {
    if (state.filtered.length === 0) {
        problemBody.innerHTML = '<tr><td colspan="5" class="state-cell">등록된 문제가 없습니다.</td></tr>';
        itemsCount.textContent = '';
        return;
    }
    itemsCount.textContent = `${state.filtered.length}건`;
    problemBody.innerHTML = state.filtered.map(p => `
        <tr class="problem-row" data-id="${esc(p.problem_id)}">
            <td>${esc(p.title)}</td>
            <td><span class="difficulty-pill ${esc(p.difficulty)}">${esc(DIFFICULTY_LABEL[p.difficulty] || p.difficulty)}</span></td>
            <td>${p.time_limit_ms != null ? esc(String(p.time_limit_ms)) + ' ms' : '-'}</td>
            <td>${p.memory_limit_mb != null ? esc(String(p.memory_limit_mb)) + ' MB' : '-'}</td>
            <td>${formatDate(p.created_at)}</td>
        </tr>
    `).join('');
    problemBody.querySelectorAll('.problem-row').forEach(row => {
        row.addEventListener('click', () => {
            window.location.href = `/coding-test/${row.dataset.id}`;
        });
    });
}

function applySearch() {
    const q = searchInput.value.trim().toLowerCase();
    state.filtered = q
        ? state.problems.filter(p => p.title.toLowerCase().includes(q))
        : state.problems.slice();
    renderTable();
}

let loadRequestSeq = 0;

async function loadProblems() {
    const seq = ++loadRequestSeq;
    problemBody.innerHTML = '<tr><td colspan="5" class="state-cell">불러오는 중...</td></tr>';
    itemsCount.textContent = '';
    try {
        const qs = state.difficulty ? `?difficulty=${encodeURIComponent(state.difficulty)}` : '';
        const result = await apiJSON(`/api/coding-test/problems${qs}`);
        if (seq !== loadRequestSeq) return; // 더 최신 요청이 이미 진행 중이면 이 응답은 버린다
        state.problems = result || [];
        applySearch();
    } catch (e) {
        if (seq !== loadRequestSeq) return;
        problemBody.innerHTML = `<tr><td colspan="5" class="state-cell">불러오기 실패: ${esc(e.message)}</td></tr>`;
    }
}

// ── 문제 출제 모달 ──────────────────────────────────────────────

function openModal(id)  { document.getElementById(id).removeAttribute('hidden'); }
function closeModal(id) { document.getElementById(id).setAttribute('hidden', ''); }

let tcCounter = 0;

function addTestCaseRow(prefill) {
    tcCounter++;
    const idx = tcCounter;
    const wrap = document.createElement('div');
    wrap.className = 'test-case-row';
    wrap.dataset.idx = idx;
    wrap.innerHTML = `
        <div class="test-case-row-head">
            <span>테스트케이스 #${idx}</span>
            <button type="button" class="btn-remove-tc">삭제</button>
        </div>
        <div class="test-case-fields">
            <textarea class="tc-input" rows="3" placeholder="입력"></textarea>
            <textarea class="tc-output" rows="3" placeholder="기대 출력"></textarea>
        </div>
        <label class="test-case-sample-toggle">
            <input type="checkbox" class="tc-sample">
            공개 샘플로 노출 (체크 안 하면 히든 테스트케이스)
        </label>
    `;
    wrap.querySelector('.btn-remove-tc').addEventListener('click', () => wrap.remove());
    document.getElementById('testCaseList').appendChild(wrap);
}

function resetCreateModal() {
    document.getElementById('inputTitle').value = '';
    document.getElementById('inputDescription').value = '';
    document.getElementById('inputDifficulty').value = 'BEGINNER';
    document.getElementById('inputTimeLimit').value = 2000;
    document.getElementById('inputMemoryLimit').value = 256;
    document.getElementById('createModalErr').textContent = '';
    document.getElementById('testCaseList').innerHTML = '';
    tcCounter = 0;
    addTestCaseRow();
    addTestCaseRow();
}

async function saveProblem() {
    const errEl = document.getElementById('createModalErr');
    errEl.textContent = '';

    const title = document.getElementById('inputTitle').value.trim();
    const description = document.getElementById('inputDescription').value.trim();
    const difficulty = document.getElementById('inputDifficulty').value;
    const timeLimitMs = parseInt(document.getElementById('inputTimeLimit').value, 10) || 2000;
    const memoryLimitMb = parseInt(document.getElementById('inputMemoryLimit').value, 10) || 256;

    const testCases = Array.from(document.querySelectorAll('.test-case-row')).map(row => ({
        input: row.querySelector('.tc-input').value,
        expectedOutput: row.querySelector('.tc-output').value,
        isSample: row.querySelector('.tc-sample').checked,
    }));

    if (!title) { errEl.textContent = '제목을 입력하세요.'; return; }
    if (!description) { errEl.textContent = '지문을 입력하세요.'; return; }
    if (testCases.length === 0) { errEl.textContent = '테스트케이스를 최소 1개 추가하세요.'; return; }
    if (testCases.some(tc => !tc.input.trim() && !tc.expectedOutput.trim())) {
        errEl.textContent = '비어있는 테스트케이스가 있습니다.';
        return;
    }

    const btn = document.getElementById('btnSaveProblem');
    btn.disabled = true;
    try {
        await apiJSON('/api/coding-test/problems', {
            method: 'POST',
            body: JSON.stringify({ title, description, difficulty, timeLimitMs, memoryLimitMb, testCases }),
        });
        closeModal('createModal');
        showToast('문제가 등록되었습니다.', 'success');
        loadProblems();
    } catch (e) {
        errEl.textContent = e.message;
    } finally {
        btn.disabled = false;
    }
}

// ── 초기화 ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    if (isAdmin()) {
        btnCreate.hidden = false;
        btnCreate.addEventListener('click', () => {
            resetCreateModal();
            openModal('createModal');
        });
    }

    document.getElementById('btnAddTestCase').addEventListener('click', () => addTestCaseRow());
    document.getElementById('btnSaveProblem').addEventListener('click', saveProblem);

    document.querySelectorAll('[data-close]').forEach(btn => {
        btn.addEventListener('click', () => closeModal(btn.dataset.close));
    });
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.setAttribute('hidden', ''); });
    });
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal-overlay:not([hidden])').forEach(el => el.setAttribute('hidden', ''));
    });

    searchInput.addEventListener('input', applySearch);

    difficultyTabs.querySelectorAll('.difficulty-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            difficultyTabs.querySelector('.difficulty-tab.active')?.classList.remove('active');
            tab.classList.add('active');
            state.difficulty = tab.dataset.difficulty;
            loadProblems();
        });
    });

    loadProblems();
});
