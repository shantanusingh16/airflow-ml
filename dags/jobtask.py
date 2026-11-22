"""Shared helpers for job-container tasks (DockerOperator) and S3 checks.

Importable from any DAG file in this folder (Airflow adds the dags dir to
sys.path). Config is resolved at parse time from env (docker-compose / .env).
"""
from __future__ import annotations

import json
import os

from airflow.exceptions import AirflowException
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.docker.operators.docker import DockerOperator

PROJECT_DIR = os.environ.get("AIRFLOW_PROJ_DIR")
if not PROJECT_DIR:
    raise AirflowException(
        "AIRFLOW_PROJ_DIR is not set (or is empty). Set it in .env / the docker-compose "
        "environment to the host path of the airflow-ml project directory; it is used to "
        "bind-mount dags/, config/ and triton-models/ into job containers."
    )

S3_BUCKET = os.environ.get("S3_BUCKET", "ml-artifacts")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
S3_CONN_ID = os.environ.get("S3_CONN_ID", "aws_default")

JOB_RUNNER_IMAGE = os.environ.get("JOB_RUNNER_IMAGE", "ml-jobrunner:latest")
JOB_NETWORK = os.environ.get("JOB_NETWORK", "airflow-ml-net")
# CUDA variant of the job image (jobrunner/Dockerfile.gpu): same contract as
# the CPU image plus torch/ultralytics, used via gpu_job_task()
JOB_GPU_IMAGE = os.environ.get("JOB_GPU_IMAGE", "ml-jobrunner-gpu:latest")

# In-container path of the DAG folder (mounted read-only into job containers)
JOBS_IN_CONTAINER = "/opt/airflow/dags/jobs"

# Host dir (bind-mounted into job containers AND the triton service) holding
# the Triton model repository: <PROJECT_DIR>/triton-models -> /models
TRITON_MODEL_STORE = f"{PROJECT_DIR}/triton-models"

# ML platform services (container-side endpoints; see .env)
DEEPLAKE_DATASET = os.environ.get("DEEPLAKE_DATASET", f"s3://{S3_BUCKET}/deeplake/feature_ds")
# Name of the DeepLake tensor whose samples are the embeddings indexed into Qdrant
EMBEDDING_TENSOR = os.environ.get("EMBEDDING_TENSOR", "features")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "feature_vectors")
QDRANT_DISTANCE = os.environ.get("QDRANT_DISTANCE", "cosine")
TRITON_HTTP_URL = os.environ.get("TRITON_HTTP_URL", "http://triton:8005")
TRITON_GRPC_URL = os.environ.get("TRITON_GRPC_URL", "triton:8000")
TRITON_MODEL_NAME = os.environ.get("TRITON_MODEL_NAME", "linreg_onnx")
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")


class _GpuDockerOperator(DockerOperator):
    """DockerOperator that requests the host GPU at execution time.

    Airflow 3.3.1 + docker provider: constructing DockerOperator with
    ``device_requests=[docker.types.DeviceRequest(...)]`` breaks the
    scheduler's DAG-version resolution for the whole DAG — manual runs end
    "success" with ZERO task instances (the run is never associated with a
    DAG version). File parsing and the stored serialized version are both
    fine (deserializes to full task lists in fresh processes); the failure
    only manifests in the long-running scheduler process.

    Workaround: serialize nothing GPU-related. The DeviceRequest is built
    inside execute(), right before the container is created. ``gpu_count``
    is a plain int; even if operator serialization drops it, the class
    default (1) is correct on this single-GPU host.
    """

    gpu_count: int = 1

    def __init__(self, *, gpu_count: int = 1, **kwargs):
        self.gpu_count = gpu_count
        super().__init__(**kwargs)

    def execute(self, context):
        from docker.types import DeviceRequest

        self.device_requests = [DeviceRequest(count=self.gpu_count, capabilities=[["gpu"]])]
        return super().execute(context)


def s3_hook() -> S3Hook:
    """S3Hook pointed at MinIO via the `aws_default` Airflow connection."""
    return S3Hook(aws_conn_id=S3_CONN_ID)

def _job_env(job_id: str, extra_env: dict | None = None) -> dict:
    """Env for every job container: identity + S3 chain + platform endpoints."""
    env = {
        "JOB_ID": job_id,
        "RUN_ID": "{{ run_id }}",
        "S3_ENDPOINT": S3_ENDPOINT,
        "S3_BUCKET": S3_BUCKET,
        "S3_REGION": S3_REGION,
        "S3_ACCESS_KEY": S3_ACCESS_KEY,
        "S3_SECRET_KEY": S3_SECRET_KEY,
        # DeepLake S3Provider env-var chain (endpoint-aware MinIO access)
        "AWS_ACCESS_KEY_ID": S3_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": S3_SECRET_KEY,
        "AWS_REGION": S3_REGION,
        "AWS_ENDPOINT_URL": S3_ENDPOINT,
        # ML platform service endpoints / knobs
        "DEEPLAKE_DATASET": DEEPLAKE_DATASET,
        "EMBEDDING_TENSOR": EMBEDDING_TENSOR,
        "QDRANT_URL": QDRANT_URL,
        "QDRANT_COLLECTION": QDRANT_COLLECTION,
        "QDRANT_DISTANCE": QDRANT_DISTANCE,
        "TRITON_HTTP_URL": TRITON_HTTP_URL,
        "TRITON_GRPC_URL": TRITON_GRPC_URL,
        "TRITON_MODEL_NAME": TRITON_MODEL_NAME,
        "MLFLOW_TRACKING_URI": MLFLOW_TRACKING_URI,
    }
    if extra_env:
        env.update(extra_env)
    return env


def _job_mounts() -> list[dict]:
    return [
        {"type": "bind", "source": f"{PROJECT_DIR}/dags", "target": "/opt/airflow/dags", "read_only": True},
        # Shared Triton model repository (the triton service mounts the same host dir)
        {"type": "bind", "source": TRITON_MODEL_STORE, "target": "/models"},
    ]

def job_task(
    script: str,
    *,
    job_id: str,
    extra_env: dict | None = None,
    image: str | None = None,
    device_requests=None,
    shm_size: str | None = None,
    timeout: int = 3600,
) -> DockerOperator:
    """DockerOperator task: run ``dags/jobs/<script>`` in a job-runner image.

    ``image`` overrides the runner image (e.g. the CUDA build
    ``ml-jobrunner-gpu:latest``); ``device_requests`` / ``shm_size`` pass
    through to the Docker SDK (``None`` = unset) for GPU / torch jobs.
    """
    return DockerOperator(
        task_id=job_id,
        image=image or JOB_RUNNER_IMAGE,
        # Full explicit command: the image has no ENTRYPOINT (dual-mode image
        # that also serves as a Ray node, where the orchestrator sets the command).
        command=["python", "/runner.py", f"{JOBS_IN_CONTAINER}/{script}"],
        environment=_job_env(job_id, extra_env),
        mounts=_job_mounts(),
        # Join the compose network so the container can reach minio/mlflow/qdrant/triton
        network_mode=JOB_NETWORK,
        # --rm: the container is removed on exit (success OR failure). The full
        # stdout/stderr is still streamed into the Airflow task log, and every
        # job publishes its manifests/artifacts to S3, so the audit trail is
        # intact without persisting container layers. Set "never" instead if
        # you need to post-mortem a job container's filesystem.
        auto_remove="force",
        xcom_all=False,
        device_requests=device_requests,
        shm_size=shm_size,
        timeout=timeout,
    )


def gpu_job_task(
    script: str,
    *,
    job_id: str,
    extra_env: dict | None = None,
    image: str | None = None,
    device_count: int = 1,
    shm_size: str = "16g",
    timeout: int = 3600,
) -> _GpuDockerOperator:
    """job_task() variant for CUDA training/export/eval jobs.

    Same env / mounts / network as a regular job, plus the host GPU(s) and
    extra /dev/shm for torch DataLoader workers. The GPU is requested via a
    DeviceRequest built in execute() by ``_GpuDockerOperator`` (NOT in the
    serialized operator kwargs — that breaks the scheduler on Airflow 3.3.1,
    see the class docstring). The host must run nvidia-container-toolkit
    (check: ``docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04
    nvidia-smi``).
    """
    return _GpuDockerOperator(
        task_id=job_id,
        image=image or JOB_GPU_IMAGE,
        # Full explicit command: the image has no ENTRYPOINT (dual-mode image
        # that also serves as a Ray node, where the orchestrator sets the command).
        command=["python", "/runner.py", f"{JOBS_IN_CONTAINER}/{script}"],
        environment=_job_env(job_id, extra_env),
        mounts=_job_mounts(),
        # Join the compose network so the container can reach minio/mlflow/qdrant/triton
        network_mode=JOB_NETWORK,
        # --rm: same contract as job_task() — removed on exit (success OR
        # failure); full log is streamed to the Airflow task log and artifacts
        # are published to S3, so nothing is lost for audit/provenance.
        auto_remove="force",
        xcom_all=False,
        shm_size=shm_size,
        timeout=timeout,
        gpu_count=device_count,
    )


def verify_dataset(**context) -> dict:
    """Airflow-side check that the job container actually published a dataset."""
    run_id = context["run_id"]
    prefix = f"data/{run_id}/"
    hook = s3_hook()

    keys = hook.list_keys(S3_BUCKET, prefix=prefix)
    if not keys:
        raise AirflowException(f"no objects under s3://{S3_BUCKET}/{prefix} — job published nothing")

    train = hook.head_object(f"{prefix}train.csv", bucket_name=S3_BUCKET)
    if not train or train.get("ContentLength", 0) == 0:
        raise AirflowException(f"s3://{S3_BUCKET}/{prefix}train.csv missing or empty")
    manifest_key = f"{prefix}manifest.json"
    manifest = json.loads(hook.read_key(manifest_key, bucket_name=S3_BUCKET)) if hook.check_for_key(
        manifest_key, bucket_name=S3_BUCKET
    ) else None
    print(f"dataset ok: {len(keys)} objects, train.csv={train['ContentLength']} bytes, manifest={manifest}")
    return {"objects": len(keys), "train_csv_bytes": train["ContentLength"], "manifest": manifest}