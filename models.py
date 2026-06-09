from pydantic import BaseModel
from enum import Enum
from typing import Any

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class JobSubmit(BaseModel):
    task_name: str
    args: dict = {}
    priority: Priority = Priority.MEDIUM

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: Any = None
    error: str | None = None
    priority: str | None = None