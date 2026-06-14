# Distributed Task Queue

A simplified Celery-like distributed task queue built with Python and Redis. Jobs are submitted via API, queued in Redis, and executed by independent worker processes with automatic retries, priority ordering, and concurrent processing.

## Architecture

```
Client → FastAPI → Redis (queue) → Worker 1 → Redis (results)
                                 → Worker 2
                                 → Worker 3
```

### Stack
- **FastAPI** — job submission and status API
- **Redis** — message broker (BRPOP-based FIFO queues) and result store
- **Python multiprocessing** — workers run as independent processes

## Design Decisions

**BRPOP as the message primitive** — workers use Redis `BRPOP` to pull jobs. `BRPOP` blocks until a job is available rather than polling in a tight loop — this is CPU-efficient and guarantees exactly-once delivery. Redis atomically pops the item and hands it to one consumer, eliminating race conditions between concurrent workers without any application-level locking.

**Priority via multi-queue** — instead of a heap or sorted set, priority is implemented as three separate Redis lists (`task_queue:high`, `task_queue:medium`, `task_queue:low`). `BRPOP` accepts multiple keys and checks them in order, so high-priority jobs are always dequeued first. This is the same pattern used by Sidekiq at companies like Shopify and GitHub. A sorted set (`ZADD`/`ZPOPMIN`) would support continuous priority scores but loses blocking semantics, requiring wasteful polling.

**Exponential backoff on retries** — failed jobs are retried with exponentially increasing delays (1s, 2s, 4s) up to a configurable maximum. This prevents a failing external dependency from being hammered with retry attempts while still recovering automatically from transient failures. After exhausting retries, the job is marked permanently failed.

**Stateless workers** — workers are independent processes with no shared state. Scaling is as simple as starting more `python worker.py` processes. Each worker pulls from the same Redis queues, and Redis's atomic operations ensure no job is processed twice. Workers can be added or removed at any time without coordination.

**Job state machine** — every job follows a strict state progression: `pending → running → completed` or `pending → running → pending (retry) → ... → failed`. State is stored in Redis alongside the job metadata, queryable at any time via the status API.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs` | Submit a job |
| GET | `/jobs/{job_id}` | Check job status and result |

### Submit a job
```bash
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "add", "args": {"a": 5, "b": 3}}'
```

```json
{"job_id": "c5a3d1a5-bb70-433c-ae10-484f923d2cb6", "status": "pending", "priority": "medium"}
```

### Submit with priority
```bash
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "add", "args": {"a": 1, "b": 1}, "priority": "high"}'
```

### Check status
```bash
curl http://localhost:8001/jobs/c5a3d1a5-bb70-433c-ae10-484f923d2cb6
```

```json
{
  "job_id": "c5a3d1a5-bb70-433c-ae10-484f923d2cb6",
  "status": "completed",
  "result": 8,
  "priority": "medium"
}
```

### Test retry logic
```bash
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "flaky", "args": {"message": "hello"}}'
```

The `flaky` task fails 70% of the time, triggering automatic retries with exponential backoff.

## Available Tasks

| Task | Args | Description |
|------|------|-------------|
| `add` | `{"a": int, "b": int}` | Addition with 2s simulated latency |
| `multiply` | `{"a": int, "b": int}` | Multiplication with 3s latency |
| `factorial` | `{"n": int}` | Factorial with 2s latency |
| `flaky` | `{"message": str}` | Fails 70% of the time — tests retry logic |

## Running Locally

**Prerequisites:** Python 3.11+, Docker Desktop

```bash
git clone https://github.com/rbharg7/task-queue
cd task-queue
pip install -r requirements.txt
cp .env.example .env
docker compose up -d

# Terminal 1 — start one or more workers
python worker.py

# Terminal 2 — start the API
uvicorn api:app --reload --port 8001
```

### Scaling workers
```bash
# Each worker pulls from the same queue — no coordination needed
python worker.py  # Terminal 1
python worker.py  # Terminal 2
python worker.py  # Terminal 3
```

### Testing priority ordering
```bash
# Stop the worker first, then submit jobs in order
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "add", "args": {"a": 1, "b": 1}, "priority": "low"}'

curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "add", "args": {"a": 2, "b": 2}, "priority": "medium"}'

curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"task_name": "add", "args": {"a": 3, "b": 3}, "priority": "high"}'

# Start the worker — processes 3+3 first, then 2+2, then 1+1
python worker.py
```

## Project Structure

```
task-queue/
├── api.py           # FastAPI — submit jobs, check status
├── worker.py        # Pulls jobs from Redis, executes with retries
├── job_queue.py     # Queue operations (enqueue, dequeue, requeue)
├── tasks.py         # Task function registry
├── models.py        # Pydantic schemas
└── docker-compose.yml
```
