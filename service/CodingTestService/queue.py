from redis import Redis
from rq import Queue

from core.config.RedisConfig import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWD

# RQ는 job을 pickle로 저장하므로 decode_responses=True인 공용 redis_client를
# 재사용하면 안 된다 (바이너리가 깨짐) — 별도 커넥션을 쓴다.
_redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWD,
)

judge_queue = Queue('judge', connection=_redis_conn)


def enqueue_judge(submission_id: str) -> None:
    judge_queue.enqueue(
        'service.CodingTestService.judge.run_judge',
        submission_id,
        job_timeout='2m',
    )
