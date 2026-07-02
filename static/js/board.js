(function () {
    'use strict';

    /* ── 상태 ─────────────────────────────────────────────── */
    var allBoards      = [];
    var isAdmin        = false;
    var canCreateBoard = false;   /* RBAC BOARD CREATE 권한 */
    var canUpdateBoard = false;   /* RBAC BOARD UPDATE 권한 */
    var canDeleteBoard = false;   /* RBAC BOARD DELETE 권한 */
    var editingBoardId = null;
    var deletingBoardId = null;
    var myDeptId       = null;
    var myDeptName     = null;
    var deptMap        = {};   /* department_id → department_name */

    /* ── DOM ─────────────────────────────────────────────── */
    var grid         = document.getElementById('boardGrid');
    var searchInput  = document.getElementById('searchInput');
    var btnAdd       = document.getElementById('btnAddBoard');
    var btnRefresh   = document.getElementById('btnRefresh');
    var boardModalEl    = document.getElementById('boardModal');
    var boardModalTitle = document.getElementById('boardModalTitle');
    var inputName       = document.getElementById('inputBoardName');
    var inputType       = document.getElementById('inputBoardType');
    var inputDeptId     = document.getElementById('inputDeptId');
    var inputIsPublic   = document.getElementById('inputIsPublic');
    var inputReqApproval = document.getElementById('inputRequiresApproval');
    var inputPurpose     = document.getElementById('inputApprovalPurpose');
    var fieldDept        = document.getElementById('fieldDepartment');
    var fieldPurpose     = document.getElementById('fieldApprovalPurpose');
    var deptDisplay      = document.getElementById('deptDisplay');
    var boardModalErr    = document.getElementById('boardModalErr');
    var btnSaveBoard     = document.getElementById('btnSaveBoard');
    var deleteBoardMsg   = document.getElementById('deleteBoardMsg');
    var deleteBoardErr   = document.getElementById('deleteBoardErr');
    var btnConfirmDel    = document.getElementById('btnConfirmDeleteBoard');

    /* ── 아이콘·레이블 매핑 ────────────────────────────────── */
    var TYPE_ICONS   = { FREE: '💬', NOTICE: '📢', DEPARTMENT: '🏢', DATA_ROOM: '📁' };
    var TYPE_LABELS  = { FREE: '자유', NOTICE: '공지', DEPARTMENT: '부서', DATA_ROOM: '자료실' };

    /* ── JWT에서 role 추출 ────────────────────────────────── */
    function getRole() {
        var token = getToken();
        if (!token) return null;
        try {
            var payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
            return payload.role || null;
        } catch (_) { return null; }
    }

    /* ── 내 부서 정보 조회 ───────────────────────────────── */
    async function fetchMyDeptInfo() {
        try {
            var results = await Promise.all([
                apiFetch('/api/member/me'),
                apiFetch('/api/member/departments'),
            ]);
            var meRes   = results[0];
            var deptRes = results[1];

            if (meRes && meRes.ok) {
                var me = (await meRes.json()).result || {};
                myDeptId = me.department_id || null;
            }
            if (deptRes && deptRes.ok) {
                var depts = (await deptRes.json()).result || [];
                depts.forEach(function (d) { deptMap[d.department_id] = d.department_name; });
                myDeptName = myDeptId ? (deptMap[myDeptId] || myDeptId) : '—';
            }
        } catch (_) { /* 부서 정보 조회 실패 시 무시 */ }
    }

    /* ── 게시판 목록 조회 ─────────────────────────────────── */
    async function fetchBoards() {
        try {
            var res = await apiFetch('/api/board/boards');
            if (!res || !res.ok) {
                showToast('게시판 목록 조회 실패', 'error');
                grid.innerHTML = '<p class="state-cell">불러오기 실패</p>';
                return;
            }
            var json = await res.json();
            allBoards = json.result || [];
            renderGrid(allBoards);
        } catch (e) {
            showToast('게시판 조회 오류', 'error');
            grid.innerHTML = '<p class="state-cell">불러오기 실패</p>';
        } finally { /* nothing */ }
    }

    /* ── 카드 그리드 렌더링 ───────────────────────────────── */
    function renderGrid(boards) {
        if (!boards.length) {
            grid.innerHTML = '<p class="state-cell">게시판이 없습니다.</p>';
            return;
        }
        grid.innerHTML = '';
        boards.forEach(function (b) {
            var card = document.createElement('div');
            card.className = 'board-card';

            /* 편집/삭제 버튼: 관리자 또는 RBAC 권한 보유자에게 표시 */
            var editBtn = (isAdmin || canUpdateBoard)
                ? '<button class="act-btn btn-edit-board" data-id="' + esc(b.boardId) + '">편집</button>'
                : '';
            var delBtn  = (isAdmin || canDeleteBoard)
                ? '<button class="act-btn act-del btn-del-board" data-id="' + esc(b.boardId) + '">삭제</button>'
                : '';
            var adminHtml = (editBtn || delBtn)
                ? '<div class="board-card-actions">' + editBtn + delBtn + '</div>'
                : '';

            card.innerHTML =
                '<div class="board-card-band band-' + esc(b.boardType) + '"></div>'
              + '<div class="board-card-body">'
              +   '<div class="board-card-icon icon-' + esc(b.boardType) + '">'
              +     (TYPE_ICONS[b.boardType] || '📋')
              +   '</div>'
              +   '<div class="board-card-title"></div>'
              +   '<div class="board-card-desc"></div>'
              + (b.requiresApproval && b.approvers && b.approvers.length
                  ? '<div class="board-card-approver"></div>'
                  : '')
              + '</div>'
              + '<div class="board-card-footer">'
              +   '<div>'
              +     '<span class="board-type-badge type-' + esc(b.boardType) + '">'
              +       esc(TYPE_LABELS[b.boardType] || b.boardType)
              +     '</span>'
              + (b.requiresApproval ? ' <span class="board-type-badge badge-approval">승인제</span>' : '')
              +   '</div>'
              +   adminHtml
              + '</div>';

            /* XSS 방지: textContent 사용 */
            card.querySelector('.board-card-title').textContent = b.boardName;
            card.querySelector('.board-card-desc').textContent =
                b.approvalPurpose || (TYPE_LABELS[b.boardType] || '') + ' 게시판';
            var approverEl = card.querySelector('.board-card-approver');
            if (approverEl) {
                approverEl.textContent = '승인자: ' + (b.approvers || []).join(', ');
            }

            /* 카드 클릭 → 게시글 목록 (이름 기반 URL) */
            card.addEventListener('click', function (e) {
                if (e.target.closest('.act-btn')) return;
                window.location.href = '/board/' + encodeURIComponent(b.boardName);
            });

            grid.appendChild(card);
        });

        /* 관리자 버튼 이벤트 */
        grid.querySelectorAll('.btn-edit-board').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                openEditModal(btn.dataset.id);
            });
        });
        grid.querySelectorAll('.btn-del-board').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                openDeleteModal(btn.dataset.id);
            });
        });
    }

    /* ── 검색 필터 ────────────────────────────────────────── */
    function filterBoards() {
        var q = searchInput.value.trim().toLowerCase();
        renderGrid(q ? allBoards.filter(function (b) {
            return b.boardName.toLowerCase().includes(q);
        }) : allBoards);
    }

    /* ── 생성/수정 모달 ───────────────────────────────────── */
    function openCreateModal() {
        editingBoardId = null;
        boardModalTitle.textContent = '게시판 추가';
        inputName.value = '';
        inputType.value = 'FREE';
        /* 부서 정보: 본인 부서 자동 설정 (수정 불가) */
        inputDeptId.value = myDeptId || '';
        deptDisplay.textContent = myDeptName || '—';
        inputIsPublic.checked = true;
        inputReqApproval.checked = false;
        inputPurpose.value = '';
        boardModalErr.textContent = '';
        fieldDept.hidden = true;
        fieldPurpose.hidden = true;
        openModal('boardModal');
    }

    function openEditModal(boardId) {
        var b = allBoards.find(function (x) { return x.boardId === boardId; });
        if (!b) return;
        editingBoardId = boardId;
        boardModalTitle.textContent = '게시판 수정';
        inputName.value = b.boardName;
        inputType.value = b.boardType;
        /* 부서: 기존 boardId 유지, 이름 표시 */
        inputDeptId.value = b.departmentId || myDeptId || '';
        deptDisplay.textContent = (b.departmentId ? (deptMap[b.departmentId] || b.departmentId) : myDeptName) || '—';
        inputIsPublic.checked = b.isPublic !== false;
        inputReqApproval.checked = !!b.requiresApproval;
        inputPurpose.value = b.approvalPurpose || '';
        boardModalErr.textContent = '';
        fieldDept.hidden = b.boardType !== 'DEPARTMENT';
        fieldPurpose.hidden = !b.requiresApproval;
        openModal('boardModal');
    }

    /* ── 게시판 저장 ──────────────────────────────────────── */
    async function saveBoard() {
        var name = inputName.value.trim();
        if (!name) { boardModalErr.textContent = '게시판 이름을 입력하세요.'; return; }

        /* 중복 이름 체크 */
        var dup = allBoards.find(function (b) {
            return b.boardName === name && b.boardId !== editingBoardId;
        });
        if (dup) { boardModalErr.textContent = '이미 같은 이름의 게시판이 있습니다.'; return; }

        var body = {
            boardName: name,
            boardType: inputType.value,
            departmentId: inputDeptId.value.trim() || null,
            isPublic: inputIsPublic.checked,
            requiresApproval: inputReqApproval.checked,
            approvalPurpose: inputPurpose.value.trim() || null,
        };
        try {
            btnSaveBoard.disabled = true;
            var url    = editingBoardId ? '/api/board/boards/' + editingBoardId : '/api/board/boards';
            var method = editingBoardId ? 'PUT' : 'POST';
            var res = await apiFetch(url, { method: method, body: JSON.stringify(body) });
            if (!res || !res.ok) {
                var err = res ? await res.json() : null;
                boardModalErr.textContent = (err && err.message) || '저장에 실패했습니다.';
                return;
            }
            closeModal('boardModal');
            showToast(editingBoardId ? '게시판이 수정되었습니다.' : '게시판이 생성되었습니다.', 'success');
            await fetchBoards();
        } catch (_) {
            boardModalErr.textContent = '오류가 발생했습니다.';
        } finally {
            btnSaveBoard.disabled = false;
        }
    }

    /* ── 게시판 삭제 ──────────────────────────────────────── */
    function openDeleteModal(boardId) {
        var b = allBoards.find(function (x) { return x.boardId === boardId; });
        if (!b) return;
        deletingBoardId = boardId;
        deleteBoardMsg.textContent = '"' + b.boardName + '" 게시판을 삭제하시겠습니까?';
        deleteBoardErr.textContent = '';
        openModal('deleteBoardModal');
    }

    async function deleteBoard() {
        if (!deletingBoardId) return;
        try {
            btnConfirmDel.disabled = true;
            var res = await apiFetch('/api/board/boards/' + deletingBoardId, { method: 'DELETE' });
            if (!res || !res.ok) {
                var err = res ? await res.json() : null;
                deleteBoardErr.textContent = (err && err.message) || '삭제에 실패했습니다.';
                return;
            }
            closeModal('deleteBoardModal');
            showToast('게시판이 삭제되었습니다.', 'success');
            await fetchBoards();
        } catch (_) {
            deleteBoardErr.textContent = '오류가 발생했습니다.';
        } finally {
            btnConfirmDel.disabled = false;
        }
    }

    /* ── 모달 공통 ────────────────────────────────────────── */
    function openModal(id)  { document.getElementById(id).removeAttribute('hidden'); }
    function closeModal(id) { document.getElementById(id).setAttribute('hidden', ''); }

    document.querySelectorAll('[data-close]').forEach(function (el) {
        el.addEventListener('click', function () { closeModal(el.dataset.close); });
    });
    document.querySelectorAll('.modal-overlay').forEach(function (ov) {
        ov.addEventListener('click', function (e) { if (e.target === ov) closeModal(ov.id); });
    });

    /* ── 동적 필드 토글 ───────────────────────────────────── */
    inputType.addEventListener('change', function () {
        fieldDept.hidden = inputType.value !== 'DEPARTMENT';
    });
    inputReqApproval.addEventListener('change', function () {
        fieldPurpose.hidden = !inputReqApproval.checked;
    });

    /* ── 이벤트 바인딩 ────────────────────────────────────── */
    btnAdd.addEventListener('click', openCreateModal);
    btnRefresh.addEventListener('click', fetchBoards);
    btnSaveBoard.addEventListener('click', saveBoard);
    btnConfirmDel.addEventListener('click', deleteBoard);
    searchInput.addEventListener('input', filterBoards);

    /* ── 초기화 (bfcache 대응: readyState 확인) ─────────────── */
    /* ── RBAC 권한 조회 ──────────────────────────────────────── */
    async function fetchMyPermissions() {
        try {
            var res = await apiFetch('/api/board/my-permissions');
            if (!res || !res.ok) return;
            var json = await res.json();
            var p = json.result || {};
            canCreateBoard = !!p.boardCreate;
            canUpdateBoard = !!p.boardUpdate;
            canDeleteBoard = !!p.boardDelete;
        } catch (_) { /* 권한 조회 실패 시 기본값 유지 */ }
        finally { /* nothing */ }
    }

    async function init() {
        isAdmin = getRole() === 'ADMIN';
        await Promise.all([fetchMyDeptInfo(), fetchMyPermissions()]);
        /* 게시판 추가 버튼: BOARD CREATE 권한 보유 시 표시 (관리자 포함) */
        btnAdd.hidden = !canCreateBoard;
        await fetchBoards();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
