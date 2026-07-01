-- ============================================================
-- VDI  (사용자당 Docker 컨테이너 1개, exec 중계 방식)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_vdi (
    vdi_id          CHAR(36)        NOT NULL,
    container_name  VARCHAR(100)    NOT NULL,   -- Docker 컨테이너명 (account_id 기반)
    image           VARCHAR(200)    NOT NULL,   -- 기반 Docker image:tag

    status          ENUM(
        'RUNNING',
        'STOPPED',
        'EXITED'
    ) NOT NULL DEFAULT 'STOPPED',

    assigned_to     CHAR(36)        NOT NULL,   -- tb_members.member_id (1인 1컨테이너)

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (vdi_id),
    UNIQUE KEY uk_container_name (container_name),
    UNIQUE KEY uk_assigned_to    (assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- VDI Snapshot  (docker commit → image:tag 저장)
-- RESTORE 시 해당 image_tag로 docker run
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_vdi_snapshot (
    snapshot_id     CHAR(36)        NOT NULL,
    vdi_id          CHAR(36)        NOT NULL,
    snapshot_name   VARCHAR(100)    NOT NULL,
    image_tag       VARCHAR(200)    NOT NULL,   -- docker commit 결과 image:tag

    created_by      CHAR(36)        NOT NULL,   -- tb_members.member_id
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (snapshot_id),

    CONSTRAINT fk_snapshot_vdi
        FOREIGN KEY (vdi_id)
        REFERENCES tb_vdi(vdi_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
