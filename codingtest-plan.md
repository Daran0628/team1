# 코딩테스트(백준형 채점) 기능 구현 계획

VM(Ubuntu) + Docker를 이용해 문제 출제 → 코드 제출 → 채점 → 점수 저장까지
동작하는 온라인 저지(Online Judge)를 만들기 위한 단계별 계획.
기존 `VdiService`가 `subprocess`로 `docker` CLI를 직접 호출하는 패턴을 그대로 따른다.

## 0. 전체 아키텍처

```
[학생] --코드 제출--> [Flask API] --Job enqueue--> [Redis Queue]
                          |                              |
                     tb_submission(PENDING)         [Judge Worker]
                                                          |
                                          docker run (격리된 컨테이너에서 컴파일/실행)
                                                          |
                                            테스트케이스별 결과 비교 -> 점수 산출
                                                          |
                                   tb_submission 갱신 + tb_score upsert + SSE로 결과 push
```

## 1. Ubuntu VM에 Docker 준비

```bash
sudo apt update && sudo apt install -y docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $(whoami)   # 앱(gunicorn) 실행 유저를 docker 그룹에 추가
```

## 2. 언어별 채점용 Docker 이미지

언어마다 최소 런타임만 있는 이미지를 따로 빌드 (`judge-python:3.11`, `judge-cpp:gcc13`, `judge-java:17` 등).

```dockerfile
# judge-python.Dockerfile
FROM python:3.11-alpine
RUN adduser -D -u 1000 runner
USER runner
WORKDIR /sandbox
```

```bash
docker build -t judge-python:3.11 -f judge-python.Dockerfile .
```

## 3. DB 스키마 (`domain/codingtest.sql`, `domain/model/`)

| 테이블 | 주요 컬럼 |
|---|---|
| `tb_problem` | problem_id, title, description, time_limit_ms, memory_limit_mb, created_by, created_at |
| `tb_test_case` | test_case_id, problem_id(FK), input, expected_output, is_sample |
| `tb_submission` | submission_id, problem_id(FK), member_id, language, source_path(MinIO 키), status, score, runtime_ms, memory_kb, created_at |
| `tb_score` | member_id, problem_id, best_score (리더보드용 upsert 테이블) |

- `status` ENUM: `PENDING`, `JUDGING`, `ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `COMPILE_ERROR`
- 소스코드는 DB에 직접 넣지 않고 기존 `StorageService`(MinIO)에 저장, `tb_submission`에는 경로만 저장.

## 4. 제출 API (`web/routes`)

- `POST /coding-test/problems` — 문제 출제
- `POST /coding-test/submissions` — 코드 제출 → 소스 저장 + `tb_submission` PENDING insert + 채점 잡 enqueue
- `GET /coding-test/submissions/{id}` — 상태/결과 조회

컨트롤러에서 `docker run`을 동기 실행하지 않는다 (동시 다중 제출 시 요청 스레드가 블로킹됨).

## 5. 비동기 채점 큐 (Redis + RQ)

```bash
pip install rq
```

```python
# service/CodingTestService/queue.py
from redis import Redis
from rq import Queue
judge_queue = Queue('judge', connection=Redis())
```

제출 시:
```python
judge_queue.enqueue('service.CodingTestService.judge.run_judge', submission_id)
```

워커는 systemd 서비스로 앱과 별도 상시 구동:
```bash
rq worker judge --url redis://localhost:6379
```

동시 채점 개수는 워커 프로세스 수(concurrency)로 VM 리소스에 맞춰 제한.

## 6. 채점 워커 핵심 로직

`VdiService._docker()` 헬퍼와 같은 패턴이되, 사용자 코드를 실행하므로 격리 옵션을 강하게 건다.

```python
def _run_in_sandbox(image, cmd, stdin_data, time_limit_ms, memory_limit_mb):
    result = subprocess.run(
        ['docker', 'run', '--rm', '-i',
         '--network', 'none',
         '--memory', f'{memory_limit_mb}m', '--memory-swap', f'{memory_limit_mb}m',
         '--cpus', '1', '--pids-limit', '64',
         '--read-only', '--tmpfs', '/tmp:rw,size=16m',
         '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
         '--user', '1000:1000',
         image, *cmd],
        input=stdin_data, capture_output=True, text=True,
        timeout=time_limit_ms / 1000 + 1,   # docker 옵션이 씹혀도 대비하는 이중 방어
    )
    return result
```

`run_judge(submission_id)` 흐름:

1. `tb_submission` → `JUDGING`
2. MinIO에서 소스코드를 내려받아 임시 디렉토리에 저장
3. 컴파일 언어(C/C++/Java)는 별도 `docker run`으로 컴파일 → 실패 시 `COMPILE_ERROR`
4. `tb_test_case` 순회하며 `_run_in_sandbox` 실행
   - `TimeoutExpired` → `TIME_LIMIT_EXCEEDED`
   - `returncode != 0` → `RUNTIME_ERROR`
   - stdout(trim/개행 정규화) != expected_output → `WRONG_ANSWER`
   - 전부 통과 → `ACCEPTED`
5. 테스트케이스 통과율로 `score` 계산
6. `tb_submission` 결과 갱신, `tb_score` 최고점 upsert

## 7. 보안 체크리스트 (사용자 코드 실행이므로 최우선)

- `--network none` — 외부 통신 차단
- `--memory` + `--memory-swap` 동일값 — 스왑으로 메모리 제한 우회 방지
- `--pids-limit` — 포크 폭탄 방지
- `--read-only` + tmpfs — 컨테이너 내부 영구 쓰기 불가
- non-root `--user`, `--cap-drop ALL`, `--security-opt no-new-privileges`
- `--rm` 필수 — 채점마다 컨테이너 누적 시 디스크 고갈
- subprocess `timeout`도 별도로 걸어 이중 방어

## 8. 실시간 결과 전달

기존 `flask-sse`를 재사용해 채점 완료 시 해당 채널로 push → 프론트 폴링 불필요.

## 9. 운영 체크리스트

- `docker system prune` 주기적 실행 (죽은 컨테이너/이미지 정리)
- 채점용 이미지는 VM에 미리 build/pull 해두고 채점 시 재빌드하지 않음 (속도)
- 워커 프로세스는 systemd unit으로 등록해 VM 재부팅 시 자동 기동

## 10. 문제 콘텐츠 준비 방법 (문제/테스트케이스는 시스템이 안 만들어줌)

이 채점 시스템은 "제출된 코드를 실행해 채점하는 인프라"일 뿐이고, 문제 지문·테스트케이스·정답은
출제자(팀원)가 직접 준비해야 한다.

**직접 준비할 것**

1. 문제 지문 (제목, 설명, 입출력 형식, 제약조건)
2. 테스트케이스 (input / expected_output 쌍) — 샘플(공개) + 히든(비공개) 둘 다 필요
3. 모범 답안 코드 (필수는 아니지만 추천) — 손으로 `expected_output`을 계산하면 실수하기 쉬우므로,
   모범 답안을 같은 채점 샌드박스에서 돌려 나온 출력을 `expected_output`으로 채택하는 방식이 안전
   (백준/코드포스 등 실제 저지도 이 방식 사용)
4. 제한사항 (time_limit_ms, memory_limit_mb) — 너무 빡빡하면 정상 코드도 TLE 남

**주의**: 백준(BOJ), 프로그래머스, LeetCode, HackerRank 등은 이용약관상 문제·테스트케이스의
스크래핑/재배포를 금지한다. 개인 연습용 열람은 괜찮지만 그 내용을 그대로 우리 채점 시스템에
옮겨 담는 건 팀 내부 프로젝트라도 약관 위반 소지가 있어 지양하는 게 안전하다.

**무료로 가져다 쓸 수 있는 곳 (라이선스가 비교적 명확한 곳 위주)**

| 출처 | 특징 | 라이선스/주의점 |
|---|---|---|
| [Kattis Problem Archive](https://open.kattis.com/problems) | ICPC 등 각종 대회 문제를 다른 저지가 가져다 쓰라고 공개한 아카이브. 지문 + 테스트데이터 세트까지 제공 | 문제별로 라이선스 표기(CC BY-SA 등), 출처 표시 조건으로 재사용 가능한 것이 많음. **문제마다 라이선스 꼭 확인** |
| [Project Euler](https://projecteuler.net/) | 수학/알고리즘 문제, 정답이 "숫자 하나"라 별도 테스트케이스 없이 값만 비교하면 됨 | 개인/교육용 사용 명시적 허용, 재배포는 지양 |
| ICPC 공식 리저널 아카이브 | 과거 지역/월드파이널 기출 문제·데이터 공개 | 교육/연습 목적 사용에 열려있음 |
| [USACO](http://www.usaco.org/) 기출 | Bronze~Platinum 난이도별 정리, 팀 실력별 문제 고르기 좋음 | 교육 목적 사용 허용 |
| 자체 출제 | 저작권 이슈 없음, 팀 수준에 맞게 난이도 조절 가능 | 시간이 걸림 — 위 3번(모범 답안으로 expected_output 자동 생성) 방식 활용 추천 |

**추천 조합**: 자체 출제(핵심 문제 몇 개) + Kattis/Project Euler(양 채우기). 처음부터 전부
직접 만들려 하지 말고, 초기엔 위 아카이브에서 라이선스 확인된 문제 몇 개를 가져와 시스템부터
검증하고, 이후 팀 내부용 문제를 늘려가는 순서를 추천.

## 다음 액션 (미정 / 논의 필요)

- [ ] `domain/model/Problem.py`, `TestCase.py`, `Submission.py`, `Score.py` 작성
- [ ] `service/CodingTestService/` 서비스 로직 구현 (VdiService 컨벤션 준수)
- [ ] `web/routes` 코딩테스트 라우트 + DTO 추가
- [ ] 채점 워커(`judge.py`) 및 언어별 컴파일/실행 커맨드 매핑 작성
- [ ] 언어별 `judge-*` Dockerfile 작성 및 VM에 빌드
- [ ] 점수 산정 규칙 확정 (테스트케이스 배점 vs 통과율 %) — 조원들과 논의 필요
