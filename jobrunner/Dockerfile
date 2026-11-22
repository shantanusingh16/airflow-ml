# Job-runner image: the shared workload image for the airflow-ml stack.
#
# Dual-mode, orchestrator-agnostic:
#   1. Airflow DockerOperator jobs — the DAG passes the full command:
#        python /runner.py <job-script.py> [job-args ...]
#      (see dags/jobtask.py; there is intentionally NO ENTRYPOINT so that ...)
#   2. Ray nodes (KubeRay on k8s, docker-based Ray clusters, ...) supply their
#      own command, e.g. `ray start --head --port=6379 ...` or `python job.py`.
#      Ray version is pinned here and must match the version of every node in
#      the cluster (see ray/raycluster.yaml).
#
# Extend the pip install below with whatever your jobs need
# (torch, xgboost, ...). Keep it lean-ish: the image is rebuilt with
# `docker compose --profile build build jobrunner` and reused by all jobs.
FROM python:3.12-slim

RUN pip install --no-cache-dir --upgrade pip && \
    # staged installs: a single 12-package resolution pass exceeds pip's
    # resolver depth (tritonclient[all] + ray + mlflow graphs are deep)
    pip install --no-cache-dir \
        "numpy" \
        "pandas" \
        "scikit-learn" \
        "boto3" \
        "requests" && \
    pip install --no-cache-dir "deeplake==3.9.52" && \
    pip install --no-cache-dir "mlflow==3.15.1" && \
    pip install --no-cache-dir \
        "onnx==1.19.1" \
        "onnxruntime==1.19.2" \
        "skl2onnx==1.20.0" && \
    pip install --no-cache-dir "qdrant-client==1.16.2" && \
    pip install --no-cache-dir "tritonclient[all]==2.71.0" && \
    pip install --no-cache-dir "ray[default]==2.58.0"   # [default] adds the dashboard deps so `ray start --include-dashboard` / `ray job submit` work on KubeRay nodes
COPY runner.py /runner.py
# NOTE: no ENTRYPOINT on purpose (dual-mode image, see header comment).