"""Full ML-platform pipeline on the airflow-ml stack.

Flow (per DAG run):

    generate_dataset (job container)  -> s3://<bucket>/data/<run_id>/{train,test}.csv, manifest.json
    verify_dataset   (airflow worker) -> S3Hook: objects exist + non-empty
    enrich_dataset   (job container)  -> DeepLake commit on s3://<bucket>/deeplake/feature_ds
                                         (demo tensors features/target/run_id + ds.info kv metadata;
                                         pipelines may commit any numeric embedding tensor)
    index_embeddings (job container)  -> mirrors EMBEDDING_TENSOR (default `features`) from the
                                         DeepLake head into Qdrant collection QDRANT_COLLECTION with
                                         distance QDRANT_DISTANCE (size discovered from the data)
    vector_search    (job container)  -> kNN retrieval over the collection -> s3://<bucket>/analysis/<run_id>/vector_search.json
    train_model      (job container)  -> model.pkl + model.onnx + metrics.json; MLflow run train-<run_id>
    deploy_model     (job container)  -> stages ONNX into Triton (shared /models bind mount), loads it
    evaluate         (job container)  -> test set through Triton gRPC; MLflow run evaluate-<run_id>
    collect_metrics  (airflow worker) -> reads train/eval/vector_search artifacts, reports

Job containers are orchestrator-agnostic (env-driven, no docker-specific code):
the same image and scripts run under Ray (see ray/raycluster.yaml).

Trigger manually:

    DAG_ID=ml_platform_pipeline make unpause
    DAG_ID=ml_platform_pipeline make trigger
"""
from __future__ import annotations

import json
from datetime import datetime

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator

from jobtask import S3_BUCKET, job_task, s3_hook, verify_dataset


def collect_metrics(**context) -> dict:
    """Fetch and report all published artifacts of the run (train/eval/vector search)."""
    run_id = context["run_id"]
    hook = s3_hook()
    out = {}
    for section, key in (
        ("train", f"models/{run_id}/metrics.json"),
        ("eval", f"models/{run_id}/eval_metrics.json"),
        ("vector_search", f"analysis/{run_id}/vector_search.json"),
    ):
        if not hook.check_for_key(key, bucket_name=S3_BUCKET):
            raise AirflowException(f"s3://{S3_BUCKET}/{key} missing — earlier task failed to publish")
        out[section] = json.loads(hook.read_key(key, bucket_name=S3_BUCKET))
        print(f"run {run_id} {section}: {out[section]}")
    print(f"train vs triton-eval r2 delta: {abs(out['train']['test_r2'] - out['eval']['test_r2']):.6f}")
    return out


with DAG(
    dag_id="ml_platform_pipeline",
    description="DeepLake versioning + MLflow batches + Qdrant retrieval + Triton inference",
    schedule=None,  # manually triggered
    start_date=datetime(2026, 8, 26),
    catchup=False,
    max_active_runs=1,
    tags=["ml", "deeplake", "mlflow", "qdrant", "triton", "docker-operator"],
) as dag:
    generate_dataset = job_task("generate_dataset.py", job_id="generate_dataset")
    verify = PythonOperator(task_id="verify_dataset", python_callable=verify_dataset)
    enrich = job_task("enrich_dataset.py", job_id="enrich_dataset")
    index = job_task("index_embeddings.py", job_id="index_embeddings")
    search = job_task("vector_search.py", job_id="vector_search")
    train = job_task("train_model.py", job_id="train_model")
    deploy = job_task("deploy_model.py", job_id="deploy_model")
    evaluate = job_task("evaluate.py", job_id="evaluate")
    metrics = PythonOperator(task_id="collect_metrics", python_callable=collect_metrics)

    (
        generate_dataset
        >> verify
        >> enrich
        >> index
        >> search
        >> train
        >> deploy
        >> evaluate
        >> metrics
    )