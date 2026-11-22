# Writing custom jobs and DAGs (Airflow reference)

> **You are between pipeline stages.** This is the "how do I add my own
> thing to the platform" reference: the job contract, writing job scripts,
> creating/editing/deleting DAGs in Airflow, running them, and reading
> status/logs. You only need this once — then stages 4–7 are just files.

## 1. Where you go and what login you need

| What | URL | Login |
|------|-----|-------|
| Airflow UI (DAGs, Grid, task logs) | <http://localhost:2405> | user `airflow`, password `airflow` (from `.env`: `_AIRFLOW_WWW_USER_*`) |
| Airflow REST API | `http://localhost:2405/api/v2/…` | Bearer JWT token (below) |
| OpenAPI docs (API explorer) | <http://localhost:2405/docs> | after login, "Authorize" with your token |
| CLI | `docker compose run --rm airflow-cli airflow …` | n/a (runs as the airflow user) |
| Task-graph (Flower) | <http://localhost:5555> | none |

**REST token** (for scripts / `curl`):

```bash
make token     # POST /auth/token with airflow:airflow -> /tmp/.airflow-ml-token
curl -s http://localhost:2405/api/v2/dags \
  -H "Authorization: Bearer $(cat /tmp/.airflow-ml-token)" | python3 -m json.tool
```

Or from the UI: any page → top-right **profile** → copy the API token.

## 2. The job contract (env vars given to every job)

`dags/jobtask.py → job_task()` is the single place that defines how a job
container is built. Every task created with it gets:

| Category | Env vars | Value on this stack |
|----------|----------|---------------------|
| Run identity | `JOB_ID`, `RUN_ID` | task id; `{{ run_id }}` of the DAG run |
| S3 / MinIO | `S3_ENDPOINT`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | `http://minio:9000`, `ml-artifacts`, `us-east-1`, `minioadmin`, `minioadmin` |
| DeepLake chain | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ENDPOINT_URL` | same values (the DeepLake S3 provider reads this chain) |
| Platform endpoints | `DEEPLAKE_DATASET`, `EMBEDDING_TENSOR`, `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_DISTANCE`, `TRITON_HTTP_URL`, `TRITON_GRPC_URL`, `TRITON_MODEL_NAME`, `MLFLOW_TRACKING_URI` | container-side URLs (see [index quick reference](index.md#quick-reference-urls-and-credentials)) |
| Per-task extras | whatever your DAG passes in `extra_env=` | e.g. `DEEPLAKE_VOC12`, `EPOCHS` |

Container mechanics (fixed, don't fight them):

- **Image:** `ml-jobrunner:latest` (CPU) or `ml-jobrunner-gpu:latest` via
  `gpu_job_task()` — **no ENTRYPOINT**; the operator always runs the explicit
  command `python /runner.py /opt/airflow/dags/jobs/<script>` (this is also
  why the same image works as a Ray node).
- **Mounts:** `dags/` → `/opt/airflow/dags` (read-only; your job script must
  live in `dags/jobs/`) and `triton-models/` → `/models` (the live Triton
  model repository — jobs can stage/load models exactly like `deploy_model.py`).
- **Network:** `airflow-ml-net` → reach `minio`, `mlflow`, `qdrant`,
  `triton` by name (and the outside internet via NAT).
- **Lifecycle:** `auto_remove="force"` (`--rm`) → the container is removed
  on exit (success or failure); the full stdout/stderr is still captured in
  the Airflow task log and artifacts land in S3, so the audit trail is
  intact without leaving container layers on disk. `timeout=3600` per task
  (bump per-task, e.g. `timeout=7200` for training).
- **GPU:** `gpu_job_task(...)` adds `device_requests=[DeviceRequest(count=1,
  capabilities=[["gpu"]])]` (= `--gpus`) + `shm_size=16g`; the host needs
  nvidia-container-toolkit (present on this machine — verified with
  `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`).

## 3. Writing a custom job script

A job is a plain Python file dropped in `dags/jobs/`. Rules that make it
portable (DockerOperator today, Ray/K8s tomorrow):

1. **Env-driven.** Read every endpoint/credential from `os.environ` (the
   contract above) — never hardcode `localhost` URLs.
2. **stdio only.** `print()` goes to the task log; no sockets, no UI, no
   docker-py, no `docker.sock`.
3. **Fail loud.** `sys.exit("message")` (or raise) → red task. Never
   swallow errors.
4. **Publish artifacts to S3** (`boto3` with the `S3_*` env) and/or
   DeepLake/MLflow — that's how other tasks (and you) consume results.

Template:

```python
"""One-line: what this job does and which run artifacts it publishes."""
import json, os, sys

import boto3

S3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"],
                  aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                  aws_secret_access_key=os.environ["S3_SECRET_KEY"],
                  region_name=os.environ.get("S3_REGION", "us-east-1"))
RUN_ID = os.environ["RUN_ID"]

def main():
    # ... your work: read inputs from S3/DeepLake, compute, ...
    out = {"ran": RUN_ID, "result": 42}
    S3.put_object(Bucket=os.environ["S3_BUCKET"], Key=f"data/{RUN_ID}/my_job.json",
                  Body=json.dumps(out).encode())
    print(f"MY_JOB OK: {out}")   # this line lands in the task log

if __name__ == "__main__":
    main()
```

Service clients from inside a job are one-liners — full patterns in
[05-data-access.md](05-data-access.md) (boto3, `deeplake`, `qdrant_client`,
`tritonclient`, `mlflow`).

## 4. Creating a DAG

Create `dags/my_pipeline.py` (the repo's `dags/` dir is bind-mounted into
Airflow and auto-scanned — **no deploy step**):

```python
from datetime import datetime
from airflow import DAG
from jobtask import job_task, gpu_job_task          # shared helpers, same folder

with DAG(
    dag_id="my_pipeline",
    schedule=None,                                   # manual triggers only
    start_date=datetime(2026, 8, 26),
    catchup=False,
    tags=["mine"],
) as dag:
    a = job_task("my_job_a.py", job_id="job_a",
                 extra_env={"MY_KNOB": "1"}, timeout=3600)
    b = job_task("my_job_b.py", job_id="job_b")
    c = gpu_job_task("train_gpu.py", job_id="train", timeout=7200)  # --gpus
    a >> b >> c                                      # chain;  b + c style: [b, c] >> d
```

- **Adding a python script as a task** = `job_task("<script>.py", job_id=…)`,
  the script in `dags/jobs/`. `extra_env` adds task-specific knobs; `image=`
  on `job_task` overrides the runner image if you ever need a third image.
- **Custom (non-Docker) tasks** (pure-Airflow Python, no container): use
  `PythonOperator`/`EmptyOperator` freely in the same DAG — `verify_dataset`
  in `ml_pipeline_example.py` is exactly that (it checks S3 from the
  scheduler).
- **Schedules:** `schedule=None` + manual trigger (this stack's default); or
  a cron string, e.g. `schedule="0 2 * * *"`, after `make unpause`.

## 5. Saving, editing, deleting DAGs

In this repo layout the **file in `dags/` is the source of truth**:

- **Save/create:** write the file (editor or copy) → the DAG processor
  picks it up within ~30 s (watch `airflow dags list` or the UI).
- **Edit:** change the file → on next parse the DAG is re-registered
  (schedule, tasks, params); in-flight runs finish with the code they
  started with.
- **Airflow 3 UI editor:** the DAG detail page also has a **Deploy** action
  that lets you edit the file in the browser and save it back to `dags/` —
  handy for one-liners; for anything non-trivial prefer the repo (it's under
  your version control and the job containers read the same files).
- **Delete:** `rm dags/my_pipeline.py` — it disappears from the UI on the
  next scan. Historical runs stay in the database (Airflow keeps run history
  for removed DAGs; they're harmless and hidden from the main list).

Sanity checks:

```bash
docker compose run --rm airflow-cli airflow dags list                 # parsed DAGs
docker compose run --rm airflow-cli airflow dags list-import-errors    # parse failures
```

## 6. Running a DAG

```bash
DAG_ID=my_pipeline make unpause     # DAGs start paused
DAG_ID=my_pipeline make trigger     # starts a run now (logical_date = now)
DAG_ID=my_pipeline make runinfo     # latest runs + per-task states
```

UI equivalents: **Browse → DAGs → `my_pipeline`** → the green **▶ Trigger**
button (or pause/unpause via the switch). The run's **Grid** view shows every
task per run as a colored cell.

## 7. Checking run status and logs

**Status, three levels:**

1. **UI Grid** (DAG detail page): per-task cells — grey=upcoming,
   blue=running, green=success, red=failed, orange=upstream-failed.
2. **CLI** — `DAG_ID=… make runinfo` (wraps `scripts/runinfo.py`: runs +
   task states), or the REST API:

   ```bash
   T=$(cat /tmp/.airflow-ml-token)
   curl -s "http://localhost:2405/api/v2/dags/my_pipeline/dagRuns" -H "Authorization: Bearer $T"
   ```
3. **Job-level** — the task log's final `… OK:` / `sys.exit` line is the
   ground truth (jobs print exactly what they published).

**Logs, three places (same content, different UX):**

- **UI:** task cell → **Details → Logs** (auto-scroll; also "download log").
- **Docker** (live tail while the task is in flight): job containers run
  with `--rm` and are removed on exit, so `docker logs` works only while
  the job is running:

  ```bash
  docker ps --filter ancestor=ml-jobrunner --filter ancestor=ml-jobrunner-gpu --format '{{.ID}} {{.Status}}'
  docker logs -f <container-id>                 # live tail during the run
  ```
  After the task finishes, the Airflow task log (above) holds the same
  content permanently.
- **Service logs** (scheduler/worker/minio/triton…): `make logs` or
  `SERVICE=airflow-scheduler make logs`.

**Debugging a failed job** = open its Airflow task log; the job's stdout is
the full story because jobs are plain `print`-driven scripts (the exit code
shows in the task instance state / `make runinfo`). To post-mortem a job
container's filesystem after a crash, set `auto_remove="never"` in
`dags/jobtask.py` for that run.

## 8. Cheat sheet

```bash
DAG_ID=detection_voc12 make unpause && DAG_ID=detection_voc12 make trigger
DAG_ID=detection_voc12 make runinfo
docker compose run --rm airflow-cli airflow dags trigger detection_voc12   # same thing, CLI form
docker compose run --rm airflow-cli airflow dags test detection_voc12      # run in-process, no container
# API:
T=$(cat /tmp/.airflow-ml-token)
curl -s http://localhost:2405/api/v2/dags/detection_voc12 -H "Authorization: Bearer $T"
curl -s "http://localhost:2405/api/v2/dags/detection_voc12/dagRuns?limit=3" -H "Authorization: Bearer $T"
```

**Next:** [05 — accessing MinIO / DeepLake / Qdrant from a job](05-data-access.md).