"""Stage 4 — TRAINING (CUDA): YOLO11n on VOC2012, tracked in MLflow.

Runs in the GPU job image (ml-jobrunner-gpu) via `gpu_job_task(...)` which
passes `--gpus` (device_requests) + /dev/shm to the container. The job:

1. pins the exact DeepLake commit produced by sampling (stage 3) via
   `s3://.../data/<run_id>/voc12_split_manifest.json` -> commit_id,
2. streams the needed JPEGs from MinIO into the container's /tmp,
3. writes YOLO-format label files from the DeepLake `bboxes`/`class_ids`
   tensors (the enrichment payoff: no re-parsing of the raw XMLs),
4. trains on the GPU while logging per-epoch metrics to the MLflow experiment
   `detection_voc12` (run name `train-<run_id>`),
5. publishes weights + results + a manifest to S3 for the export stage.

Env (injected by job_task()/gpu_job_task(); override per task via extra_env):
  DEEPLAKE_VOC12   s3://ml-artifacts/deeplake/voc12
  VOC_S3_PREFIX    datasets/voc12/VOC2012
  YOLO_MODEL       yolo11n.pt  (or yolo11s/... — auto-downloaded first run)
  IMGSZ            640
  EPOCHS           30
  BATCH            16
  GPU_DEVICE       0
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import boto3
import deeplake
import mlflow
import numpy as np
import torch
from ultralytics import YOLO

# --- env ---------------------------------------------------------------------
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")
VOC_S3_PREFIX = os.environ.get("VOC_S3_PREFIX", "datasets/voc12/VOC2012")
YOLO_MODEL = os.environ.get("YOLO_MODEL", "yolo11n.pt")
IMGSZ = int(os.environ.get("IMGSZ", "640"))
EPOCHS = int(os.environ.get("EPOCHS", "30"))
BATCH = int(os.environ.get("BATCH", "16"))
GPU_DEVICE = int(os.environ.get("GPU_DEVICE", "0"))

ROOT = Path("/tmp/voc12")


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


def text_of(value) -> str:
    a = np.asarray(value)
    v = a.item() if a.size == 1 else a.reshape(-1)[0]
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    return str(v)


def scalar_of(value) -> float:
    return float(np.asarray(value).reshape(-1)[0])


def materialize(ds, s3) -> dict:
    """Download JPEGs from MinIO into the container and write YOLO labels
    from the DeepLake tensors. Layout YOLO expects:

        /tmp/voc12/{train,val}/images/<id>.jpg   (symlinks into /tmp/voc12/raw/)
        /tmp/voc12/{train,val}/labels/<id>.txt   ("cls cx cy w h" normalized)
    """
    for split in ("train", "val"):
        (ROOT / split / "images").mkdir(parents=True, exist_ok=True)
        (ROOT / split / "labels").mkdir(parents=True, exist_ok=True)
    raw = ROOT / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    n = len(ds)
    stats = {"train": 0, "val": 0, "downloaded": 0, "boxes": 0}
    for i in range(n):
        split = text_of(ds["split"][i].numpy())
        img_id = text_of(ds["image_id"][i].numpy())
        uri = text_of(ds["image_uri"][i].numpy())          # s3://bucket/prefix/JPEGImages/x.jpg
        key = uri.split("/", 3)[3]                         # prefix/JPEGImages/x.jpg

        local = raw / Path(key).name
        if not local.exists():
            s3.download_file(S3_BUCKET, key, str(local))
            stats["downloaded"] += 1
        link = ROOT / split / "images" / local.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(local)

        # YOLO label file from the enriched tensors
        cls = ds["class_ids"][i].numpy().astype(np.int64).reshape(-1)
        bb = ds["bboxes"][i].numpy().astype(np.float64)    # (N, 4) x1 y1 x2 y2 px
        w, h = scalar_of(ds["width"][i].numpy()), scalar_of(ds["height"][i].numpy())
        lines = []
        for c, (x1, y1, x2, y2) in zip(cls, bb):
            if c < 0:
                continue  # class not in the model's class list
            cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
            bw, bh = (x2 - x1) / w, (y2 - y1) / h
            lines.append(f"{int(c)} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            stats["boxes"] += 1
        label_path = ROOT / split / "labels" / (img_id + ".txt")
        label_path.write_text("\n".join(lines))
        stats[split] += 1

    return stats


def main() -> None:
    # --- GPU sanity: fail loud, never silently train on CPU ------------------
    if not torch.cuda.is_available():
        sys.exit("CUDA is not visible in this container — task must use gpu_job_task() "
                 "and the host needs nvidia-container-toolkit")
    print(f"CUDA ok: {torch.cuda.get_device_name(0)} | torch {torch.__version__}")

    s3 = s3_client()
    creds = dl_creds()

    # --- pin the exact sampling commit from this run -------------------------
    manifest_key = f"data/{RUN_ID}/voc12_split_manifest.json"
    body = s3.get_object(Bucket=S3_BUCKET, Key=manifest_key)["Body"].read()
    split_manifest = json.loads(body)
    commit = split_manifest["commit_id"]
    ds = deeplake.load(f"{VOC12_DATASET}@{commit}", read_only=True, creds=creds)
    print(f"pinned dataset {VOC12_DATASET}@{commit[:12]} (train={split_manifest['train_count']}, "
          f"val={split_manifest['val_count']})")

    names = [text_of(ds["class_names"][i].numpy()) for i in range(len(ds["class_names"]))]

    # --- MLflow: experiment + run for the train batch ------------------------
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("detection_voc12")
    with mlflow.start_run(run_name=f"train-{RUN_ID}") as run:
        mlflow.log_params({
            "model": YOLO_MODEL,
            "imgsz": IMGSZ,
            "epochs": EPOCHS,
            "batch": BATCH,
            "gpu": torch.cuda.get_device_name(0),
            "dataset": VOC12_DATASET,
            "dataset_commit": commit,
            "train_images": split_manifest["train_count"],
            "val_images": split_manifest["val_count"],
            "num_classes": len(names),
            "torch": torch.__version__,
        })
        mlflow.set_tag("batch", "train")

        # --- materialize data ------------------------------------------------
        t0 = time.time()
        stats = materialize(ds, s3)
        print(f"materialized: {stats} in {time.time() - t0:.1f}s")

        data_yaml = ROOT / "data.yaml"
        data_yaml.write_text(
            "path: /tmp/voc12\ntrain: train\nval: val\n"
            f"names: {json.dumps(names)}\n"
        )

        # --- train (per-epoch metrics streamed to MLflow) --------------------
        model = YOLO(YOLO_MODEL)  # downloads pretrained weights on first use

        def on_train_epoch_end(engine):
            m = getattr(engine, "metrics", None) or {}
            metrics = {
                k.replace("metrics/", ""): float(v)
                for k, v in m.items()
                if isinstance(v, (int, float, np.floating)) and not isinstance(v, bool)
            }
            if metrics:
                mlflow.log_metrics(metrics, epoch=int(engine.epoch) + 1)

        model.add_callback("on_train_epoch_end", on_train_epoch_end)

        model.train(
            data=str(data_yaml),
            epochs=EPOCHS,
            imgsz=IMGSZ,
            batch=BATCH,
            device=GPU_DEVICE,
            project="/tmp",
            name="yolo",
            exist_ok=True,
            plots=False,
            verbose=2,
        )

        # --- final validation + artifacts ------------------------------------
        results = model.val(data=str(data_yaml), split="val", device=GPU_DEVICE, imgsz=IMGSZ, plots=False)
        final = {
            "map50": float(results.box.map50),
            "map50_95": float(results.box.map),
            "precision": float(results.box.mp),
            "recall": float(results.box.mr),
        }
        mlflow.log_metrics(final)
        run_dir = Path("/tmp/yolo")
        best_pt = run_dir / "weights" / "best.pt"
        last_pt = run_dir / "weights" / "last.pt"
        mlflow.log_artifact(str(best_pt))
        mlflow.log_artifact(str(last_pt))
        results_csv = run_dir / "results.csv"
        if results_csv.exists():
            mlflow.log_artifact(str(results_csv))
        mlflow.log_artifact(str(data_yaml))

        # --- publish to S3 (export stage reads this manifest) ----------------
        run_s3 = f"models/{RUN_ID}/yolo"
        for local, name in (
            (best_pt, "best.pt"),
            (last_pt, "last.pt"),
            (results_csv, "results.csv"),
            (data_yaml, "data.yaml"),
        ):
            if local.exists():
                s3.upload_file(str(local), S3_BUCKET, f"{run_s3}/{name}")
        args_json = json.dumps({
            "model": YOLO_MODEL, "imgsz": IMGSZ, "epochs": EPOCHS, "batch": BATCH,
            "commit_id": commit, "num_classes": len(names),
            "final": final, "stats": stats,
        }).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=f"{run_s3}/train_args.json", Body=args_json)
        s3.put_object(Bucket=S3_BUCKET, Key=f"{run_s3}/metrics.json", Body=json.dumps(final, indent=2).encode())

        manifest = {
            "run_id": RUN_ID,
            "mlflow_run_id": run.info.run_id,
            "mlflow_uri": MLFLOW_TRACKING_URI,
            "mlflow_experiment": "detection_voc12",
            "model": YOLO_MODEL,
            "imgsz": IMGSZ,
            "epochs": EPOCHS,
            "commit_id": commit,
            "deeplake_ref": f"{VOC12_DATASET}@{commit}",
            "run_dir_s3": f"s3://{S3_BUCKET}/{run_s3}/",
            "best_pt": f"{run_s3}/best.pt",
            "final": final,
            "stats": stats,
            "class_names": names,
        }
        mkey = f"data/{RUN_ID}/yolo_train_manifest.json"
        s3.put_object(Bucket=S3_BUCKET, Key=mkey, Body=json.dumps(manifest, indent=2).encode())
        print(f"artifacts published: s3://{S3_BUCKET}/{run_s3}/ + manifest {mkey}")
        print(f"TRAIN OK: {final} (commit {commit[:12]}, mlflow run {run.info.run_id})")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"train_yolo_voc12 finished in {time.time() - t0:.1f}s")