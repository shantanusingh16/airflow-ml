# airflow-ml

Local MLOps stack: **Apache Airflow 3.3.1** (Docker) orchestrating **custom ML
job containers** (via `DockerOperator`) with **S3 storage emulated by MinIO**
— all running on your machine with Docker Compose.

```
                        +----------------------------- host machine ---------------------------+
                        |                                                                     |
   UI  :2405            |  +----------------+   tasks    +---------------------------+        |
+--------------------+   |  |               +----------->|  airflow-worker (celery)  |        |
|   Airflow web UI   |   |  |  postgres 16  |             |                           |  docker|
|   (airflow/airflow)|   |  |  (metadata)   |             +-------------+-------------+  socket|
+--------------------+   |  +--------------+                           | launches jobs       |
                          |  +--------------+                          v                     |
   console :9001          |  |  redis 7.2   |               +------------------------+        |
+--------------------+   |  |  (celery     |             | job-runner container    |        |
|   MinIO console    |   |  |  broker)     |             | ml-jobrunner:latest     |        |
| (minioadmin/...)   |   |  +--------------+             | python /runner.py job.py|        |
+--------------------+   |                          +---+------------------------+        |
   S3 API  :9000          |                          |   joins network `airflow-ml-net`   |
+--------------------+   |                          v                                     |
|   MinIO (S3)     |<---+------------------- S3/MinIO hook calls (boto3) --------------+   |
|  bucket:         |   |  +--------------+   in DAG worker / job container             |   |
|  ml-artifacts    |   |  | airflow-     |                                              |   |
+--------------------+   |  | scheduler  |   apiserver :8080 (internal)                  |   |
                          |  | dag-proc   |   dag-processor, triggerer ...               |   |
                          |  +--------------+                                              |   |
                          +----------------------------------------------------------------+
```

## Services

| Service                  | What it is                                                        |
|--------------------------|-------------------------------------------------------------------|
| `postgres`               | Airflow metadata DB (PostgreSQL 16)                               |
| `redis`                  | Celery broker                                                     |
| `minio`                  | Local S3 (API on :9000, console on :9001)                         |
| `minio-init`             | One-shot: creates the `ml-artifacts` bucket                       |
| `airflow-init`           | One-shot: DB migration + web user creation                        |
| `airflow-conn-init`      | One-shot: creates the `aws_default` connection (MinIO as S3)      |
| `airflow-apiserver`      | UI + REST API, host port **2405** (:8080 is taken on this host)   |
| `airflow-dag-processor`  | Picks up DAG files from `dags/`                                   |
| `airflow-scheduler`      | Schedules DAG runs                                                |
| `airflow-worker`         | Celery worker; runs tasks; launches job containers via the docker socket |
| `airflow-triggerer`      | Runs triggered (unscheduled) DAGs / callbacks                     |
| `flower`                 | Optional Celery monitoring UI (:5555) — `docker compose --profile flower up -d flower` |
| `airflow-cli`            | Shell for ad-hoc CLI — `docker compose --profile debug run --rm airflow-cli airflow dags list` |
| `jobrunner`              | Build-only service (`--profile build`) producing `ml-jobrunner:latest` |
| `mlflow`                 | Experiment logging server + UI (host port **5000**); built from `mlflow/Dockerfile` (base `ghcr.io/mlflow/mlflow:v3.15.1` + `boto3`); sqlite state in `mlflow-data`, run artifacts streamed to the `mlflow/` bucket prefix via `--artifacts-destination` (standard `AWS_*` env vars) |
| `qdrant`                 | Vector database for kNN retrieval (HTTP **6333**, gRPC **6334**); state in `qdrant-storage` |
| `triton`                 | Inference server (nvcr.io `tritonserver:26.07-py3` — the full `-py3` variant; `-pyt-python-py3` lacks the onnxruntime backend); CPU-only ONNX Runtime (gRPC **8000**, HTTP **8005**, metrics **8006**); model repo = `triton-models/` |

## Quick start

```bash
# 1. build images (airflow + providers, and the job-runner image)
make build          # or: docker compose build && docker compose --profile build build jobrunner

# 2. start everything
make up

# 3. wait for healthy (usually <1 min)
make status         # all services should be healthy/running

# 4. open the UI
#    http://localhost:2405          (user: airflow / pass: airflow)
#    http://localhost:9001          (MinIO console: minioadmin / minioadmin)

# 5. unpause + trigger the example pipeline
make unpause
make trigger
make runinfo        # poll until the run is success

# 6. inspect artifacts in MinIO
docker compose exec -T minio-init mc ls local/ml-artifacts/data/    # datasets
docker compose exec -T minio-init mc ls local/ml-artifacts/models/  # models + metrics
```

The example DAG (`dags/ml_pipeline_example.py`) does:
1. `generate_dataset` — **job container** publishes `data/<run_id>/{train,test}.csv + manifest.json` to S3
2. `verify_dataset` — Airflow-side `S3Hook` sanity-check (list/head) the objects
3. `train_model` — **job container** reads the CSVs from S3, trains `LinearRegression`,
   publishes `models/<run_id>/{model.pkl, metrics.json}`
4. `collect_metrics` — Airflow-side `S3Hook` reads `metrics.json`, prints + XComs it

## How the pieces talk

- **Airflow → job containers.** `airflow-worker` has the host docker socket mounted,
  so `DockerOperator` launches `ml-jobrunner:latest` on the *host* daemon. The container
  is attached to the compose network `airflow-ml-net` (name set in `.env` → `JOB_NETWORK`),
  can therefore reach `minio` by service name, and gets the DAG folder mounted
  read-only at `/opt/airflow/dags`.
- **Job contract.** `dags/jobtask.py:job_task()` launches `ml-jobrunner:latest` with the full
  explicit command `python /runner.py <job-script.py> [args...]` (the image has **no
  ENTRYPOINT** — it doubles as a Ray node image; see "ML platform services" below). A job is a
  plain Python file in `dags/jobs/`. It receives env vars (`JOB_ID`, `RUN_ID`, `S3_*`, `AWS_*`,
  plus the platform service endpoints from `.env`) and should publish artifacts to S3 under keys
  namespaced by `RUN_ID`.
- **S3 access from Airflow.** DAGs use `S3Hook` with the `aws_default` connection
  (created by `airflow-conn-init`): `endpoint_url=http://minio:9000` + path-style
  addressing in the connection `extra`. Job containers use plain `boto3` with the
  same credentials from env.

## Adding your own ML work

1. **Job** — drop `my_job.py` in `dags/jobs/` (any function; reads/writes S3 via boto3
   using the env vars above). No image change needed unless you need new packages.
2. **Image packages** — add them to `jobrunner/Dockerfile`, then
   `make jobs` to rebuild `ml-jobrunner:latest`.
3. **Pipeline** — copy `dags/ml_pipeline_example.py`; the `job_task(script, job_id=...)`
   helper builds the `DockerOperator` for you (mounts, network, env). Or write your own
   `DockerOperator(image=..., command=..., mounts=[...], network_mode=...)`.
4. New DAGs are picked up automatically by `airflow-dag-processor` (watch for import
   errors: Airflow UI → Browse → Import errors, or
   `docker compose --profile debug run --rm airflow-cli airflow dags list-import-errors`).

## ML platform services (DeepLake / MLflow / Qdrant / Triton)

The stack ships three platform services; every job container gets their container-side
endpoints via `.env` → `x-airflow-common-env` → `dags/jobtask.py`. Host-side equivalents:

| Service | What it is | Host ports |
|---------|------------|------------|
| `mlflow` | Experiment logging server + UI at `http://localhost:5000`; sqlite state in the `mlflow-data` volume; run artifacts (sklearn/ONNX model weights) land in the `mlflow/` prefix of `ml-artifacts` via the server-side artifact proxy (`--artifacts-destination s3://ml-artifacts/mlflow`; the MLflow 3.x S3 store reads standard `AWS_*` env vars). The server's `--allowed-hosts` — the Host headers it accepts, i.e. its DNS-rebinding protection — is configurable via `MLFLOW_ALLOWED_HOSTS`: default = the previous pinned list plus `localhost:*` / `127.0.0.1:*` (any loopback port, so the UI also works on a random published port); behind a reverse proxy or on a differently published port, set the exact `host[:port]` the UI is reached at (e.g. `mlflow.example.com:8443`). A bare `*` must never be set — it allows all hosts and disables the protection. Job containers only need the tracking URI | **5000** |
| `qdrant` | Vector database for kNN retrieval; state in the `qdrant-storage` volume | **6333** (HTTP) / **6334** (gRPC) |
| `triton` | Inference server (CPU-only ONNX Runtime backend, `26.07-py3` image variant); model repository is the project dir `triton-models/` bind-mounted at `/models` in the service *and* in every job container (26.x layout: `config.pbtxt` at the model root, model file under `<name>/1/`; model control via gRPC because the 26.07 HTTP load endpoint is broken) | **8000** (gRPC) / **8005** (HTTP) / **8006** (metrics) |

### The `ml_platform_pipeline` DAG

Chains nine tasks: `generate_dataset` → `verify_dataset` (S3) → `enrich_dataset` (one
**DeepLake** commit per run: tensors + key-value `ds.info` metadata) → `index_embeddings`
(**Qdrant** collection rebuilt from the DeepLake head) → `vector_search` (kNN retrieval,
publishes `analysis/<run_id>/vector_search.json`) → `train_model` (sklearn + **ONNX** export
via skl2onnx; MLflow run `train-<run_id>`) → `deploy_model` (stages ONNX into Triton's shared
model repository; explicit model control over gRPC — Triton 26.x keeps `config.pbtxt` at the
model root (`triton-models/<name>/config.pbtxt`) with the ONNX file under the version dir, and
the 26.07 HTTP `.../load` endpoint 404s, so index/unload/load go through `tritonclient` gRPC)
→ `evaluate` (test set through Triton over gRPC; MLflow run `evaluate-<run_id>`) →
`collect_metrics` (S3 artifact check)

```bash
DAG_ID=ml_platform_pipeline make unpause
DAG_ID=ml_platform_pipeline make trigger
DAG_ID=ml_platform_pipeline make runinfo
```

### Demo pipeline (`voc12_demo`)

Short, demo-friendly run over **PASCAL VOC 2012** that reuses the detection
jobs of the full pipeline and stops before training:

1. `upload_voc12` (CPU) — copies the annotated JPEG+XML pairs from the local
   VOC2012 tree (bind-mounted read-only at `/datasets/voc2012` in the job
   container) to `s3://<bucket>/datasets/voc12/VOC2012/{JPEGImages,
   Annotations}/` and writes `ImageSets/Main/trainval.txt` listing exactly
   the uploaded ids. Idempotent (existing objects with the same size are
   skipped); prints upload/skip counts.
2. `verify_upload` (CPU) — the uploaded prefix has >= `MIN_IMAGES` JPEGs, the
   same count of XMLs, and a `trainval.txt` with a matching line count, so a
   partial upload fails before any GPU time is spent.
3. `ingest_voc12` (CPU) — parses every XML and rebuilds the DeepLake dataset
   `s3://<bucket>/deeplake/voc12` (images, bboxes, classes), publishing
   `data/<run>/voc12_ingest_manifest.json`.
4. `embed_fastdup` (GPU) — fastdup DINOv2 embeddings (576-d) + image
   attributes + duplicate groups committed to DeepLake, and a 4-page PDF
   report at `analysis/<run>/voc12_embed_report.pdf`.
5. `cluster_split` (GPU) — DBSCAN kNN clustering of the embeddings; whole
   clusters are assigned to train/val/test at 70/10/20 (no near-duplicate
   ever crosses a split); split counts are logged and
   `data/<run>/voc12_cluster_manifest.json` + `voc12_split_manifest.json`
   are published.

Trigger (no schedule — manual only), from the Airflow UI (Browse →
`voc12_demo` → trigger) or on a compose stack:

```bash
DAG_ID=voc12_demo make unpause
DAG_ID=voc12_demo make trigger
DAG_ID=voc12_demo make runinfo
```

- `SAMPLE` (per-trigger DAG param; default from the stack env `SAMPLE`,
  else `1000`; `0` = all ~5,138 annotated pairs) sizes the upload: the
  first N ids in sorted order. A non-default value is set per trigger in
  the UI's "Trigger w/ config" form or via the API
  `conf: {"SAMPLE": 200}`; the stack-env default goes in the deployment env
  (`.env` / the factory env block) before the stack starts. `MIN_IMAGES` is
  set to that count automatically (`5000`, the full-pipeline floor, for the
  full set).
- Caveat: `verify_upload` counts **every** JPEG under the shared prefix
  `datasets/voc12/VOC2012/` (shared with the full pipeline), not just what
  this trigger uploaded. If the prefix already holds more JPEGs than the
  current selection (an earlier larger `SAMPLE`, or the full pipeline's
  5,717-image upload), verification fails — and pruning the shared bucket
  is not an option. Keep the prefix empty, or holding only an earlier
  upload of the same or a smaller sample, before triggering the demo.
- The VOC2012 tree must be visible to the job container: staging
  bind-mounts the host dataset read-only into `airflow-worker` at
  `/datasets/voc2012` (the `datasets:` block in `deploy.yaml`) and the shim
  re-exports it into the job container at the same path. The mount source
  default, `VOC_DATASET_HOST_DIR=/datasets/voc2012`, is the in-worker path:
  on the staging stack the shim provides that mapping (the operator confirms
  it during acceptance); on a bare compose host set `VOC_DATASET_HOST_DIR`
  to the real host path of the tree (`JPEGImages/` + `Annotations/`
  required; an image counts only if its XML is present).

### Artifacts

- `data/<run_id>/` — CSVs, `manifest.json`, `deeplake_commit.json` (commit id + `ds.info` snapshot)
- `models/<run_id>/` — `model.pkl`, `model.onnx`, `metrics.json`, `config.pbtxt`, `model_info.json`, `eval_metrics.json`
- `analysis/<run_id>/` — `vector_search.json` (kNN results)
- `mlflow/` — MLflow experiment + run artifacts, inside the `ml-artifacts` bucket
- DeepLake dataset `s3://ml-artifacts/deeplake/feature_ds` — one commit per pipeline run;
  head = newest commit; key-value metadata in `ds.info` persists atomically with each commit

### Vector configuration

- `EMBEDDING_TENSOR` (default `features`) — which DeepLake tensor holds the embeddings to index.
  Embeddings are **pipeline-generated, not model-derived**: any job may commit a numeric
  tensor of arbitrary size/dtype (e.g. a learned embedding layer) and point this at it. The
  vector size is **discovered at index time** from the first sample (uniform size required
  across samples; ragged tensors are rejected), and samples are cast to float32 (Qdrant's only
  vector dtype — non-numeric tensors fail at index time).
- `QDRANT_COLLECTION` (default `feature_vectors`) — collection name. **Rebuilt from scratch on
  every run** so it always mirrors the latest DeepLake head; DeepLake is the source of truth.
- `QDRANT_DISTANCE` (default `cosine`) — vector match type: `cosine` | `euclidean` | `dot` |
  `manhattan` — the complete set of Qdrant core built-in metrics. Custom distance functions
  are **not** supported by qdrant/qdrant; any other value fails fast with the valid set listed.

### Ray compatibility (dual-mode job image)

`ml-jobrunner` is orchestrator-agnostic by design:

- **No ENTRYPOINT** — the image bakes in no command. Airflow's `DockerOperator` passes the
  full explicit command `python /runner.py <job-script>` (see `dags/jobtask.py`); Ray/K8s
  supply their own container command. Note `ray start` is a *launcher* (it exits once the
  GCS/raylet daemons are up), so Ray node commands must keep the process alive explicitly,
  e.g. `sh -c "ray start --head --port=6379 && sleep infinity"`.
- **Pins `ray[default]==2.58.0`** — the image doubles as a Ray node image (`ray[default]`
  adds the dashboard dependencies, so `ray job submit` / the :8265 dashboard work): KubeRay on
  k8s via the reference manifest `ray/raycluster.yaml` (head + 2 workers; push
  `ml-jobrunner:latest` to a registry first — the local tag is not resolvable from k8s), or
  any docker-based Ray deployment:

  ```bash
  docker run -d -p 12655:8265 --shm-size=1g ml-jobrunner:latest \
    sh -c "ray start --head --port=6379 --include-dashboard=true --dashboard-host=0.0.0.0 && sleep infinity"
  ```

- **Job scripts run unmodified on Ray** — they are env-driven, stdio-based, and reach platform
  services by URL (no docker-specific code). On a cluster they may additionally
  `ray.init(address="auto")` to parallelize work across nodes.

### Storage & persistence

- `make down` keeps all named volumes (`postgres-db-volume`, `minio-data`, `mlflow-data`,
  `qdrant-storage`); `docker compose down -v` wipes MLflow state (sqlite + artifacts) and the
  Qdrant collections (S3/DeepLake state survives in `minio-data` / real S3).
- The Triton model repository is a plain project dir `triton-models/` (not a named volume) and
  **always survives `down`** — it is bind-mounted into the `triton` service and into every job
  container, so a model staged by `deploy_model` stays loadable across stack restarts.

## Configuration (`.env`)

| Var | Meaning | Default |
|-----|---------|---------|
| `AIRFLOW_PROJ_DIR` | Host path mapped to `/opt/airflow/dags` + `config/`, AND passed into every airflow-* container so job containers' bind mounts (dags/, config/, triton-models/) resolve on the correct host | required — no default |
| `AIRFLOW_IMAGE_NAME` | Airflow image tag (built by `Dockerfile.airflow`) | `airflow-ml:3.3.1` |
| `AIRFLOW_UID` / `AIRFLOW_GID` | UID:GID to run airflow as (use `id -u`) | `1000:0` |
| `DOCKER_GROUP` | Host docker group (name or numeric GID — numeric works where name lookup fails) | `973` |
| `_AIRFLOW_WWW_USER_USERNAME/PASSWORD` | Web UI login | `airflow/airflow` |
| `AIRFLOW__CORE__FERNET_KEY` | Fernet key for secrets/XCom (regenerate only with a fresh DB) | set |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | MinIO admin creds = S3 creds | `minioadmin/minioadmin` |
| `MINIO_BUCKET` | Artifact bucket created by `minio-init` | `ml-artifacts` |
| `S3_ENDPOINT` / `S3_REGION` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` | S3 config given to DAGs and job containers | MinIO values |
| `S3_CONN_ID` | Airflow connection id for `S3Hook` | `aws_default` |
| `JOB_RUNNER_IMAGE` | Image `DockerOperator` launches | `ml-jobrunner:latest` |
| `JOB_NETWORK` | Compose network name job containers join | `airflow-ml-net` |
| `DEEPLAKE_DATASET` | S3 path of the DeepLake dataset (used by job containers) | `s3://ml-artifacts/deeplake/feature_ds` |
| `EMBEDDING_TENSOR` | DeepLake tensor holding the embeddings indexed into Qdrant | `features` |
| `QDRANT_URL` / `QDRANT_COLLECTION` / `QDRANT_DISTANCE` | Qdrant endpoint / collection / match type (`cosine`\|`euclidean`\|`dot`\|`manhattan`) | `http://qdrant:6333` / `feature_vectors` / `cosine` |
| `TRITON_HTTP_URL` / `TRITON_GRPC_URL` / `TRITON_MODEL_NAME` | Triton endpoints + deployed model name | `http://triton:8005` / `triton:8000` / `linreg_onnx` |
| `MLFLOW_TRACKING_URI` | MLflow tracking endpoint (artifact proxy is on by default — jobs only need this) | `http://mlflow:5000` |
| `MLFLOW_ALLOWED_HOSTS` | Comma-separated Host headers the MLflow server accepts (DNS-rebinding protection); default = the previous pinned list + any port on localhost/127.0.0.1; for a reverse proxy or a differently published UI port set the exact `host[:port]` the UI is reached at (e.g. `mlflow.example.com:8443`); a bare `*` disables the protection and must never be set | `mlflow:5000,localhost:5000,127.0.0.1:5000,localhost,127.0.0.1,localhost:*,127.0.0.1:*` |

## Going to real AWS (or other S3)

1. Change `S3_ENDPOINT`/keys in `.env` (e.g. `https://s3.amazonaws.com`, real IAM keys)
   and re-run `docker compose up -d airflow-conn-init` (recreates `aws_default`
   with path-style config — drop `config_kwargs` from the extra for real AWS, or keep
   it; AWS also accepts path style, virtual-host style is default).
2. Pin `boto3`/region in job scripts (they already read env).
3. For bucket lifecycle/replication, manage via the MinIO console or `mc`.

## Troubleshooting

- **UI on :2405 doesn't come up** — `make logs` on `airflow-apiserver`; the host port
  8080 is used by another container on this machine, which is why this stack uses 2405.
- **`DockerOperator` task fails with docker client errors** — the worker needs
  `/var/run/docker.sock` access: the host user running compose must be in the
  `docker` group (it is: `id` shows group `docker`), and `DOCKER_GROUP` in `.env`
  must be the docker group *name or GID* on the host.
- **Job container can't reach MinIO** — check `docker network inspect airflow-ml-net`
  shows the job container + `minio` attached; job env must contain `S3_ENDPOINT=http://minio:9000`.
- **`S3Hook` errors like "PermanentRedirect" or endpoint issues** — the connection
  must carry `endpoint_url` + path-style `config_kwargs` (done by `airflow-conn-init`);
  re-run it: `docker compose up -d --force-recreate airflow-conn-init`.
- **Stale job-runner image after editing `jobrunner/Dockerfile`** — `make jobs`,
  then new DAG runs pick up the new tag.
- **Wipe everything** (DB + S3 data): `make wipe`.
- **Job containers** — run with `--rm` (`auto_remove="force"`): removed on
  exit (success or failure); the full log lives in the Airflow task log and
  artifacts in S3. To inspect a job container's filesystem after a crash,
  set `auto_remove="never"` in `dags/jobtask.py` for that run.

## Layout

```
airflow-ml/
├── docker-compose.yml      # the whole stack (airflow + minio + mlflow + qdrant + triton)
├── .env                    # config (ports, creds, image tags, platform endpoints)
├── Makefile                # build/up/trigger helpers
├── Dockerfile.airflow      # 3.3.1 + providers (docker, amazon)
├── mlflow/
│   └── Dockerfile           # mlflow server image (base + boto3 for the S3 artifact store)
├── dags/
│   ├── jobtask.py                 # shared DockerOperator/S3 helpers (env, mounts, command)
│   ├── ml_pipeline_example.py     # example DAG (DockerOperator + S3Hook)
│   ├── ml_platform_pipeline.py    # full platform DAG (DeepLake/MLflow/Qdrant/Triton)
│   └── jobs/                      # job scripts run inside job-runner containers
│       ├── generate_dataset.py
│       ├── train_model.py         # + ONNX export + MLflow "train" batch
│       ├── enrich_dataset.py      # DeepLake commit + kv metadata
│       ├── index_embeddings.py    # DeepLake head -> Qdrant collection
│       ├── vector_search.py       # kNN retrieval -> analysis artifact
│       ├── deploy_model.py        # stage ONNX into Triton, gRPC explicit load + config verify
│       └── evaluate.py            # Triton gRPC eval + MLflow "evaluate" batch
├── ray/
│   └── raycluster.yaml      # KubeRay reference scaffold (ml-jobrunner as Ray node image)
├── triton-models/           # Triton model repository (bind-mounted into triton + job containers)
├── jobrunner/
│   ├── Dockerfile           # ml-jobrunner image (ML stack + ray; no ENTRYPOINT)
│   ├── Dockerfile.gpu       # ml-jobrunner-gpu (same contract + torch CUDA + ultralytics)
│   └── runner.py            # runs a job script with env + S3 access
├── examples/detection/      # runnable VOC2012 YOLO11 example (jobs + DAG + scripts)
└── docs/detection-example/  # guide: ingestion -> enrichment -> ... -> inference
```

## References

- Airflow 3 docker-stack guide: https://airflow.apache.org/docs/docker-stack/latest/
- Airflow 3 REST API: `http://localhost:2405/docs` (OpenAPI)
- DockerOperator: https://airflow.apache.org/docs/apache-airflow-providers-docker/stable/operators/docker.html
- S3Hook: https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/hooks/s3/index.html
- MinIO + Airflow S3Hook: https://min.io/docs/minio/linux/from-the-field/using-minio-as-s3-compatible-storage-with-apache-airflow.html
- Detection example guide (VOC2012 + YOLO11 + CUDA + Triton): `docs/detection-example/index.md`