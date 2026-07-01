-- ============================================================
-- Object Storage  (MinIO 기반 멀티 버켓 관리)
-- ============================================================

-- ── Bucket registry ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tb_storage_bucket (
    bucket_id   CHAR(36)    NOT NULL,
    bucket_name VARCHAR(63) NOT NULL,   -- MinIO bucket naming rules
    created_by  CHAR(36)    NOT NULL,   -- member_id (FK 없음)
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (bucket_id),
    UNIQUE KEY uk_bucket_name (bucket_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Object metadata ──────────────────────────────────────────
-- ※ 기존 tb_storage_resource가 있다면 아래 마이그레이션 실행:
--   ALTER TABLE tb_storage_resource
--     ADD COLUMN bucket_name VARCHAR(63) NOT NULL DEFAULT '' AFTER resource_id,
--     ADD CONSTRAINT fk_resource_bucket
--       FOREIGN KEY (bucket_name) REFERENCES tb_storage_bucket(bucket_name) ON DELETE CASCADE;
CREATE TABLE IF NOT EXISTS tb_storage_resource (
    resource_id   CHAR(36)     NOT NULL,
    bucket_name   VARCHAR(63)  NOT NULL,
    resource_name VARCHAR(255) NOT NULL,   -- 표시 이름 (파일명)
    s3_key        VARCHAR(1000) NOT NULL,  -- MinIO object key (bucket 내 경로)
    owner_id      CHAR(36)     NOT NULL,   -- member_id
    is_deleted    TINYINT(1)   NOT NULL DEFAULT 0,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (resource_id),
    UNIQUE KEY uk_bucket_key (bucket_name, s3_key),

    CONSTRAINT fk_resource_bucket
        FOREIGN KEY (bucket_name)
        REFERENCES tb_storage_bucket(bucket_name)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
