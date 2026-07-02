from dotenv import load_dotenv
load_dotenv()

import json
import os

from sqlalchemy.exc import OperationalError

from app import app, db
from domain.model.Member import Member
from domain.model.Problem import Problem
from domain.model.TestCase import TestCase

## python seed_codingtest.py 로 적용
## 각자 DB에 코딩테스트 문제(난이도별 10문제 x 4단계 = 40문제)를 채워 넣는 스크립트.
## - 이미 difficulty 컬럼이 있으면 ALTER는 건너뛴다.
## - 이미 등록된 제목의 문제는 건너뛴다(재실행해도 중복 생성 안 됨).

_SEED_DIR = os.path.join(os.path.dirname(__file__), 'seed_data', 'codingtest')

FILES = [
    ('bronze.json', 'BEGINNER'),
    ('silver.json', 'BASIC'),
    ('gold.json', 'INTERMEDIATE'),
    ('platinum.json', 'ADVANCED'),
]


def ensure_difficulty_column():
    from sqlalchemy import text
    try:
        db.session.execute(text(
            "ALTER TABLE tb_problem ADD COLUMN difficulty "
            "ENUM('BEGINNER','BASIC','INTERMEDIATE','ADVANCED') "
            "NOT NULL DEFAULT 'BEGINNER' AFTER memory_limit_mb"
        ))
        db.session.commit()
        print("difficulty 컬럼을 추가했습니다.")
    except OperationalError as e:
        db.session.rollback()
        if 'Duplicate column name' in str(e):
            print("difficulty 컬럼이 이미 존재합니다. 건너뜁니다.")
        else:
            raise


def seed_problems():
    admin = Member.query.filter_by(account_id='admin1').first()
    if not admin:
        raise SystemExit("admin1 계정이 없습니다. 먼저 seed.py를 실행해 기본 계정을 만들어주세요.")

    total_created = 0
    for filename, difficulty in FILES:
        with open(os.path.join(_SEED_DIR, filename), encoding='utf-8') as f:
            problems = json.load(f)

        created = 0
        for p in problems:
            if Problem.query.filter_by(title=p['title']).first():
                continue
            problem = Problem(
                title=p['title'],
                description=p['description'],
                difficulty=difficulty,
                time_limit_ms=p.get('time_limit_ms', 2000),
                memory_limit_mb=p.get('memory_limit_mb', 256),
                created_by=admin.id,
            )
            db.session.add(problem)
            db.session.flush()
            for tc in p['test_cases']:
                db.session.add(TestCase(
                    problem_id=problem.problem_id,
                    input=tc['input'],
                    expected_output=tc['expected_output'],
                    is_sample=bool(tc.get('is_sample', False)),
                ))
            created += 1
        db.session.commit()
        print(f"{filename} -> {difficulty}: {created}개 생성 (총 {len(problems)}개 중 나머지는 이미 존재)")
        total_created += created

    print(f"완료. 이번 실행에서 새로 생성된 문제 수: {total_created} / 전체 문제 수: {Problem.query.count()}")


if __name__ == '__main__':
    with app.app_context():
        ensure_difficulty_column()
        seed_problems()
