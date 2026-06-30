-- ============================================================
-- Chat
-- ============================================================

-- ── Chat Room ─────────────────────────────────────────────
-- room_type  : DIRECT(1:1) / GROUP(그룹)
-- direct_key : DIRECT 방 중복 방지용
--              (sorted member_id_a + '_' + member_id_b, CHAR(36+1+36))
--              GROUP 방은 NULL
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_chat_room (
    room_id     CHAR(36)                    NOT NULL,
    room_type   ENUM('DIRECT', 'GROUP')     NOT NULL,
    room_name   VARCHAR(100)                NULL,       -- GROUP 방 이름 (DIRECT는 NULL)
    direct_key  CHAR(73)                    NULL,       -- DIRECT 방 중복 방지 (GROUP은 NULL)
    created_by  CHAR(36)                    NOT NULL,   -- member_id (FK 없음)
    created_at  DATETIME                    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME                    NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (room_id),
    UNIQUE KEY uk_direct_key (direct_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Chat Room Member ──────────────────────────────────────
-- room_role   : MEMBER / ADMIN (공지, 강퇴, 권한 변경)
-- last_read_at: 마지막으로 읽은 시각 → 미읽음 메시지 수 계산에 사용
--               미읽음 수 = COUNT(*) FROM tb_chat_message
--                           WHERE room_id = ? AND created_at > last_read_at
-- is_active   : 0 = 방 나간 상태 (이력 보존, 재초대 가능)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_chat_room_member (
    room_id         CHAR(36)                    NOT NULL,
    member_id       CHAR(36)                    NOT NULL,
    room_role       ENUM('MEMBER', 'ADMIN')     NOT NULL DEFAULT 'MEMBER',
    last_read_at    DATETIME                    NULL,
    joined_at       DATETIME                    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active       TINYINT(1)                  NOT NULL DEFAULT 1,

    PRIMARY KEY (room_id, member_id),

    CONSTRAINT fk_chat_room_member_room
        FOREIGN KEY (room_id)
        REFERENCES tb_chat_room(room_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chat_room_member_member
        FOREIGN KEY (member_id)
        REFERENCES tb_members(member_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Chat Message ──────────────────────────────────────────
-- message_type: TEXT / FILE / IMAGE / NOTICE(관리자 공지)
-- content     : 메시지 본문 (FILE·IMAGE는 NULL 가능)
-- is_deleted  : soft delete → 클라이언트에 "삭제된 메시지"로 표시
-- created_at  : DATETIME(6) 마이크로초 → 동시 메시지 정렬 정확도 보장
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_chat_message (
    message_id      CHAR(36)                                        NOT NULL,
    room_id         CHAR(36)                                        NOT NULL,
    sender_id       CHAR(36)                                        NOT NULL,   -- member_id
    message_type    ENUM('TEXT', 'FILE', 'IMAGE', 'NOTICE')         NOT NULL DEFAULT 'TEXT',
    content         TEXT                                            NULL,
    is_deleted      TINYINT(1)                                      NOT NULL DEFAULT 0,
    created_at      DATETIME(6)                                     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (message_id),

    INDEX idx_chat_message_room_time (room_id, created_at),   -- 페이지네이션
    FULLTEXT INDEX ft_chat_message_content (content),         -- 메시지 검색

    CONSTRAINT fk_chat_message_room
        FOREIGN KEY (room_id)
        REFERENCES tb_chat_room(room_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chat_message_sender
        FOREIGN KEY (sender_id)
        REFERENCES tb_members(member_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Chat File ─────────────────────────────────────────────
-- 메시지에 첨부된 파일·이미지 메타데이터
-- resource_id : tb_storage_resource.resource_id (FK 없음 - 스토리지 독립 관리)
-- mime_type   : 이미지 판별 및 미리보기 여부 결정 (e.g. image/*)
-- file_size   : bytes 단위
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_chat_file (
    file_id         CHAR(36)        NOT NULL,
    message_id      CHAR(36)        NOT NULL,
    resource_id     CHAR(36)        NOT NULL,   -- tb_storage_resource.resource_id (FK 없음)
    original_name   VARCHAR(255)    NOT NULL,
    file_size       BIGINT          NOT NULL,
    mime_type       VARCHAR(100)    NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (file_id),

    CONSTRAINT fk_chat_file_message
        FOREIGN KEY (message_id)
        REFERENCES tb_chat_message(message_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
