-- ============================================================
-- 파일 스토리지 리소스 (S3/MinIO 기반)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_storage_resource (
    resource_id     CHAR(36)        NOT NULL,
    resource_name   VARCHAR(255)    NOT NULL,
    s3_key          VARCHAR(1000)   NOT NULL,
    owner_id        CHAR(36)        NOT NULL,   -- member_id (FK 없음)
    is_deleted      TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
