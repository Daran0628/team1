(function () {
    'use strict';

    /* ── URL에서 게시판 이름 추출, boardId는 API 조회 후 할당 ── */
    var BOARD_NAME = decodeURIComponent(window.location.pathname.split('/')[2] || '');
    var BOARD_ID   = null;

    /* ── 상태 ─────────────────────────────────────────────── */
    var currentPage       = 1;
    var pageSize          = 20;
    var totalItems        = 0;
    var allPosts          = [];
    var isAdmin           = false;
    var isApprover        = false;
    var myMemberId        = null;
    var pendingOnly           = false;
    var boardRequiresApproval = false;   /* 승인제 게시판 여부 */
    var showActionsColumn     = false;   /* Actions 컬럼 표시 여부 */
    var canApprove            = false;   /* RBAC BOARD APPROVE 권한 */
    var canDeletePost         = false;   /* RBAC POST DELETE 권한 */
    var deletingPostId    = null;
    var inlineImageFiles  = [];   /* 본문 삽입용 이미지 파일 목록 */
    var inlinePrevUrls    = [];   /* ObjectURL 해제용 */

    /* ── DOM ─────────────────────────────────────────────── */
    var postsBody    = document.getElementById('postsBody');
    var pageTitle    = document.getElementById('pageTitle');
    var breadcrumb   = document.getElementById('breadcrumbBoard');
    var paginationBar = document.getElementById('paginationBar');
    var searchInput  = document.getElementById('searchInput');
    var itemsCount   = document.getElementById('itemsCount');
    var btnWrite     = document.getElementById('btnWritePost');
    var btnRefresh   = document.getElementById('btnRefresh');
    var btnPending        = document.getElementById('btnPendingOnly');
    var colActionsHeader  = document.getElementById('colActionsHeader');
    var inputTitle   = document.getElementById('inputPostTitle');
    var inputContent = document.getElementById('inputPostContent');
    var inputFiles   = document.getElementById('inputPostFiles');
    var writeModalErr    = document.getElementById('writeModalErr');
    var btnSavePost      = document.getElementById('btnSavePost');
    var deletePostErr    = document.getElementById('deletePostErr');
    var btnConfirmDel    = document.getElementById('btnConfirmDeletePost');
    var btnInsertImage   = document.getElementById('btnInsertImage');
    var inputInlineImage = document.getElementById('inputInlineImage');
    var inlinePreviewWrap = document.getElementById('inlinePreviewWrap');

    /* ── 상태 레이블 ─────────────────────────────────────── */
    var STATUS_LABELS = { DRAFT: '임시', PENDING: '대기', PUBLISHED: '게시', REJECTED: '반려' };

    /* ── 날짜 포맷 ────────────────────────────────────────── */
    function fmtDate(iso) { return iso ? iso.slice(0, 10) : ''; }

    /* ── JWT 파싱 ─────────────────────────────────────────── */
    function parseJwt() {
        var token = getToken();
        if (!token) return {};
        try {
            return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        } catch (_) { return {}; }
    }

    /* ── 게시판 정보 조회 (이름 기반, BOARD_ID 할당 포함) ───── */
    async function fetchBoardInfo() {
        try {
            var res = await apiFetch('/api/board/boards/by-name/' + encodeURIComponent(BOARD_NAME));
            if (!res || !res.ok) return;
            var json = await res.json();
            var b = json.result;
            if (!b) return;
            BOARD_ID = b.boardId;
            boardRequiresApproval = !!b.requiresApproval;
            pageTitle.textContent = b.boardName;
            breadcrumb.textContent = b.boardName;
            document.title = b.boardName + ' — 게시글';
        } catch (_) { /* nothing */ }
    }

    /* ── 게시글 목록 조회 ─────────────────────────────────── */
    async function fetchPosts() {
        try {
            var COLSPAN = showActionsColumn ? 7 : 6;
            postsBody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="state-cell">불러오는 중...</td></tr>';
            var url = '/api/board/boards/' + BOARD_ID + '/posts?page=' + currentPage + '&size=' + pageSize;
            var res = await apiFetch(url);
            if (!res || !res.ok) { showToast('게시글 목록 조회 실패', 'error'); return; }
            var json = await res.json();
            var data = json.result || {};
            allPosts   = data.items || [];
            totalItems = data.total || 0;
            itemsCount.textContent = '총 ' + totalItems + '건';
            renderPosts();
            renderPagination();
        } catch (e) {
            showToast('게시글 조회 오류', 'error');
        } finally { /* nothing */ }
    }

    /* ── 게시글 렌더링 ────────────────────────────────────── */
    function renderPosts() {
        var q = searchInput.value.trim().toLowerCase();
        var posts = pendingOnly
            ? allPosts.filter(function (p) { return p.status === 'PENDING'; })
            : allPosts;
        if (q) posts = posts.filter(function (p) { return p.title.toLowerCase().includes(q); });

        var COLSPAN = showActionsColumn ? 7 : 6;
        if (!posts.length) {
            postsBody.innerHTML = '<tr><td colspan="' + COLSPAN + '" class="state-cell">게시글이 없습니다.</td></tr>';
            return;
        }
        postsBody.innerHTML = '';
        var frag = document.createDocumentFragment();

        posts.forEach(function (p) {
            var tr = document.createElement('tr');
            tr.className = 'role-row';

            /* 승인/반려: 승인제 게시판이면서 권한 있는 경우 + PENDING 상태만 */
            var approveHtml = boardRequiresApproval
                && (isAdmin || isApprover || canApprove)
                && p.status === 'PENDING'
                ? '<button class="act-btn btn-approve" data-id="' + esc(p.postId) + '">승인</button>'
                + '<button class="act-btn act-del btn-reject" data-id="' + esc(p.postId) + '">반려</button>'
                : '';

            /* 삭제: 작성자, 관리자, 또는 RBAC POST DELETE 권한 보유자 */
            var deleteHtml = (isAdmin || p.authorAccountId === myMemberId || canDeletePost)
                ? '<button class="act-btn act-del btn-del-post" data-id="' + esc(p.postId) + '">삭제</button>'
                : '';

            /* Actions td: showActionsColumn 인 경우에만 렌더링 */
            var actionsTd = showActionsColumn
                ? '<td class="row-actions">' + (approveHtml + deleteHtml || '<span>—</span>') + '</td>'
                : '';

            tr.innerHTML =
                '<td><span class="status-badge status-' + esc(p.status) + '">'
                + esc(STATUS_LABELS[p.status] || p.status) + '</span>'
                + (p.isPinned ? ' 📌' : '') + '</td>'
              + '<td class="post-title-link role-name"></td>'
              + '<td class="role-desc author-cell"></td>'
              + '<td class="role-desc">' + esc(fmtDate(p.createdAt)) + '</td>'
              + '<td class="num-cell">' + (p.viewCount || 0) + '</td>'
              + '<td class="num-cell">' + (p.likeCount || 0) + '</td>'
              + actionsTd;

            /* textContent로 XSS 방지 */
            tr.querySelector('.post-title-link').textContent = p.title;
            tr.querySelector('.author-cell').textContent = p.authorName || '';

            /* 제목 클릭 → 상세 페이지 */
            tr.querySelector('.post-title-link').addEventListener('click', function () {
                window.location.href = '/board/' + encodeURIComponent(BOARD_NAME) + '/post/' + p.postId;
            });

            frag.appendChild(tr);
        });

        postsBody.appendChild(frag);

        /* 승인/반려/삭제 이벤트 */
        postsBody.querySelectorAll('.btn-approve').forEach(function (btn) {
            btn.addEventListener('click', function () { approvePost(btn.dataset.id); });
        });
        postsBody.querySelectorAll('.btn-reject').forEach(function (btn) {
            btn.addEventListener('click', function () { rejectPost(btn.dataset.id); });
        });
        postsBody.querySelectorAll('.btn-del-post').forEach(function (btn) {
            btn.addEventListener('click', function () { openDeleteModal(btn.dataset.id); });
        });
    }

    /* ── 페이지네이션 ─────────────────────────────────────── */
    function renderPagination() {
        var totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
        paginationBar.innerHTML =
            '<div class="page-size-wrap">'
          + '<span>페이지당</span>'
          + '<select id="pageSizeSelect">'
          + [10, 20, 50].map(function (n) {
                return '<option value="' + n + '"' + (n === pageSize ? ' selected' : '') + '>' + n + '</option>';
            }).join('')
          + '</select><span>건</span></div>'
          + '<div class="page-nav-wrap">'
          + '<button id="btnPrev"' + (currentPage <= 1 ? ' disabled' : '') + '>◀</button>'
          + '<span>' + currentPage + ' / ' + totalPages + '</span>'
          + '<button id="btnNext"' + (currentPage >= totalPages ? ' disabled' : '') + '>▶</button>'
          + '</div>';

        document.getElementById('pageSizeSelect').addEventListener('change', function () {
            pageSize = parseInt(this.value, 10); currentPage = 1; fetchPosts();
        });
        document.getElementById('btnPrev').addEventListener('click', function () {
            if (currentPage > 1) { currentPage--; fetchPosts(); }
        });
        document.getElementById('btnNext').addEventListener('click', function () {
            if (currentPage < totalPages) { currentPage++; fetchPosts(); }
        });
    }

    /* ── 인라인 이미지 마커 삽입 ─────────────────────────── */
    function addInlineImages(files) {
        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            if (!file.type.startsWith('image/')) continue;
            var idx    = inlineImageFiles.length;
            var marker = '[이미지 ' + (idx + 1) + ']';
            inlineImageFiles.push(file);

            /* 커서 위치에 마커 삽입 */
            var start = inputContent.selectionStart;
            var end   = inputContent.selectionEnd;
            inputContent.value =
                inputContent.value.slice(0, start) + marker + inputContent.value.slice(end);
            inputContent.selectionStart = inputContent.selectionEnd = start + marker.length;

            /* 썸네일 미리보기 */
            var prevUrl = URL.createObjectURL(file);
            inlinePrevUrls.push(prevUrl);
            var wrap = document.createElement('div');
            wrap.className = 'inline-img-preview';
            var img = document.createElement('img');
            img.src = prevUrl;
            img.className = 'inline-img-thumb';
            var lbl = document.createElement('span');
            lbl.textContent = '이미지 ' + (idx + 1);
            wrap.appendChild(img);
            wrap.appendChild(lbl);
            inlinePreviewWrap.appendChild(wrap);
        }
        inputInlineImage.value = '';   /* 동일 파일 재선택 허용 */
    }

    /* ── 글쓰기 모달 ──────────────────────────────────────── */
    function openWriteModal() {
        inputTitle.value = '';
        inputContent.value = '';
        inputFiles.value = '';
        writeModalErr.textContent = '';
        /* 인라인 이미지 초기화 */
        inlineImageFiles = [];
        inlinePrevUrls.forEach(function (u) { URL.revokeObjectURL(u); });
        inlinePrevUrls = [];
        inlinePreviewWrap.innerHTML = '';
        openModal('writeModal');
    }

    async function savePost() {
        var title   = inputTitle.value.trim();
        var content = inputContent.value.trim();
        if (!title)   { writeModalErr.textContent = '제목을 입력하세요.'; return; }
        if (!content) { writeModalErr.textContent = '내용을 입력하세요.'; return; }
        try {
            btnSavePost.disabled = true;
            var res = await apiFetch('/api/board/boards/' + BOARD_ID + '/posts', {
                method: 'POST',
                body: JSON.stringify({ title: title, content: content }),
            });
            if (!res || !res.ok) {
                var err = res ? await res.json() : null;
                writeModalErr.textContent = (err && err.message) || '등록에 실패했습니다.';
                return;
            }
            var json    = await res.json();
            var newPost = json.result;

            if (newPost && newPost.postId) {
                var updatedContent = content;

                /* 인라인 이미지 업로드 → 마커를 {{ATTACHMENT:uuid}}로 치환 */
                if (inlineImageFiles.length) {
                    var imgFd = new FormData();
                    inlineImageFiles.forEach(function (f) { imgFd.append('files', f); });
                    var imgRes = await apiFetch(
                        '/api/board/boards/' + BOARD_ID + '/posts/' + newPost.postId + '/attachments',
                        { method: 'POST', body: imgFd }
                    );
                    if (imgRes && imgRes.ok) {
                        var imgJson   = await imgRes.json();
                        var uploaded  = imgJson.result || [];
                        uploaded.forEach(function (a, idx) {
                            var marker = '[이미지 ' + (idx + 1) + ']';
                            /* split/join으로 모든 출현 치환 */
                            updatedContent = updatedContent.split(marker).join(
                                '{{ATTACHMENT:' + a.attachmentId + '}}'
                            );
                        });
                        /* 마커가 치환됐으면 본문 업데이트 */
                        if (updatedContent !== content) {
                            await apiFetch(
                                '/api/board/boards/' + BOARD_ID + '/posts/' + newPost.postId,
                                { method: 'PUT', body: JSON.stringify({ title: title, content: updatedContent }) }
                            );
                        }
                    }
                }

                /* 일반 첨부파일 업로드 */
                if (inputFiles.files.length) {
                    var fileFd = new FormData();
                    for (var k = 0; k < inputFiles.files.length; k++) {
                        fileFd.append('files', inputFiles.files[k]);
                    }
                    await apiFetch(
                        '/api/board/boards/' + BOARD_ID + '/posts/' + newPost.postId + '/attachments',
                        { method: 'POST', body: fileFd }
                    );
                }
            }

            closeModal('writeModal');
            showToast('게시글이 등록되었습니다.', 'success');
            if (newPost && newPost.postId) {
                window.location.href = '/board/' + BOARD_ID + '/post/' + newPost.postId;
            } else {
                await fetchPosts();
            }
        } catch (_) {
            writeModalErr.textContent = '오류가 발생했습니다.';
        } finally {
            btnSavePost.disabled = false;
        }
    }

    /* ── 승인/반려 ────────────────────────────────────────── */
    async function approvePost(postId) {
        try {
            var res = await apiFetch(
                '/api/board/boards/' + BOARD_ID + '/posts/' + postId + '/approve',
                { method: 'PATCH' }
            );
            if (!res || !res.ok) { showToast('승인 처리 실패', 'error'); return; }
            showToast('승인되었습니다.', 'success');
            await fetchPosts();
        } catch (_) { showToast('오류가 발생했습니다.', 'error'); }
    }

    async function rejectPost(postId) {
        try {
            var res = await apiFetch(
                '/api/board/boards/' + BOARD_ID + '/posts/' + postId + '/reject',
                { method: 'PATCH' }
            );
            if (!res || !res.ok) { showToast('반려 처리 실패', 'error'); return; }
            showToast('반려되었습니다.', 'success');
            await fetchPosts();
        } catch (_) { showToast('오류가 발생했습니다.', 'error'); }
    }

    /* ── 게시글 삭제 ──────────────────────────────────────── */
    function openDeleteModal(postId) {
        deletingPostId = postId;
        deletePostErr.textContent = '';
        openModal('deletePostModal');
    }

    async function deletePost() {
        if (!deletingPostId) return;
        try {
            btnConfirmDel.disabled = true;
            var res = await apiFetch(
                '/api/board/boards/' + BOARD_ID + '/posts/' + deletingPostId,
                { method: 'DELETE' }
            );
            if (!res || !res.ok) {
                var err = res ? await res.json() : null;
                deletePostErr.textContent = (err && err.message) || '삭제에 실패했습니다.';
                return;
            }
            closeModal('deletePostModal');
            showToast('게시글이 삭제되었습니다.', 'success');
            deletingPostId = null;
            await fetchPosts();
        } catch (_) {
            deletePostErr.textContent = '오류가 발생했습니다.';
        } finally {
            btnConfirmDel.disabled = false;
        }
    }

    /* ── 승인 대기만 보기 토글 ───────────────────────────── */
    function togglePendingOnly() {
        pendingOnly = !pendingOnly;
        btnPending.textContent = pendingOnly ? '전체 보기' : '승인 대기만 보기';
        renderPosts();
    }

    /* ── 승인자 여부 확인 ─────────────────────────────────── */
    async function checkApprover() {
        try {
            var res = await apiFetch('/api/board/boards/' + BOARD_ID + '/approvers');
            if (!res || !res.ok) return;
            var json = await res.json();
            var approvers = json.result || [];
            isApprover = approvers.some(function (a) { return a.memberAccountId === myMemberId; });
        } catch (_) { /* nothing */ }
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

    /* ── 이벤트 ───────────────────────────────────────────── */
    btnWrite.addEventListener('click', openWriteModal);
    btnRefresh.addEventListener('click', fetchPosts);
    btnSavePost.addEventListener('click', savePost);
    btnConfirmDel.addEventListener('click', deletePost);
    btnPending.addEventListener('click', togglePendingOnly);
    searchInput.addEventListener('input', renderPosts);
    /* 인라인 이미지 삽입 */
    btnInsertImage.addEventListener('click', function () { inputInlineImage.click(); });
    inputInlineImage.addEventListener('change', function () { addInlineImages(this.files); });

    /* ── RBAC 권한 조회 ──────────────────────────────────────── */
    async function fetchMyPermissions() {
        try {
            var permRes = await apiFetch('/api/board/my-permissions');
            if (!permRes || !permRes.ok) return;
            var p = (await permRes.json()).result || {};
            canApprove    = !!p.boardApprove;
            canDeletePost = !!p.postDelete;
        } catch (_) { /* 권한 조회 실패 시 기본값 유지 */ }
        finally { /* nothing */ }
    }

    /* ── 초기화 (bfcache 대응: readyState 확인) ─────────────── */
    async function init() {
        if (!BOARD_NAME) { showToast('잘못된 접근입니다.', 'error'); return; }
        var payload = parseJwt();
        myMemberId  = payload.sub || null;
        isAdmin     = payload.role === 'ADMIN';
        /* fetchBoardInfo가 BOARD_ID를 할당해야 fetchPosts 등이 동작 */
        await fetchBoardInfo();
        if (!BOARD_ID) { showToast('게시판을 찾을 수 없습니다.', 'error'); return; }
        /* 권한 먼저 확정 후 게시글 렌더링 (경쟁 조건 방지) */
        await Promise.all([checkApprover(), fetchMyPermissions()]);
        showActionsColumn = isAdmin || isApprover || canApprove || canDeletePost;
        colActionsHeader.hidden = !showActionsColumn;
        /* 승인 대기만 보기 버튼: 승인제 게시판 + 권한 있는 경우만 */
        btnPending.hidden = !(boardRequiresApproval && (isAdmin || isApprover || canApprove));
        await fetchPosts();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
