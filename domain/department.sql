CREATE TABLE IF NOT EXISTS tb_department (
    department_id   CHAR(36) PRIMARY KEY,
    department_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;