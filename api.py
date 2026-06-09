from fastapi import FastAPI, HTTPException
from models import JobSubmit, JobResponse, JobStatus
from job_queue import enqueue, get_job

app = FastAPI()

@app.post("/jobs", response_model=JobResponse)
def submit_job(body: JobSubmit):
    job_id = enqueue(body.task_name, body.args, priority=body.priority.value)
    return JobResponse(job_id=job_id, status=JobStatus.PENDING, priority=body.priority.value)

@app.get("/jobs/{job_id}", response_model=JobResponse)
def check_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=job["job_id"],
        status=job["status"],
        result=job.get("result"),
        error=job.get("error"),
        priority=job.get("priority")
    )