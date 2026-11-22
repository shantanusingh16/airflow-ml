"""PASCAL VOC 2012 full detection pipeline (Yolo11 on the ML platform).

End-to-end data-quality + training chain, exactly as specified:

  1. verify_upload   (CPU)  dataset uploaded to MinIO is complete
                            (5717 JPEGs + XMLs + trainval.txt)
  2. ingest_voc12    (CPU)  raw VOC (images + XML annotations on S3) ->
                            DeepLake `voc12` dataset (images, bboxes, classes)
  3. embed_fastdup   (GPU)  fastdup over the whole set: DINOv2 embeddings
                            (576-d) + image attributes (size/brightness/RGB
                            means) + duplicate groups, committed to DeepLake
                            and rendered to a PDF report on S3
                            (analysis/<run>/voc12_embed_report.pdf)
  4. cluster_split   (GPU)  DBSCAN kNN clustering of the DINOv2 embeddings;
                            WHOLE clusters assigned to train/val/test at
                            70/10/20 (no near-duplicate ever crosses a
                            split -> no leakage), committed to DeepLake
  5. train_tide      (GPU)  YOLO11n trained on train3, validated on val3,
                            evaluated on val3 AND test3 with TIDE-framework
                            metrics (TIDE10/20/50 + 101-pt mAP50 + operating
                            precision/recall); results -> MLflow
  6. export_triton   (GPU)  best.pt -> ONNX (dynamic batch) -> deployed to
                            Triton (onnxruntime) as `yolo_voc12`, verified
                            via gRPC

After a green run, inference from the HOST with only stdlib + PIL + numpy
+ requests (no torch/ultralytics needed on the host):

    python3 examples/detection/infer_cli.py <image_path>

prints a JSON dict with every bbox + confidence and writes an annotated
copy of the image. NMS is applied client-side: the deployed YOLO11 ONNX
is the raw detection head (no NMS op) on Triton's onnxruntime backend.

To activate:
    cp examples/detection/dags/voc12_full_pipeline.py dags/
    cp examples/detection/jobs/{verify_voc12_upload,ingest_voc12,embed_voc12,
        cluster_split_voc12,train_eval_tide_voc12,export_yolo_onnx}.py dags/jobs/
    DAG_ID=voc12_full_pipeline make unpause && DAG_ID=voc12_full_pipeline make trigger

Prerequisites: VOC2012 uploaded to s3://ml-artifacts/datasets/voc12/ (stage 1,
see docs/detection-example/01-ingestion.md), ml-jobrunner-gpu:latest built
(docker build -f jobrunner/Dockerfile.gpu -t ml-jobrunner-gpu:latest jobrunner/).
"""
from datetime import datetime

from airflow import DAG

from jobtask import gpu_job_task, job_task

# Shared env for the detection jobs (job_task() already injects S3_*, AWS_*,
# and all platform endpoints)
DET_ENV = {
    "DEEPLAKE_VOC12": "s3://ml-artifacts/deeplake/voc12",
    "VOC_S3_PREFIX": "datasets/voc12/VOC2012",
    "MIN_IMAGES": "5000",
    "YOLO_MODEL": "yolo11n.pt",
    "IMGSZ": "640",
    "EPOCHS": "30",
    "BATCH": "16",
    "TRITON_DET_MODEL": "yolo_voc12",
    "DBSCAN_EPS": "0.15",
    "DBSCAN_MIN_SAMPLES": "5",
}

with DAG(
    dag_id="voc12_full_pipeline",
    description=("VOC2012 YOLO11: verify upload -> ingest -> fastdup DINOv2 embeddings "
                 "+ PDF report -> DBSCAN cluster-pure 70/10/20 split -> YOLO11 train + "
                 "TIDE eval (MLflow) -> ONNX export -> Triton"),
    schedule=None,
    start_date=datetime(2026, 8, 26),
    catchup=False,
    tags=["detection", "voc12", "fastdup", "gpu", "tide"],
) as dag:
    verify = job_task(
        "verify_voc12_upload.py", job_id="verify_upload", extra_env=DET_ENV,
        timeout=1800,
    )
    ingest = job_task(
        "ingest_voc12.py", job_id="ingest_voc12", extra_env=DET_ENV,
        timeout=3600,
    )
    embed = gpu_job_task(
        "embed_voc12.py", job_id="embed_fastdup", extra_env=DET_ENV,
        timeout=7200,   # 5717 images through the fastdup DINOv2 engine
    )
    cluster = gpu_job_task(
        "cluster_split_voc12.py", job_id="cluster_split", extra_env=DET_ENV,
        timeout=3600,   # DBSCAN on 5717x576 precomputed distances: minutes
    )
    train = gpu_job_task(
        "train_eval_tide_voc12.py", job_id="train_tide", extra_env=DET_ENV,
        timeout=10800,  # 30 epochs yolo11n @640 on ~4000 images (4090) + TIDE eval
    )
    export = gpu_job_task(
        "export_yolo_onnx.py", job_id="export_triton", extra_env=DET_ENV,
        timeout=3600,
    )

    verify >> ingest >> embed >> cluster >> train >> export