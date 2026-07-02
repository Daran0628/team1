"""코딩테스트 채점 워커.

실행: rq worker judge --url redis://<host>:<port>/<db>  (비밀번호가 있으면
      redis://:<password>@<host>:<port>/<db> 형태로 접속 URL에 포함)

RQ 워커 프로세스는 Flask 앱 컨텍스트가 없는 별도 프로세스이므로,
run_judge()가 호출될 때마다 app을 import해서 컨텍스트를 직접 잡는다.
(app.py는 최상단에서 load_dotenv()를 하므로 .env도 이 시점에 로드된다.)
"""

import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

JUDGE_IMAGES = {
    'PYTHON': 'judge-python:3.11',
    'CPP': 'judge-cpp:gcc13',
    'JAVA': 'judge-java:17',
}

# 언어별 소스 파일명 — Java는 public class 이름이 파일명과 같아야 하므로
# 제출 코드의 public 클래스명은 반드시 Main 이어야 한다.
SOURCE_FILENAME = {
    'PYTHON': 'main.py',
    'CPP': 'main.cpp',
    'JAVA': 'Main.java',
}

COMPILE_CMD = {
    'CPP': ['g++', '-O2', '-o', 'main', 'main.cpp'],
    'JAVA': ['javac', 'Main.java'],
}

RUN_CMD = {
    'PYTHON': ['python3', 'main.py'],
    'CPP': ['./main'],
    'JAVA': ['java', 'Main'],
}

COMPILE_TIME_LIMIT_MS = 10000


def run_judge(submission_id: str) -> None:
    from app import app
    with app.app_context():
        _run_judge_impl(submission_id)


def _run_judge_impl(submission_id: str) -> None:
    from extensions import db
    from domain.model.Submission import Submission
    from domain.model.TestCase import TestCase
    from domain.model.Score import Score
    import service.CodingTestService.CodingTestService as coding_test_service

    submission = Submission.query.get(submission_id)
    if not submission:
        logger.error("채점 대상 제출을 찾을 수 없습니다: %s", submission_id)
        return

    submission.status = 'JUDGING'
    db.session.commit()

    problem = submission.problem
    workdir = tempfile.mkdtemp(prefix='judge-')

    def finish(status: str, score: int) -> None:
        submission.status = status
        submission.score = score
        db.session.commit()

        existing = Score.query.filter_by(
            member_id=submission.member_id, problem_id=submission.problem_id,
        ).first()
        if existing:
            if score > existing.best_score:
                existing.best_score = score
        else:
            db.session.add(Score(
                member_id=submission.member_id,
                problem_id=submission.problem_id,
                best_score=score,
            ))
        db.session.commit()
        # TODO: flask-sse로 프론트에 결과 push

    try:
        try:
            source_bytes = _download_source(coding_test_service.SUBMISSION_BUCKET, submission.source_path)
        except Exception:
            logger.exception("소스코드 다운로드 실패: %s", submission.source_path)
            finish('RUNTIME_ERROR', 0)
            return

        source_path = os.path.join(workdir, SOURCE_FILENAME[submission.language])
        with open(source_path, 'wb') as f:
            f.write(source_bytes)
        os.chmod(workdir, 0o777)  # 컨테이너 안 non-root(uid 1000)가 워크디렉터리에 쓸 수 있도록

        image = JUDGE_IMAGES[submission.language]

        if submission.language in COMPILE_CMD:
            compile_result = _run_in_sandbox(
                image, COMPILE_CMD[submission.language], workdir,
                stdin_data='', time_limit_ms=COMPILE_TIME_LIMIT_MS,
                memory_limit_mb=problem.memory_limit_mb,
            )
            if compile_result is None or compile_result.returncode != 0:
                finish('COMPILE_ERROR', 0)
                return

        test_cases = TestCase.query.filter_by(problem_id=problem.problem_id).all()
        if not test_cases:
            finish('ACCEPTED', 100)
            return

        passed = 0
        for tc in test_cases:
            result = _run_in_sandbox(
                image, RUN_CMD[submission.language], workdir,
                stdin_data=tc.input, time_limit_ms=problem.time_limit_ms,
                memory_limit_mb=problem.memory_limit_mb,
            )
            if result is None:
                finish('TIME_LIMIT_EXCEEDED', _partial_score(passed, len(test_cases)))
                return
            if result.returncode != 0:
                finish('RUNTIME_ERROR', _partial_score(passed, len(test_cases)))
                return
            if _normalize(result.stdout) != _normalize(tc.expected_output):
                finish('WRONG_ANSWER', _partial_score(passed, len(test_cases)))
                return
            passed += 1

        finish('ACCEPTED', 100)
    except Exception:
        logger.exception("채점 중 알 수 없는 오류: %s", submission_id)
        finish('RUNTIME_ERROR', 0)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _download_source(bucket_name: str, object_name: str) -> bytes:
    from core.config.MinioConfig import get_minio_client
    response = get_minio_client().get_object(bucket_name, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _run_in_sandbox(image: str, cmd: list[str], workdir: str, stdin_data: str,
                    time_limit_ms: int, memory_limit_mb: int):
    """docker run으로 사용자 코드를 격리 실행한다. 타임아웃 시 None을 반환한다."""
    try:
        return subprocess.run(
            [
                'docker', 'run', '--rm', '-i',
                '--network', 'none',
                '--memory', f'{memory_limit_mb}m',
                '--memory-swap', f'{memory_limit_mb}m',
                '--cpus', '1',
                '--pids-limit', '64',
                '--read-only',
                '-v', f'{workdir}:/sandbox:rw',
                '--tmpfs', '/tmp:rw,size=16m',
                '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges',
                '--user', '1000:1000',
                '-w', '/sandbox',
                image, *cmd,
            ],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=(time_limit_ms / 1000) + 60,  # 공용 VM 메모리 부족으로 인한 스왑 지연 방어용 여유분 (근본 해결 아님, VM 리소스 이슈)
        )
    except subprocess.TimeoutExpired:
        return None


def _normalize(text: str) -> str:
    return '\n'.join(line.rstrip() for line in (text or '').strip().splitlines())


def _partial_score(passed: int, total: int) -> int:
    return round(passed / total * 100) if total else 0
