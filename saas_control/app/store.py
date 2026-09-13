import json
import os

import psycopg
from psycopg.rows import dict_row
from redis import Redis

from .domain import Product, TenantContext


class PostgresStore:
    def __init__(self, database_url: str, redis_url: str):
        self.database_url = database_url
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def authenticate(self, user_id: str, _password: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select o.organization_id::text, o.name organization_name,
                       p.project_id::text, p.name project_name
                from auth.users u
                join memberships m on m.user_id = u.id
                join organizations o on o.organization_id = m.organization_id
                join projects p on p.organization_id = o.organization_id
                where u.id = %s
                order by o.name, p.name
                """,
                (user_id,),
            )
            return cur.fetchall()

    def has_access(self, user_id: str, organization_id: str, project_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select exists(
                  select 1 from memberships m
                  join projects p on p.organization_id = m.organization_id
                  where m.user_id = %s and m.organization_id = %s and p.project_id = %s
                ) allowed
                """,
                (user_id, organization_id, project_id),
            )
            return cur.fetchone()["allowed"]

    def products(self, organization_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select product from product_entitlements where organization_id = %s and active order by product",
                (organization_id,),
            )
            return [row["product"] for row in cur.fetchall()]

    def submit_job(self, tenant: TenantContext, product: Product, operation: str, key: str):
        if not operation.strip() or not key.strip():
            raise ValueError("任务操作和幂等键不能为空")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into jobs (organization_id, project_id, product, operation, idempotency_key, status)
                values (%s, %s, %s, %s, %s, 'QUEUED')
                on conflict (organization_id, idempotency_key)
                do update set idempotency_key = excluded.idempotency_key
                returning job_id::text, organization_id::text, project_id::text,
                          product, operation, idempotency_key, status, progress
                """,
                (tenant.organization_id, tenant.project_id, product.value, operation, key),
            )
            job = cur.fetchone()
        self.redis.lpush("gpu:jobs", json.dumps({
            "job_id": job["job_id"],
            "organization_id": job["organization_id"],
            "project_id": job["project_id"],
        }))
        return job

    def list_jobs(self, tenant: TenantContext):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select job_id::text, organization_id::text, project_id::text,
                       product, operation, idempotency_key, status, progress
                from jobs
                where organization_id = %s and project_id = %s
                order by created_at desc
                """,
                (tenant.organization_id, tenant.project_id),
            )
            return cur.fetchall()

    def status(self):
        database = "error"
        redis = "error"
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("select 1")
                database = "ok" if cur.fetchone() else "error"
        except psycopg.Error:
            pass
        try:
            redis = "ok" if self.redis.ping() else "error"
        except Exception:
            pass
        return {
            "api": "ok",
            "database": database,
            "redis": redis,
            "worker": "ok" if self.redis.get("gpu:worker:heartbeat") else "error",
        }


def from_environment():
    return PostgresStore(os.environ["DATABASE_URL"], os.environ["REDIS_URL"])
