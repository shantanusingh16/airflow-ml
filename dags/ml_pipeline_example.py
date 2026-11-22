"""Example ML pipeline on the airflow-ml stack.

Flow (per DAG run):

    generate_dataset (job container)        -> s3://<bucket>/data/<run_id>/{train,test}.csv, manifest.json
    verify_dataset   (airflow worker)       -> S3Hook: list + head objects, fail run if dataset missing
    train_model      (job container)        -> s3://<bucket>/models/<run_id>/{model.pkl,metrics.json}
    collect_metrics  (airflow worker)       -> S3Hook: read metrics.json, print + XCom

Job containers are launched by DockerOperator: image ``ml-jobrunner`` runs
``runner.py <job-script>``; the DAG folder is mounted read-only at
``/opt/airflow/dags`` and the container joins the compose network
``airflow-ml-net`` so it can reach ``minio`` by service name.

Trigger manually (UI, or::)

    curl -u airflow:airflow -X POST \
      http://localhost:2405/api/v2/dags/ml_pipeline_example/dagRuns \
      -H 'Content-Type: application/json' -d '{}'
"""

from __future__ import annotations

import json
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator

from jobtask import S3_BUCKET, job_task, s3_hook, verify_dataset


def collect_metrics(**context) -> dict:
    """Fetch and report training metrics published to S3 by the job container."""
    run_id = context["run_id"]
    key = f"models/{run_id}/metrics.json"
    hook = s3_hook()

    if not hook.check_for_key(key, bucket_name=S3_BUCKET):
        raise AirflowException(f"s3://{S3_BUCKET}/{key} missing — training job failed to publish metrics")

    metrics = json.loads(hook.read_key(key, bucket_name=S3_BUCKET))
    print(f"run {run_id} metrics: {metrics}")
    return metrics


with DAG(
    dag_id="ml_pipeline_example",
    description="Dataset gen (container) -> verify (S3) -> training (container) -> metrics (S3)",
    schedule=None,  # manually triggered
    start_date=datetime(2026, 8, 25),
    catchup=False,
    max_active_runs=1,
    tags=["ml", "example", "docker-operator", "minio"],
) as dag:
    generate_dataset = job_task("generate_dataset.py", job_id="generate_dataset")

    verify = PythonOperator(task_id="verify_dataset", python_callable=verify_dataset)

    train_model = job_task("train_model.py", job_id="train_model")

    metrics = PythonOperator(task_id="collect_metrics", python_callable=collect_metrics)

    generate_dataset >> verify >> train_model >> metrics