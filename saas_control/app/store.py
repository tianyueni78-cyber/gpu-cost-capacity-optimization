import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from redis import Redis

from .domain import Product, TenantContext
from .gpu_data_runner import inspect_files, prepare_public_files, run_analysis
from .gpu_optimize_runner import build_recommendations


class PostgresStore:
    def __init__(self, database_url: str, redis_url: str, data_root: str = "/data"):
        self.database_url = database_url
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.data_root = Path(data_root)

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def ensure_gpu_data_schema(self):
        with self._connect() as conn:
            for name in ("003_gpu_data.sql", "004_public_optimize.sql"):
                migration = Path(__file__).parents[1] / "migrations" / name
                conn.execute(migration.read_text(encoding="utf-8"))

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
                          product, operation, idempotency_key, status, progress, (xmax = 0) created
                """,
                (tenant.organization_id, tenant.project_id, product.value, operation, key),
            )
            job = cur.fetchone()
        created = job.pop("created")
        if created:
            self.redis.lpush("gpu:jobs", json.dumps({
                "job_id": job["job_id"],
                "organization_id": job["organization_id"],
                "project_id": job["project_id"],
            }))
        return job

    def create_dataset(self, tenant: TenantContext, files: dict[str, tuple[str, bytes]], source_type: str):
        dataset_id = str(uuid4())
        folder = self.data_root / "uploads" / tenant.organization_id / tenant.project_id / dataset_id
        folder.mkdir(parents=True, exist_ok=False)
        try:
            inspection = inspect_files(files)
            row_counts = inspection["row_counts"]
            for role, (file_name, content) in files.items():
                target = folder / f"{role}.csv"
                target.write_bytes(content)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """insert into datasets
                       (organization_id, project_id, dataset_id, source_type, row_counts, period_start, period_end)
                       values (%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                    (tenant.organization_id, tenant.project_id, dataset_id, source_type, json.dumps(row_counts),
                     inspection["period_start"], inspection["period_end"]),
                )
                for role, (file_name, _content) in files.items():
                    cur.execute(
                        """insert into dataset_files
                           (organization_id, project_id, dataset_id, role, file_name, storage_path, row_count)
                           values (%s,%s,%s,%s,%s,%s,%s)""",
                        (tenant.organization_id, tenant.project_id, dataset_id, role, file_name,
                         str(folder / f"{role}.csv"), row_counts[role]),
                    )
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return self.get_dataset(tenant, dataset_id)

    def create_sample_dataset(self, tenant: TenantContext, sample_root: Path):
        files = {role: (f"{role}.csv", (sample_root / f"{role}.csv").read_bytes())
                 for role in ("inventory", "usage", "billing", "sla")}
        return self.create_dataset(tenant, files, "SAMPLE")

    def create_public_dataset(self, tenant: TenantContext, source_root: Path):
        output = self.data_root / "validation" / "prepared" / f"public-{uuid4()}"
        try:
            files = prepare_public_files(source_root, output)
            return self.create_dataset(tenant, files, "PUBLIC")
        finally:
            shutil.rmtree(output, ignore_errors=True)

    def get_dataset(self, tenant: TenantContext, dataset_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """select dataset_id::text, source_type, status, row_counts, period_start, period_end, created_at
                   from datasets where organization_id=%s and project_id=%s and dataset_id=%s""",
                (tenant.organization_id, tenant.project_id, dataset_id),
            )
            dataset = cur.fetchone()
            if not dataset:
                return None
            cur.execute(
                """select role, file_name, row_count from dataset_files
                   where organization_id=%s and project_id=%s and dataset_id=%s order by role""",
                (tenant.organization_id, tenant.project_id, dataset_id),
            )
            dataset["files"] = cur.fetchall()
            return dataset

    def submit_gpu_data_analysis(self, tenant: TenantContext, dataset_id: str, key: str):
        if not self.get_dataset(tenant, dataset_id):
            return None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """insert into jobs (organization_id, project_id, product, operation, idempotency_key, status, dataset_id)
                   values (%s,%s,'gpu-data','ANALYZE',%s,'QUEUED',%s)
                   on conflict (organization_id, idempotency_key)
                   do update set idempotency_key=excluded.idempotency_key
                   returning job_id::text, organization_id::text, project_id::text, product, operation,
                             idempotency_key, status, progress, dataset_id::text, (xmax = 0) created""",
                (tenant.organization_id, tenant.project_id, key, dataset_id),
            )
            job = cur.fetchone()
        created = job.pop("created")
        if created:
            self.redis.lpush("gpu:jobs", json.dumps(job))
        return job

    def get_analysis(self, tenant: TenantContext, dataset_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """select result_id::text, dataset_id::text, job_id::text, status, summary, audit, signals, created_at
                   from analysis_results where organization_id=%s and project_id=%s and dataset_id=%s
                   order by created_at desc limit 1""",
                (tenant.organization_id, tenant.project_id, dataset_id),
            )
            result = cur.fetchone()
            if not result:
                return None
            cur.execute(
                """select artifact_id::text, kind, file_name, mime_type from report_artifacts
                   where organization_id=%s and project_id=%s and result_id=%s order by kind""",
                (tenant.organization_id, tenant.project_id, result["result_id"]),
            )
            result["artifacts"] = cur.fetchall()
            return result

    def get_artifact(self, tenant: TenantContext, artifact_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """select file_name, storage_path, mime_type from report_artifacts
                   where organization_id=%s and project_id=%s and artifact_id=%s""",
                (tenant.organization_id, tenant.project_id, artifact_id),
            )
            return cur.fetchone()

    def create_recommendations(self, tenant: TenantContext, dataset_id: str):
        result = self.get_analysis(tenant, dataset_id)
        if not result:
            return None
        if result["status"] != "SUCCEEDED":
            raise ValueError("数据质量未通过，不能生成优化建议")
        recommendations = build_recommendations(result)
        with self._connect() as conn, conn.cursor() as cur:
            for item in recommendations:
                cur.execute(
                    """insert into optimization_recommendations
                       (organization_id,project_id,result_id,dataset_id,recommendation_key,payload)
                       values (%s,%s,%s,%s,%s,%s::jsonb)
                       on conflict (result_id,recommendation_key) do update set payload=excluded.payload""",
                    (tenant.organization_id, tenant.project_id, result["result_id"], dataset_id,
                     item["recommendation_key"], json.dumps(item, ensure_ascii=False)),
                )
        return self.get_recommendations(tenant, dataset_id)

    def get_recommendations(self, tenant: TenantContext, dataset_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """select recommendation_id::text, payload, created_at
                   from optimization_recommendations
                   where organization_id=%s and project_id=%s and dataset_id=%s
                   order by created_at,recommendation_key""",
                (tenant.organization_id, tenant.project_id, dataset_id),
            )
            return [dict(row["payload"], recommendation_id=row["recommendation_id"], created_at=row["created_at"])
                    for row in cur.fetchall()]

    def process_gpu_data_job(self, job):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("update jobs set status='RUNNING', progress=20 where job_id=%s and status='QUEUED'", (job["job_id"],))
            cur.execute("update datasets set status='ANALYZING' where dataset_id=%s", (job["dataset_id"],))
            cur.execute("select storage_path from dataset_files where dataset_id=%s limit 1", (job["dataset_id"],))
            source_dir = Path(cur.fetchone()["storage_path"]).parent
        result_id = str(uuid4())
        output_dir = source_dir / "results" / result_id
        outcome = run_analysis(source_dir, output_dir)
        job_status = "SUCCEEDED" if outcome["status"] == "SUCCEEDED" else "FAILED"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """insert into analysis_results
                   (organization_id,project_id,result_id,dataset_id,job_id,status,summary,audit,signals)
                   values (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",
                (job["organization_id"], job["project_id"], result_id, job["dataset_id"], job["job_id"],
                 outcome["status"], json.dumps(outcome["summary"]), json.dumps(outcome["audit"], ensure_ascii=False),
                 json.dumps(outcome["signals"], ensure_ascii=False)),
            )
            for artifact in outcome["artifacts"]:
                path = Path(artifact["path"])
                cur.execute(
                    """insert into report_artifacts
                       (organization_id,project_id,result_id,kind,file_name,storage_path,mime_type)
                       values (%s,%s,%s,%s,%s,%s,%s)""",
                    (job["organization_id"], job["project_id"], result_id, artifact["kind"], path.name,
                     str(path), artifact["mime_type"]),
                )
            cur.execute("update datasets set status=%s where dataset_id=%s", (outcome["status"], job["dataset_id"]))
            cur.execute(
                """update jobs set status=%s, progress=100, public_error_code=%s where job_id=%s""",
                (job_status, None if job_status == "SUCCEEDED" else "DATA_QUALITY_BLOCKED", job["job_id"]),
            )

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
    store = PostgresStore(os.environ["DATABASE_URL"], os.environ["REDIS_URL"], os.environ.get("DATA_ROOT", "/data"))
    store.ensure_gpu_data_schema()
    return store
