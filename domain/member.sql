CREATE TABLE IF NOT EXISTS tb_members (
    member_id       CHAR(36) ,
    name_ko         VARCHAR(18)     NOT NULL,
    account_id      VARCHAR(20)     NOT NULL,
    employee_no     VARCHAR(10)     NOT NULL,
    department_id   CHAR(36) NOT NULL,
    email           VARCHAR(50)     NOT NULL,
    password        VARCHAR(60)     NOT NULL,
    enrollment_status ENUM('ACTIVE', 'ON_LEAVE', 'RESIGNED') NOT NULL,
    account_type    ENUM('USER', 'ADMIN', 'SUPERADMIN')      NOT NULL,
    work_type       ENUM('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN') NOT NULL,
    car_num         VARCHAR(8)      NULL,
    address         VARCHAR(50)     NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login      DATETIME        NULL,

    PRIMARY KEY (member_id),
    CONSTRAINT fk_member_department
        FOREIGN KEY (department_id)
        REFERENCES tb_department(department_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
