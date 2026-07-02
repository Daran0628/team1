(function () {
    'use strict';

    const form        = document.getElementById('loginForm');
    const accountInput = document.getElementById('accountId');
    const passwordInput = document.getElementById('password');
    const errorMsg    = document.getElementById('errorMsg');
    const submitBtn   = document.getElementById('submitBtn');
    const btnText     = document.getElementById('btnText');
    const btnLoader   = document.getElementById('btnLoader');

    // ── 텍스트 출력은 반드시 textContent 사용 ──
    function showError(msg) {
        // innerHTML 절대 사용 금지 — textContent는 HTML 태그를 문자 그대로 출력
        errorMsg.textContent = typeof msg === 'string' ? msg : '오류가 발생했습니다.';
    }

    function clearError() {
        errorMsg.textContent = '';
    }

    function setLoading(on) {
        submitBtn.disabled = on;
        btnText.hidden     = on;
        btnLoader.hidden   = !on;
    }

    // ── 클라이언트 입력 검증 ──────────────────────────
    function validate(accountId, password) {
        if (!accountId || accountId.trim().length === 0) return '아이디를 입력해주세요.';
        if (accountId.length > 50)   return '아이디는 50자 이하여야 합니다.';
        if (!password || password.length === 0) return '비밀번호를 입력해주세요.';
        if (password.length > 100)   return '비밀번호는 100자 이하여야 합니다.';
        return null;
    }

    // ── 로그인 요청 ───────────────────────────────────
    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        clearError();

        const accountId = accountInput.value.trim();
        const password  = passwordInput.value;       // 비밀번호 trim 금지

        const err = validate(accountId, password);
        if (err) {
            showError(err);
            accountInput.classList.toggle('invalid', !accountId);
            passwordInput.classList.toggle('invalid', !password);
            return;
        }

        setLoading(true);

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // JSON.stringify 사용 — 문자열 연결로 JSON 만들면 Injection 위험
                body: JSON.stringify({ accountId, password }),
                credentials: 'same-origin', // refreshToken 쿠키 포함
            });

            const data = await res.json();

            if (!res.ok || !data.isSuccess) {
                // 서버 응답 메시지도 textContent로 표시 (서버 응답에 태그가 있어도 안전)
                showError(data.message || '로그인에 실패했습니다.');
                return;
            }

            // access_token 타입 검증 후 sessionStorage 저장
            // - sessionStorage: 탭 닫으면 자동 삭제, localStorage보다 안전
            const token = data.result?.access_token;
            if (typeof token === 'string' && token.length > 0) {
                sessionStorage.setItem('access_token', token);
            }

            const accountType = data.result?.account_type;
            if (typeof accountType === 'string' && accountType.length > 0) {
                sessionStorage.setItem('role', accountType);
            }

            // 히스토리에 로그인 페이지 남기지 않음
            window.location.replace('/');

        } catch (_) {
            showError('서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        } finally {
            setLoading(false);
        }
    });

    // ── 입력 시 에러 초기화 ──────────────────────────
    [accountInput, passwordInput].forEach(function (input) {
        input.addEventListener('input', function () {
            input.classList.remove('invalid');
            clearError();
        });
    });

}());
