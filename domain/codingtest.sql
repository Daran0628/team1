-- ============================================================
-- Coding Test — Problem  (문제 지문)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_problem (
    problem_id      CHAR(36)        NOT NULL,
    title           VARCHAR(200)    NOT NULL,
    description     TEXT            NOT NULL,   -- 지문 (입출력 형식/제약조건 포함)

    time_limit_ms   INT             NOT NULL DEFAULT 2000,
    memory_limit_mb INT             NOT NULL DEFAULT 256,

    difficulty      ENUM('BEGINNER','BASIC','INTERMEDIATE','ADVANCED')
                    NOT NULL DEFAULT 'BEGINNER',  -- 입문/초급/중급/고급

    created_by      CHAR(36)        NOT NULL,   -- tb_members.member_id (출제자)

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (problem_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Coding Test — Test Case  (문제별 입출력 테스트케이스)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_test_case (
    test_case_id     CHAR(36)   NOT NULL,
    problem_id       CHAR(36)   NOT NULL,

    input            TEXT       NOT NULL,
    expected_output  TEXT       NOT NULL,
    is_sample        TINYINT(1) NOT NULL DEFAULT 0,   -- 1=공개 샘플, 0=비공개(채점용) 히든

    created_at       DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (test_case_id),

    CONSTRAINT fk_testcase_problem
        FOREIGN KEY (problem_id)
        REFERENCES tb_problem(problem_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Coding Test — Submission  (코드 제출 및 채점 결과)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_submission (
    submission_id   CHAR(36)        NOT NULL,
    problem_id      CHAR(36)        NOT NULL,
    member_id       CHAR(36)        NOT NULL,   -- tb_members.member_id (제출자)

    language        VARCHAR(20)     NOT NULL,   -- PYTHON / CPP / JAVA ...
    source_path     VARCHAR(255)    NOT NULL,   -- MinIO 오브젝트 키 (소스코드 원문 저장 위치)

    status          ENUM(
        'PENDING',
        'JUDGING',
        'ACCEPTED',
        'WRONG_ANSWER',
        'TIME_LIMIT_EXCEEDED',
        'RUNTIME_ERROR',
        'COMPILE_ERROR'
    ) NOT NULL DEFAULT 'PENDING',

    score           INT             NOT NULL DEFAULT 0,   -- 0~100 (테스트케이스 통과율 기준)
    runtime_ms      INT             NULL,
    memory_kb       INT             NULL,

    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (submission_id),

    CONSTRAINT fk_submission_problem
        FOREIGN KEY (problem_id)
        REFERENCES tb_problem(problem_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- Coding Test — Score  (회원별 문제별 최고 점수, 리더보드용 upsert)
-- ============================================================
CREATE TABLE IF NOT EXISTS tb_score (
    member_id   CHAR(36) NOT NULL,   -- tb_members.member_id
    problem_id  CHAR(36) NOT NULL,

    best_score  INT      NOT NULL DEFAULT 0,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (member_id, problem_id),

    CONSTRAINT fk_score_problem
        FOREIGN KEY (problem_id)
        REFERENCES tb_problem(problem_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
