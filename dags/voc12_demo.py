"""PASCAL VOC 2012 demo DAG (data side only — no training, eval or export).

Short, demo-friendly chain over a local VOC2012 tree, reusing the existing
detection job scripts from voc12_full_pipeline:

  1. upload_voc12  (CPU)  copies the annotated JPEG+XML pairs from the
                          read-only /datasets/voc2012 bind mount to
                          s3://<bucket>/datasets/voc12/VOC2012/ and writes
                          ImageSets/Main/trainval.txt listing exactly the
                          uploaded ids (deterministic first SAMPLE of the
                          sorted annotated ids; SAMPLE=0 = all; default from
                          the stack env SAMPLE, else 1000)
  2. verify_upload (CPU)  the upload landed complete: >= MIN_IMAGES JPEGs,
                          the same count of XMLs, trainval.txt line count
                          matching the JPEG count (fails a partial upload
                          before any GPU time is spent)
  3. ingest_voc12  (CPU)  raw VOC on S3 -> DeepLake `voc12` dataset
                          (images, bboxes, classes), rebuilt from scratch
  4. embed_fastdup (GPU)  fastdup DINOv2 embeddings (576-d) + image
                          attributes (size/brightness/RGB means) + duplicate
                          groups, committed to DeepLake and rendered to a
                          PDF report on S3 (analysis/<run>/voc12_embed_report.pdf)
  5. cluster_split (GPU)  DBSCAN kNN clustering of the DINOv2 embeddings;
                          WHOLE clusters assigned to train/val/test at
                          70/10/20 (no near-duplicate crosses a split -> no
                          leakage), committed to DeepLake

Trigger (no schedule — manual only), from the Airflow UI (Browse ->
``voc12_demo`` -> trigger) or on a compose stack:

    DAG_ID=voc12_demo make unpause && DAG_ID=voc12_demo make trigger

``SAMPLE`` is a per-trigger DAG param: override it in the UI's "Trigger w/
config" form or via the API with ``conf: {"SAMPLE": 200}``; its default
comes from the stack env ``SAMPLE`` (injected into the Airflow containers
by docker-compose), otherwise 1000.
"""
from datetime import datetime

import os

from airflow import DAG
from airflow.sdk import Param

from jobtask import gpu_job_task, job_task

# --- demo knobs ----------------------------------------------------------------
# SAMPLE is a per-trigger DAG param (the ``params=`` block below): >0 =
# first N ids in sorted order (deterministic), 0 = all annotated pairs. Its
# default is the stack env SAMPLE, which docker-compose injects into the
# Airflow containers (${SAMPLE:-1000}).
# Source of the read-only dataset bind mount (resolved by the docker daemon /
# staging shim, not by the job): in staging the shim re-exports the host
# VOC2012 tree the worker sees at /datasets/voc2012; on other hosts set
# VOC_DATASET_HOST_DIR to the real host path of the tree.
VOC_DATASET_HOST_DIR = os.environ.get("VOC_DATASET_HOST_DIR", "/datasets/voc2012")

# Same keys as voc12_full_pipeline's DET_ENV (minus nothing — the training/
# export keys are inert here since this DAG stops before training); only
# MIN_IMAGES differs: it is sized to what upload_voc12 stages, so
# verify_upload accepts exactly that.
DEMO_ENV = {
    "DEEPLAKE_VOC12": "s3://ml-artifacts/deeplake/voc12",
    "VOC_S3_PREFIX": "datasets/voc12/VOC2012",
    # exact count when sampling; for the full set the same floor as the full
    # pipeline (below the 5717-image full trainval — this tree has 5138
    # annotated pairs)
    "MIN_IMAGES": "{{ params.SAMPLE if params.SAMPLE | int > 0 else 5000 }}",
    "YOLO_MODEL": "yolo11n.pt",
    "IMGSZ": "640",
    "EPOCHS": "30",
    "BATCH": "16",
    "TRITON_DET_MODEL": "yolo_voc12",
    "DBSCAN_EPS": "0.15",
    "DBSCAN_MIN_SAMPLES": "5",
}

# Read-only bind mount of the local VOC2012 tree into the upload job
# container (only that task needs it; later stages read from S3/DeepLake).
DATASET_MOUNT = {
    "type": "bind",
    "source": VOC_DATASET_HOST_DIR,
    "target": "/datasets/voc2012",
    "read_only": True,
}

with DAG(
    dag_id="voc12_demo",
    description=("VOC2012 demo (no training): upload SAMPLE of annotated pairs -> "
                 "verify upload -> DeepLake ingest -> fastdup DINOv2 embed + PDF "
                 "report -> DBSCAN cluster-pure 70/10/20 split"),
    schedule=None,
    start_date=datetime(2026, 11, 22),
    catchup=False,
    tags=["demo", "voc12"],
    params={"SAMPLE": Param(int(os.environ.get("SAMPLE", "1000")),
                            type="integer", minimum=0)},
) as dag:
    upload = job_task(
        "upload_voc12.py", job_id="upload_voc12",
        extra_env={**DEMO_ENV, "SAMPLE": "{{ params.SAMPLE }}"},
        extra_mounts=[DATASET_MOUNT],
        timeout=3600,
    )
    verify = job_task(
        "verify_voc12_upload.py", job_id="verify_upload", extra_env=DEMO_ENV,
        timeout=1800,
    )
    ingest = job_task(
        "ingest_voc12.py", job_id="ingest_voc12", extra_env=DEMO_ENV,
        timeout=3600,
    )
    embed = gpu_job_task(
        "embed_voc12.py", job_id="embed_fastdup", extra_env=DEMO_ENV,
        timeout=7200,   # DINOv2 over the whole (sampled) set
    )
    cluster = gpu_job_task(
        "cluster_split_voc12.py", job_id="cluster_split", extra_env=DEMO_ENV,
        timeout=3600,   # DBSCAN on the precomputed N x 576 distance matrix
    )

    upload >> verify >> ingest >> embed >> cluster
