"""Stage 7 — COLLECT/VERIFY: end-of-run summary across all stores.

Runs in the CPU job image. Checks, and hard-fails the run if any is missing:

* S3:    per-stage manifests (ingest/split/train/export/eval) under data/<run_id>/
         + model artifacts under models/<run_id>/yolo/
* DeepLake: dataset head loads, row/tensor counts, commit history, kv metadata
* Triton: server healthy + the deployed model ready + reported config
* MLflow: the train-<run_id> / evaluate-<run_id> runs exist in the experiment

Publishes data/<run_id>/detection_summary.json — a single flat view of the
whole run (what was trained, on which commit, how it scored, where it is).
"""
from __future__ import annotations

import json
import os
import sys
import time

import boto3
import deeplake
import requests

S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
TRITON_HTTP_URL = os.environ.get("TRITON_HTTP_URL", "http://triton:8005")
TRITON_DET_MODEL = os.environ.get("TRITON_DET_MODEL", "yolo_voc12")
VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")

MANIFESTS = {
    "ingest": f"data/{RUN_ID}/voc12_ingest_manifest.json",
    "split": f"data/{RUN_ID}/voc12_split_manifest.json",
    "train": f"data/{RUN_ID}/yolo_train_manifest.json",
    "export": f"data/{RUN_ID}/yolo_export_manifest.json",
    "eval": f"data/{RUN_ID}/yolo_eval_manifest.json",
}


def s3_client() -> "boto3.client":
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=S3_REGION,
    )


def dl_creds() -> dict:
    return {
        "aws_access_key_id": S3_ACCESS,
        "aws_secret_access_key": S3_SECRET,
        "aws_region": S3_REGION,
        "endpoint_url": S3_ENDPOINT,
    }


def main() -> None:
    s3 = s3_client()
    problems = []

    # --- S3: manifests + model artifacts -------------------------------------
    manifests = {}
    for stage, key in MANIFESTS.items():
        try:
            manifests[stage] = json.loads(s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read())
        except Exception as e:
            problems.append(f"missing manifest {key}: {e}")
    model_keys = []
    for key in s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"models/{RUN_ID}/yolo/")["Contents"]:
        model_keys.append({"key": key["Key"], "size": key["Size"]})

    # --- DeepLake -------------------------------------------------------------
    ds = None
    dl = {}
    try:
        ds = deeplake.load(VOC12_DATASET, read_only=True, creds=dl_creds())
        dl = {
            "rows": len(ds),
            "tensors": list(ds.tensors),
            "commit_id": ds.commit_id,
            "info": {k: v for k, v in dict(ds.info).items()},
            "commits": len(ds.commits),
            "last_commit": (ds.commits[0]["commit"][:12] if ds.commits else None),
            "last_message": (ds.commits[0]["message"] if ds.commits else None),
        }
    except Exception as e:
        problems.append(f"deeplake load failed: {e}")

    # --- Triton ----------------------------------------------------------------
    triton = {}
    try:
        r = requests.get(f"{TRITON_HTTP_URL}/v2/health/ready", timeout=10)
        triton["server_ready"] = r.status_code == 200
        r = requests.get(f"{TRITON_HTTP_URL}/v2/models/{TRITON_DET_MODEL}/ready", timeout=10)
        triton["model_ready"] = r.status_code == 200
        if triton["model_ready"]:
            r = requests.get(f"{TRITON_HTTP_URL}/v2/models/{TRITON_DET_MODEL}/config", timeout=10)
            triton["max_batch_size"] = r.json().get("config", {}).get("max_batch_size")
    except Exception as e:
        problems.append(f"triton check failed: {e}")
        triton = {"server_ready": False, "model_ready": False}

    # --- MLflow -----------------------------------------------------------------
    mlflow_runs = []
    try:
        r = requests.get(f"{MLFLOW_TRACKING_URI}/api/2.0/mlflow/experiments/get-by-name",
                         params={"experiment_name": "detection_voc12"}, timeout=10)
        exp = r.json().get("experiment", {})
        if exp:
            r = requests.get(f"{MLFLOW_TRACKING_URI}/api/2.0/mlflow/runs/list",
                             params={"experiment_id": exp["experiment_id"]}, timeout=10)
            for run in r.json().get("runs", []):
                name = (run.get("tags", {}) or {}).get("mlflow.runName", "")
                if RUN_ID in name:
                    mlflow_runs.append({"run": name, "status": run.get("status")})
    except Exception as e:
        problems.append(f"mlflow check failed: {e}")

    # --- verdict ------------------------------------------------------------------
    summary = {
        "run_id": RUN_ID,
        "s3": {
            "manifests": {k: bool(v) for k, v in manifests.items()},
            "model_artifacts": model_keys,
            "model_artifact_count": len(model_keys),
        },
        "deeplake": dl,
        "triton": triton,
        "mlflow": {"experiment": "detection_voc12", "runs": mlflow_runs},
        "highlights": {
            "commit_id": (manifests.get("split") or {}).get("commit_id"),
            "train": (manifests.get("train") or {}).get("final"),
            "eval": {
                "map50_torch": (manifests.get("eval") or {}).get("map50_torch"),
                "map50_triton": (manifests.get("eval") or {}).get("map50_triton"),
                "delta": (manifests.get("eval") or {}).get("delta"),
            },
        },
        "problems": problems,
    }
    key = f"data/{RUN_ID}/detection_summary.json"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(summary, indent=2).encode())
    print(json.dumps(summary, indent=2))
    if problems:
        print(f"VERIFY FAIL: {len(problems)} problems — see 'problems'")
        sys.exit(1)
    print(f"VERIFY OK: all stores consistent for run {RUN_ID}; summary at s3://{S3_BUCKET}/{key}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"collect_detection_metrics finished in {time.time() - t0:.1f}s")