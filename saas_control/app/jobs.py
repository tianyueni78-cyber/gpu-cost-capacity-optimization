from dataclasses import dataclass, replace
from enum import Enum
from uuid import uuid4

from .domain import Product, TenantContext


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TRANSITIONS = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(), JobStatus.FAILED: set(), JobStatus.CANCELLED: set(),
}


@dataclass(frozen=True)
class Job:
    job_id: str
    organization_id: str
    project_id: str
    product: Product
    operation: str
    idempotency_key: str
    status: JobStatus = JobStatus.QUEUED


class JobService:
    def __init__(self):
        self._jobs = {}
        self._keys = {}

    def submit(self, context: TenantContext, product: Product, operation: str, idempotency_key: str):
        if not operation or not idempotency_key:
            raise ValueError("任务操作和幂等键不能为空")
        tenant_key = (context.organization_id, idempotency_key)
        if tenant_key in self._keys:
            return self._jobs[self._keys[tenant_key]]
        job = Job(str(uuid4()), context.organization_id, context.project_id, product, operation, idempotency_key)
        self._jobs[job.job_id] = job
        self._keys[tenant_key] = job.job_id
        return job

    def transition(self, job_id: str, status: JobStatus):
        job = self._jobs[job_id]
        if status not in _TRANSITIONS[job.status]:
            raise ValueError("非法任务状态转换")
        updated = replace(job, status=status)
        self._jobs[job_id] = updated
        return updated
