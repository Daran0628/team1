-- ============================================================
-- Role
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_role (
    role_id         CHAR(36)        NOT NULL,
    role_name       VARCHAR(50)     NOT NULL,
    description     VARCHAR(255),

    PRIMARY KEY (role_id),
    UNIQUE KEY uk_role_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Permission
-- type   : STORAGE / VDI / RBAC
-- action : StorageAction / VdiAction / RbacAction 값
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_permission (
    permission_id   CHAR(36)        NOT NULL,
    type            VARCHAR(30)     NOT NULL,
    action          VARCHAR(30)     NOT NULL,

    PRIMARY KEY (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Permission -> Resource  (M:N)
-- RBAC 타입은 리소스 불필요, STORAGE/VDI 타입은 리소스 UUID 목록
-- resource_id : tb_storage_resource.resource_id 또는 VDI UUID
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_permission_resource (
    permission_id   CHAR(36)        NOT NULL,
    resource_id     CHAR(36)        NOT NULL,

    PRIMARY KEY (permission_id, resource_id),

    CONSTRAINT fk_perm_resource_perm
        FOREIGN KEY (permission_id)
        REFERENCES tb_permission(permission_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Role -> Permission
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_role_permission (
    role_id         CHAR(36)        NOT NULL,
    permission_id   CHAR(36)        NOT NULL,

    PRIMARY KEY (role_id, permission_id),

    CONSTRAINT fk_role_permission_role
        FOREIGN KEY (role_id)
        REFERENCES tb_role(role_id),

    CONSTRAINT fk_role_permission_permission
        FOREIGN KEY (permission_id)
        REFERENCES tb_permission(permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Group  (커스텀 그룹 / TEAM 주체)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_group (
    group_id        CHAR(36)        NOT NULL,
    group_name      VARCHAR(50)     NOT NULL,
    description     VARCHAR(255),
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (group_id),
    UNIQUE KEY uk_group_name (group_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Group -> Member  (M:N)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_group_member (
    group_id        CHAR(36)        NOT NULL,
    member_id       CHAR(36)        NOT NULL,

    PRIMARY KEY (group_id, member_id),

    CONSTRAINT fk_group_member_group
        FOREIGN KEY (group_id)
        REFERENCES tb_group(group_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_group_member_member
        FOREIGN KEY (member_id)
        REFERENCES tb_members(member_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Role Binding
--
-- MEMBER
-- DEPARTMENT
-- TEAM
--
-- 를 모두 하나의 테이블에서 관리
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_role_binding (

    subject_type    ENUM(
        'MEMBER',
        'DEPARTMENT',
        'TEAM'
    ) NOT NULL,

    subject_id      CHAR(36)        NOT NULL,

    resource_type   VARCHAR(30)     NOT NULL,

    resource_id     CHAR(36)        NOT NULL,

    role_id         CHAR(36)        NOT NULL,

    granted_by      CHAR(36)        NOT NULL,

    granted_at      DATETIME        NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        subject_type,
        subject_id,
        resource_type,
        resource_id
    ),

    CONSTRAINT fk_role_binding_role
        FOREIGN KEY (role_id)
        REFERENCES tb_role(role_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;