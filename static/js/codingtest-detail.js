/* codingtest-detail.js — 코딩테스트 문제 상세 + 코드 제출 페이지 */

async function apiJSON(url, options) {
    const res = await apiFetch(url, options);
    if (!res) return null;
    const json = await res.json();
    if (!res.ok || json.isSuccess === false) {
        throw new Error(json.message || 'API error');
    }
    return json.result !== undefined ? json.result : json;
}

const PROBLEM_ID = window.location.pathname.split('/').filter(Boolean).pop();

const DIFFICULTY_LABEL = {
    BEGINNER: '입문',
    BASIC: '초급',
    INTERMEDIATE: '중급',
    ADVANCED: '고급',
};

const STATUS_LABEL = {
    PENDING: '대기중',
    JUDGING: '채점중',
    ACCEPTED: '정답',
    WRONG_ANSWER: '오답',
    TIME_LIMIT_EXCEEDED: '시간초과',
    RUNTIME_ERROR: '런타임에러',
    COMPILE_ERROR: '컴파일에러',
};

function formatDateTime(iso) {
    if (!iso) return '-';
    try {
        return new Date(iso.endsWith('Z') ? iso : iso + 'Z')
            .toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
}

async function loadProblem() {
    try {
        const problem = await apiJSON(`/api/coding-test/problems/${encodeURIComponent(PROBLEM_ID)}`);
        document.getElementById('pageTitle').textContent = problem.title;
        document.getElementById('crumbTitle').textContent = problem.title;
        document.title = `${problem.title} — 코딩테스트`;

        document.getElementById('problemMeta').innerHTML = `
            <span class="difficulty-pill ${esc(problem.difficulty)}">${esc(DIFFICULTY_LABEL[problem.difficulty] || problem.difficulty)}</span>
            <span class="ct-limit-pill">⏱ ${esc(String(problem.time_limit_ms))} ms</span>
            <span class="ct-limit-pill">💾 ${esc(String(problem.memory_limit_mb))} MB</span>
        `;
        document.getElementById('problemDescription').textContent = problem.description;

        const sampleList = document.getElementById('sampleList');
        if (!problem.sample_test_cases || problem.sample_test_cases.length === 0) {
            sampleList.innerHTML = '<div class="state-cell">공개된 샘플 테스트케이스가 없습니다.</div>';
        } else {
            sampleList.innerHTML = problem.sample_test_cases.map((tc, i) => `
                <div class="ct-sample-item">
                    <div class="ct-sample-cols">
                        <div class="ct-sample-col">
                            <div class="ct-sample-col-label">입력 예제 ${i + 1}</div>
                            <pre>${esc(tc.input)}</pre>
                        </div>
                        <div class="ct-sample-col">
                            <div class="ct-sample-col-label">출력 예제 ${i + 1}</div>
                            <pre>${esc(tc.expected_output)}</pre>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    } catch (e) {
        document.getElementById('pageTitle').textContent = '문제를 불러올 수 없습니다';
        document.getElementById('problemDescription').textContent = e.message;
        showToast(e.message, 'error');
    }
}

async function loadSubmissions() {
    const body = document.getElementById('submissionBody');
    try {
        const list = await apiJSON(`/api/coding-test/submissions?problemId=${encodeURIComponent(PROBLEM_ID)}`);
        if (!list || list.length === 0) {
            body.innerHTML = '<tr><td colspan="4" class="state-cell">아직 제출 내역이 없습니다.</td></tr>';
            return;
        }
        body.innerHTML = list.map(s => `
            <tr>
                <td>${formatDateTime(s.created_at)}</td>
                <td>${esc(s.language)}</td>
                <td><span class="status-pill ${esc(s.status)}">${esc(STATUS_LABEL[s.status] || s.status)}</span></td>
                <td>${esc(String(s.score))}</td>
            </tr>
        `).join('');
    } catch (e) {
        body.innerHTML = `<tr><td colspan="4" class="state-cell">불러오기 실패: ${esc(e.message)}</td></tr>`;
    }
}

async function submitCode() {
    const errEl   = document.getElementById('submitErr');
    const btn     = document.getElementById('btnSubmit');
    const language = document.getElementById('languageSelect').value;
    const sourceCode = document.getElementById('sourceCode').value;

    errEl.textContent = '';
    if (!sourceCode.trim()) { errEl.textContent = '제출할 코드를 입력하세요.'; return; }

    btn.disabled = true;
    try {
        await apiJSON('/api/coding-test/submissions', {
            method: 'POST',
            body: JSON.stringify({ problemId: PROBLEM_ID, language, sourceCode }),
        });
        showToast('코드가 제출되었습니다. 채점이 진행됩니다.', 'info');
        loadSubmissions();
        pollLatestSubmission();
    } catch (e) {
        errEl.textContent = e.message;
    } finally {
        btn.disabled = false;
    }
}

async function pollLatestSubmission() {
    for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 2000));
        try {
            const list = await apiJSON(`/api/coding-test/submissions?problemId=${encodeURIComponent(PROBLEM_ID)}`);
            const latest = list && list[0];
            await loadSubmissions();
            if (!latest || !['PENDING', 'JUDGING'].includes(latest.status)) return;
        } catch {
            return;
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btnSubmit').addEventListener('click', submitCode);
    loadProblem();
    loadSubmissions();
});
