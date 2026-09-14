import json
import os
import time

import psycopg
from redis import Redis

from .store import from_environment


def run():
    redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    database_url = os.environ["DATABASE_URL"]
    store = from_environment()
    while True:
        redis.set("gpu:worker:heartbeat", str(time.time()), ex=30)
        item = redis.brpop("gpu:jobs", timeout=5)
        if not item:
            continue
        job = json.loads(item[1])
        if job.get("product") == "gpu-data" and job.get("operation") == "ANALYZE" and job.get("dataset_id"):
            try:
                store.process_gpu_data_job(job)
            except Exception:
                with psycopg.connect(database_url) as conn, conn.cursor() as cur:
                    cur.execute(
                        "update jobs set status='FAILED', progress=100, public_error_code='ANALYSIS_FAILED' where job_id=%s",
                        (job["job_id"],),
                    )
            continue
        with psycopg.connect(database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                update jobs set status = 'RUNNING', progress = 50
                where job_id = %s and organization_id = %s and project_id = %s and status = 'QUEUED'
                """,
                (job["job_id"], job["organization_id"], job["project_id"]),
            )
            cur.execute(
                """
                update jobs set status = 'SUCCEEDED', progress = 100
                where job_id = %s and organization_id = %s and project_id = %s and status = 'RUNNING'
                """,
                (job["job_id"], job["organization_id"], job["project_id"]),
            )


if __name__ == "__main__":
    run()
