import redis
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

QUEUE_KEYS = {
    "high": "task_queue:high",
    "medium": "task_queue:medium",
    "low": "task_queue:low",
}

def enqueue(task_name: str, args: dict, priority: str = "medium", max_retries: int = 3) -> str:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "task_name": task_name,
        "args": args,
        "status": "pending",
        "priority": priority,
        "retries": 0,
        "max_retries": max_retries
    }
    queue_key = QUEUE_KEYS.get(priority, QUEUE_KEYS["medium"])
    r.set(f"job:{job_id}", json.dumps(job))
    r.lpush(queue_key, job_id)
    return job_id

def dequeue() -> dict | None:
    # BRPOP checks keys in order — high first, then medium, then low
    result = r.brpop(
        [QUEUE_KEYS["high"], QUEUE_KEYS["medium"], QUEUE_KEYS["low"]],
        timeout=1
    )
    if result is None:
        return None
    job_id = result[1]
    job_data = r.get(f"job:{job_id}")
    if job_data is None:
        return None
    return json.loads(job_data)

def requeue(job_id: str):
    job_data = r.get(f"job:{job_id}")
    if job_data:
        job = json.loads(job_data)
        priority = job.get("priority", "medium")
        queue_key = QUEUE_KEYS.get(priority, QUEUE_KEYS["medium"])
        r.lpush(queue_key, job_id)

def update_job(job_id: str, status: str, result=None, error=None, retries=None):
    job_data = r.get(f"job:{job_id}")
    if job_data:
        job = json.loads(job_data)
        job["status"] = status
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        if retries is not None:
            job["retries"] = retries
        r.set(f"job:{job_id}", json.dumps(job))

def get_job(job_id: str) -> dict | None:
    job_data = r.get(f"job:{job_id}")
    if job_data:
        return json.loads(job_data)
    return None