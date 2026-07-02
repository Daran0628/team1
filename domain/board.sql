-- ============================================================
-- Board (게시판)
-- ============================================================

-- ── 게시판 ────────────────────────────────────────────────────
-- board_type      : FREE(자유) / NOTICE(공지) / DEPARTMENT(부서) / DATA_ROOM(자료실)
-- department_id   : DEPARTMENT 타입일 때만 값이 있음 (부서 삭제 시 NULL 처리)
-- is_public       : 0 = 부서원만 볼 수 있음 (DEPARTMENT 기본값)
-- requires_approval: 1 = 게시글 작성 시 승인 필요
-- approval_expires_at: 승인 기간 (NULL = 무기한)
-- created_by      : member_id (FK 없음 — 멤버 삭제 후에도 게시판 유지)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_board (
    board_id             CHAR(36)                                                    NOT NULL,
    board_name           VARCHAR(100)                                                NOT NULL,
    board_type           ENUM('FREE', 'NOTICE', 'DEPARTMENT', 'DATA_ROOM')          NOT NULL DEFAULT 'FREE',
    description          VARCHAR(500)                                                NULL,
    department_id        CHAR(36)                                                    NULL,
    is_active            TINYINT(1)                                                  NOT NULL DEFAULT 1,
    is_public            TINYINT(1)                                                  NOT NULL DEFAULT 1,
    requires_approval    TINYINT(1)                                                  NOT NULL DEFAULT 0,
    approval_expires_at  DATETIME                                                    NULL,
    approval_purpose     VARCHAR(200)                                                NULL,
    created_by           CHAR(36)                                                    NOT NULL,
    created_at           DATETIME                                                    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME                                                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (board_id),

    INDEX idx_board_type   (board_type, is_active),
    INDEX idx_board_dept   (department_id),

    CONSTRAINT fk_board_department
        FOREIGN KEY (department_id)
        REFERENCES tb_department(department_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 게시글 ────────────────────────────────────────────────────
-- status  : DRAFT(임시저장) / PENDING(승인대기) / PUBLISHED(게시됨) / REJECTED(반려)
--           requires_approval=0인 게시판은 바로 PUBLISHED
-- author_id: member_id (FK 없음)
-- like_count: tb_post_like COUNT를 캐싱 (동기화는 애플리케이션에서 관리)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_post (
    post_id     CHAR(36)                                            NOT NULL,
    board_id    CHAR(36)                                            NOT NULL,
    title       VARCHAR(300)                                        NOT NULL,
    content     LONGTEXT                                            NOT NULL,
    author_id   CHAR(36)                                            NOT NULL,
    status      ENUM('DRAFT', 'PENDING', 'PUBLISHED', 'REJECTED')  NOT NULL DEFAULT 'PUBLISHED',
    view_count  INT UNSIGNED                                        NOT NULL DEFAULT 0,
    like_count  INT UNSIGNED                                        NOT NULL DEFAULT 0,
    is_pinned   TINYINT(1)                                         NOT NULL DEFAULT 0,
    is_deleted  TINYINT(1)                                         NOT NULL DEFAULT 0,
    created_at  DATETIME                                            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME                                            NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (post_id),

    INDEX idx_post_board  (board_id, is_deleted, created_at DESC),
    INDEX idx_post_author (author_id),
    INDEX idx_post_status (status),
    FULLTEXT INDEX ft_post_title_content (title, content),

    CONSTRAINT fk_post_board
        FOREIGN KEY (board_id)
        REFERENCES tb_board(board_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 게시글 첨부파일 ───────────────────────────────────────────
-- s3_key: MinIO 오브젝트 키 (tb_storage_resource FK 없음 — 스토리지 독립 관리)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_post_attachment (
    attachment_id   CHAR(36)        NOT NULL,
    post_id         CHAR(36)        NOT NULL,
    original_name   VARCHAR(255)    NOT NULL,
    s3_key          VARCHAR(500)    NOT NULL,
    file_size       BIGINT UNSIGNED NOT NULL DEFAULT 0,
    content_type    VARCHAR(100)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (attachment_id),

    INDEX idx_attach_post (post_id),

    CONSTRAINT fk_attach_post
        FOREIGN KEY (post_id)
        REFERENCES tb_post(post_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 댓글 (대댓글: parent_id 자기참조) ─────────────────────────
-- parent_id NULL = 최상위 댓글, NOT NULL = 대댓글
-- author_id: member_id (FK 없음)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_post_comment (
    comment_id  CHAR(36)    NOT NULL,
    post_id     CHAR(36)    NOT NULL,
    parent_id   CHAR(36)    NULL,
    author_id   CHAR(36)    NOT NULL,
    content     TEXT        NOT NULL,
    is_deleted  TINYINT(1)  NOT NULL DEFAULT 0,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (comment_id),

    INDEX idx_comment_post   (post_id, is_deleted),
    INDEX idx_comment_parent (parent_id),

    CONSTRAINT fk_comment_post
        FOREIGN KEY (post_id)
        REFERENCES tb_post(post_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_comment_parent
        FOREIGN KEY (parent_id)
        REFERENCES tb_post_comment(comment_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 추천 (좋아요) ─────────────────────────────────────────────
-- 복합 PK로 중복 추천 방지
-- INSERT 시 tb_post.like_count += 1, DELETE 시 -= 1 (애플리케이션 처리)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_post_like (
    post_id     CHAR(36)    NOT NULL,
    member_id   CHAR(36)    NOT NULL,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (post_id, member_id),

    CONSTRAINT fk_like_post
        FOREIGN KEY (post_id)
        REFERENCES tb_post(post_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 조회/회람 기록 ────────────────────────────────────────────
-- last_viewed_at ON UPDATE: 재방문 시 갱신 → 미읽음 계산 가능
-- 미읽음 여부 = post.updated_at > post_view.last_viewed_at
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_post_view (
    post_id         CHAR(36)    NOT NULL,
    member_id       CHAR(36)    NOT NULL,
    last_viewed_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (post_id, member_id),

    CONSTRAINT fk_view_post
        FOREIGN KEY (post_id)
        REFERENCES tb_post(post_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── 게시판별 승인자 ───────────────────────────────────────────
-- requires_approval=1인 게시판에서 게시글을 PUBLISHED로 바꿀 수 있는 멤버
-- 전역 관리 권한(RBAC BOARD/MANAGE)과 별개로 게시판 단위로 지정
-- granted_by: member_id (FK 없음)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_board_approver (
    board_id    CHAR(36)    NOT NULL,
    member_id   CHAR(36)    NOT NULL,
    granted_by  CHAR(36)    NOT NULL,
    granted_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (board_id, member_id),

    CONSTRAINT fk_approver_board
        FOREIGN KEY (board_id)
        REFERENCES tb_board(board_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_approver_member
        FOREIGN KEY (member_id)
        REFERENCES tb_members(member_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
