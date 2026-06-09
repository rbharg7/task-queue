import time
import traceback
from job_queue import dequeue, update_job, requeue
from tasks import TASK_REGISTRY

def run_worker():
    print("Worker started. Waiting for jobs...")
    while True:
        job = dequeue()
        if job is None:
            continue

        job_id = job["job_id"]
        task_name = job["task_name"]
        args = job["args"]
        retries = job.get("retries", 0)
        max_retries = job.get("max_retries", 3)

        print(f"Processing job {job_id}: {task_name}({args}) [attempt {retries + 1}]")
        update_job(job_id, "running")

        try:
            func = TASK_REGISTRY.get(task_name)
            if func is None:
                raise ValueError(f"Unknown task: {task_name}")

            result = func(**args)
            update_job(job_id, "completed", result=result)
            print(f"Job {job_id} completed: {result}")

        except Exception as e:
            if retries < max_retries:
                wait = 2 ** retries  # 1s, 2s, 4s
                print(f"Job {job_id} failed (attempt {retries + 1}/{max_retries + 1}). Retrying in {wait}s...")
                update_job(job_id, "pending", error=str(e), retries=retries + 1)
                time.sleep(wait)
                requeue(job_id)
            else:
                update_job(job_id, "failed", error=str(e))
                print(f"Job {job_id} permanently failed after {max_retries + 1} attempts: {e}")

if __name__ == "__main__":
    run_worker()