"""PASCAL VOC 2012 object-detection pipeline (Yolo11 on the ML platform).

To activate: copy this file to <project>/dags/detection_pipeline.py and all
job scripts to <project>/dags/jobs/:

    cp examples/detection/dags/detection_pipeline.py dags/
    cp examples/detection/jobs/*.py dags/jobs/

Prerequisites (one-time, see docs/detection-example/):
  * VOC2012 uploaded to s3://ml-artifacts/datasets/voc12/   (stage 1)
  * ml-jobrunner-gpu:latest built   (docker build -f jobrunner/Dockerfile.gpu ...)
  * GPU host: nvidia-container-toolkit installed

Chain (schedule=None -> manual triggers only):
  ingest_voc12 (CPU) -> sample_voc12 (CPU) -> train_yolo (GPU)
    -> export_yolo (GPU) -> eval_yolo (GPU, triton vs torch guard)
    -> collect_detection_metrics (CPU, cross-store verification)
"""
from datetime import datetime

from airflow import DAG

from jobtask import gpu_job_task, job_task

# Shared env for the detection jobs (job_task() already injects S3_*, AWS_*,
# and all platform endpoints)
DET_ENV = {
    "DEEPLAKE_VOC12": "s3://ml-artifacts/deeplake/voc12",
    "VOC_S3_PREFIX": "datasets/voc12/VOC2012",
    "YOLO_MODEL": "yolo11n.pt",
    "IMGSZ": "640",
    "EPOCHS": "30",
    "BATCH": "16",
    "TRITON_DET_MODEL": "yolo_voc12",
}

with DAG(
    dag_id="detection_voc12",
    description="VOC2012 YOLO11: ingest -> sample -> train (GPU) -> export -> eval -> verify",
    schedule=None,
    start_date=datetime(2026, 8, 26),
    catchup=False,
    tags=["detection", "voc12", "gpu"],
) as dag:
    ingest = job_task(
        "ingest_voc12.py", job_id="ingest_voc12", extra_env=DET_ENV,
        timeout=3600,
    )
    sample = job_task(
        "sample_voc12.py", job_id="sample_voc12", extra_env=DET_ENV,
        timeout=3600,
    )
    train = gpu_job_task(
        "train_yolo_voc12.py", job_id="train_yolo", extra_env=DET_ENV,
        timeout=7200,   # 30 epochs of yolo11n @ 640 on a 4090: ~15-30 min
    )
    export = gpu_job_task(
        "export_yolo_onnx.py", job_id="export_yolo", extra_env=DET_ENV,
        timeout=3600,
    )
    ev = gpu_job_task(
        "eval_yolo_voc12.py", job_id="eval_yolo", extra_env=DET_ENV,
        timeout=3600,
    )
    collect = job_task(
        "collect_detection_metrics.py", job_id="collect_detection_metrics",
        extra_env=DET_ENV, timeout=1800,
    )

    ingest >> sample >> train >> export >> ev >> collect