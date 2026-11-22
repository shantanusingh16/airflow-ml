"""Task 3 of 3 — train YOLO11 on the cluster-pure split + TIDE evaluation.

Runs in ml-jobrunner-gpu (CUDA). Flow:

1. pins the exact dataset commit from `voc12_cluster_manifest.json`
   (the DBSCAN cluster-pure 70/10/20 commit — train/val/test share no
   near-duplicate cluster, so no leakage),
2. streams the JPEGs from MinIO and writes YOLO labels from the DeepLake
   tensors (no raw-XML re-parsing),
3. trains YOLO11n on `train3` (ultralytics validates on `val3` each epoch),
   streaming per-epoch metrics to the MLflow experiment `detection_voc12`
   (run `train-<run_id>`),
4. evaluates on `val3` AND `test3` with **TIDE-framework metrics**:
   TIDE10 / TIDE20 / TIDE50 (AP computed at 10/20/50 recall points — the
   TIDE benchmark's core metrics, Weng et al. ICLR'21) plus 101-point mAP50,
   computed from the model's own predictions (NMS @ 0.5, IoU-0.5 greedy
   matching, per class);
5. publishes weights/results to `s3://<bucket>/models/<run_id>/yolo/` and
   `s3://<bucket>/data/<run_id>/yolo_train_manifest.json` (the export job
   consumes it unchanged).

Env: YOLO_MODEL (yolo11n.pt), IMGSZ (640), EPOCHS, BATCH, GPU_DEVICE.
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
YOLO_MODEL = os.environ.get("YOLO_MODEL", "yolo11n.pt")
IMGSZ = int(os.environ.get("IMGSZ", "640"))
EPOCHS = int(os.environ.get("EPOCHS", "30"))
BATCH = int(os.environ.get("BATCH", "16"))
GPU_DEVICE = int(os.environ.get("GPU_DEVICE", "0"))
NMS_IOU_CURVE = 0.5      # NMS for the PR/TIDE curves
NMS_IOU_OPERATING = 0.45  # NMS for operating-point precision/recall
CONF_OPERATING = 0.25

ROOT = Path("/tmp/voc12_full")


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


# --- geometry / metrics (TIDE) -------------------------------------------------
def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (4,) or (N,4) x1y1x2y2 ; b: (M,4) -> (N,M) broadcast IoU."""
    A = a.reshape(-1, 4); B = b.reshape(-1, 4)
    x1 = np.maximum(A[:, None, 0], B[None, :, 0])
    y1 = np.maximum(A[:, None, 1], B[None, :, 1])
    x2 = np.minimum(A[:, None, 2], B[None, :, 2])
    y2 = np.minimum(A[:, None, 3], B[None, :, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    aa = np.maximum(0, A[:, 2] - A[:, 0]) * np.maximum(0, A[:, 3] - A[:, 1])
    ab = np.maximum(0, B[:, 2] - B[:, 0]) * np.maximum(0, B[:, 3] - B[:, 1])
    iou = inter / np.maximum(1e-9, aa[:, None] + ab[None, :] - inter)
    return iou


def nms_sorted(dets: np.ndarray, iou_thresh: float) -> np.ndarray:
    """dets: (N, 6) x1 y1 x2 y2 conf cls, sorted by conf desc -> kept rows."""
    keep = []
    used = np.zeros(len(dets), dtype=bool)
    for i in range(len(dets)):
        if used[i]:
            continue
        keep.append(i)
        rest = np.where(~used & (np.arange(len(dets)) > i))[0]
        if len(rest):
            iou = box_iou(dets[i, :4], dets[rest, :4])   # (1, M) IoU matrix
            used[rest[iou[0] > iou_thresh]] = True
    return dets[keep] if keep else dets[:0]


def ap_n(tp: list, fp: list, n_gt: int, n_points: int) -> float:
    """Average precision with N-point recall interpolation.
    n_points=101 ~ all-points mAP; 10/20/50 = TIDE10/TIDE20/TIDE50."""
    if n_gt == 0:
        return 0.0
    tp = np.cumsum(np.asarray(tp, dtype=np.float64))
    fp = np.cumsum(np.asarray(fp, dtype=np.float64))
    rec = tp / n_gt
    prec = tp / np.maximum(1e-9, tp + fp)
    ap = 0.0
    for r in np.linspace(0.0, 1.0, n_points):
        idx = np.where(rec >= r)[0]
        ap += (prec[idx].max() if idx.size else 0.0) / n_points
    return float(ap)


def evaluate_split(model, image_paths: list[str], gt_by_class: dict,
                   num_classes: int) -> dict:
    """TIDE-framework metrics for one split: mAP50 (101-pt), TIDE10/20/50,
    operating precision/recall @ conf 0.25. `gt_by_class`: class -> img_path
    -> list of (x1,y1,x2,y2) in ORIGINAL image pixels (matches the
    coordinates model.predict returns)."""
    per_class_dets: dict[int, list] = {c: [] for c in range(num_classes)}
    for p in image_paths:
        r = model.predict(p, conf=0.0, iou=0.7, verbose=False)[0]
        if r.boxes is None or len(r.boxes) == 0:
            continue
        dets = np.column_stack([r.boxes.xyxy.cpu().numpy(),
                                r.boxes.conf.cpu().numpy(),
                                r.boxes.cls.cpu().numpy().astype(np.int64)])
        for c in range(num_classes):                 # NMS per class, per image
            rows = dets[dets[:, 5] == c]
            if not len(rows):
                continue
            rows = nms_sorted(rows[rows[:, 4].argsort()[::-1]], NMS_IOU_CURVE)
            for row in rows:
                per_class_dets[c].append((p, row[:4], row[4]))

    metrics = {}
    for c in range(num_classes):
        dets = per_class_dets[c]
        dets.sort(key=lambda d: -d[2])
        gts = gt_by_class.get(c, {})
        n_gt = sum(len(v) for v in gts.values())
        used = {img: [False] * len(gts.get(img, [])) for img in
                {d[0] for d in dets} | set(gts.keys())}
        tp, fp = [], []
        for img, box, conf in dets:
            hit = -1
            gs = gts.get(img, [])
            if gs:
                ious = box_iou(box, np.asarray(gs))
                for g, iou in enumerate(ious[0]):
                    if iou >= 0.5 and not used[img][g]:
                        hit = g
                        break
            if hit >= 0:
                used[img][hit] = True
                tp.append(1); fp.append(0)
            else:
                tp.append(0); fp.append(1)
        metrics[f"class_{c}_ap101"] = ap_n(tp, fp, n_gt, 101)
        metrics[f"class_{c}_tide10"] = ap_n(tp, fp, n_gt, 10)
        metrics[f"class_{c}_tide20"] = ap_n(tp, fp, n_gt, 20)
        metrics[f"class_{c}_tide50"] = ap_n(tp, fp, n_gt, 50)
    ap = lambda suffix: float(np.mean([metrics[f"class_{c}_{suffix}"] for c in range(num_classes)]))
    out = {
        "map50": ap("ap101"),
        "tide10": ap("tide10"),
        "tide20": ap("tide20"),
        "tide50": ap("tide50"),
        "per_class": {
            "map50": [metrics[f"class_{c}_ap101"] for c in range(num_classes)],
            "tide10": [metrics[f"class_{c}_tide10"] for c in range(num_classes)],
            "tide20": [metrics[f"class_{c}_tide20"] for c in range(num_classes)],
            "tide50": [metrics[f"class_{c}_tide50"] for c in range(num_classes)],
        },
    }
    # operating point: conf >= CONF_OPERATING, per-class NMS @ NMS_IOU_OPERATING
    tp_t, fp_t = [], []
    n_gt_total = sum(sum(len(v) for v in gts.values()) for gts in gt_by_class.values())
    for c in range(num_classes):
        gts_c = gt_by_class.get(c, {})
        cand = sorted((d for d in per_class_dets[c] if d[2] >= CONF_OPERATING),
                      key=lambda d: -d[2])
        kept = []
        for d in cand:
            d_box = np.asarray(d[1], dtype=np.float64).reshape(1, 4)
            if not any(box_iou(d_box, np.asarray(k[1], dtype=np.float64).reshape(1, 4))[0, 0]
                       > NMS_IOU_OPERATING for k in kept):
                kept.append(d)
        for img, box, conf in kept:
            gs = gts_c.get(img, [])
            if not gs:
                fp_t.append(1)
                continue
            ious = box_iou(np.asarray(box, dtype=np.float64).reshape(1, 4), np.asarray(gs))[0]
            (tp_t if bool((ious >= 0.5).any()) else fp_t).append(1)
    out["precision"] = (sum(tp_t) / (len(tp_t) + len(fp_t))) if (tp_t or fp_t) else 0.0
    out["recall"] = sum(tp_t) / max(1, n_gt_total)
    out["n_tp"] = len(tp_t); out["n_fp"] = len(fp_t); out["n_gt"] = n_gt_total
    return out




# --- data ----------------------------------------------------------------------
def materialize_split(ds, s3, split_name: str, split_field: str, root: Path) -> list[Path]:
    """Download the split's JPEGs and write YOLO labels. Returns image paths."""
    img_dir = root / split_name / "images"
    lbl_dir = root / split_name / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(len(ds["image_id"])):
        if text_of(ds[split_field][i].numpy()) != split_name:
            continue
        img_id = text_of(ds["image_id"][i].numpy())
        key = text_of(ds["image_uri"][i].numpy()).split("/", 3)[3]
        local = raw / Path(key).name
        if not local.exists():
            s3.download_file(S3_BUCKET, key, str(local))
        link = img_dir / local.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(local)
        cls = ds["class_ids"][i].numpy().astype(np.int64).reshape(-1)
        bb = ds["bboxes"][i].numpy().astype(np.float64)
        w, h = scalar_of(ds["width"][i].numpy()), scalar_of(ds["height"][i].numpy())
        lines = []
        for c, (x1, y1, x2, y2) in zip(cls, bb):
            if c < 0:
                continue
            lines.append(f"{int(c)} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} "
                         f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
        (lbl_dir / (img_id + ".txt")).write_text("\n".join(lines))
        paths.append(link)
    return paths


def gt_by_class_original(ds, split_field: str, split_name: str) -> dict:
    """class -> image_path -> [(x1,y1,x2,y2) in original pixels] for one split."""
    gt: dict = {}
    for i in range(len(ds["image_id"])):
        if text_of(ds[split_field][i].numpy()) != split_name:
            continue
        img_id = text_of(ds["image_id"][i].numpy())
        img_path = str(ROOT / split_name / "images" / f"{img_id}.jpg")
        cls = ds["class_ids"][i].numpy().astype(np.int64).reshape(-1)
        bb = ds["bboxes"][i].numpy().astype(np.float64)
        for c, box in zip(cls, bb):
            if c < 0:
                continue
            gtc = gt.setdefault(int(c), {})
            gtc.setdefault(img_path, []).append(tuple(map(float, box)))
    return gt


def main() -> None:
    if not torch.cuda.is_available():
        sys.exit("CUDA not visible — this task must use gpu_job_task()")
    print(f"CUDA ok: {torch.cuda.get_device_name(0)} | torch {torch.__version__}")

    s3 = s3_client()
    creds = dl_creds()

    # --- pin the cluster-pure split commit ------------------------------------
    cluster_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/voc12_cluster_manifest.json")["Body"].read())
    commit = cluster_m["commit_id"]
    ds = deeplake.load(f"{VOC12_DATASET}@{commit}", read_only=True, creds=creds)
    names = [text_of(ds["class_names"][i].numpy()) for i in range(len(ds["class_names"]))]
    print(f"pinned {VOC12_DATASET}@{commit[:12]}: "
          f"train={cluster_m['split_counts']['train']} val={cluster_m['split_counts']['val']} "
          f"test={cluster_m['split_counts']['test']} | {len(names)} classes")

    # --- MLflow ----------------------------------------------------------------
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("detection_voc12")
    with mlflow.start_run(run_name=f"train-{RUN_ID}") as run:
        mlflow.log_params({
            "model": YOLO_MODEL, "imgsz": IMGSZ, "epochs": EPOCHS, "batch": BATCH,
            "gpu": torch.cuda.get_device_name(0), "dataset": VOC12_DATASET,
            "dataset_commit": commit,
            "train_images": cluster_m["split_counts"]["train"],
            "val_images": cluster_m["split_counts"]["val"],
            "test_images": cluster_m["split_counts"]["test"],
            "num_classes": len(names), "torch": torch.__version__,
            "split_scheme": "DBSCAN cluster-pure 70/10/20",
        })
        mlflow.set_tag("batch", "train")
        mlflow.set_tag("evaluation", "tide10/20/50 + mAP50")

        # --- materialize train/val/test ----------------------------------------
        t0 = time.time()
        train_paths = materialize_split(ds, s3, "train", "split3", ROOT)
        val_paths = materialize_split(ds, s3, "val", "split3", ROOT)
        test_paths = materialize_split(ds, s3, "test", "split3", ROOT)
        print(f"materialized train={len(train_paths)} val={len(val_paths)} test={len(test_paths)} "
              f"in {time.time() - t0:.0f}s")

        data_yaml = ROOT / "data.yaml"
        data_yaml.write_text(
            f"path: {ROOT}\ntrain: train/images\nval: val/images\nnames: {json.dumps(names)}\n")

        # --- train --------------------------------------------------------------
        model = YOLO(YOLO_MODEL)

        def on_train_epoch_end(engine):
            m = getattr(engine, "metrics", None) or {}
            metrics = {
                # MLflow metric names reject parentheses: precision(B) -> precision_B
                k.replace("metrics/", "").replace("(", "_").replace(")", ""): float(v)
                for k, v in m.items()
                if isinstance(v, (int, float, np.floating)) and not isinstance(v, bool)}
            if metrics:
                mlflow.log_metrics(metrics, step=int(engine.epoch) + 1)

        model.add_callback("on_train_epoch_end", on_train_epoch_end)
        model.train(data=str(data_yaml), epochs=EPOCHS, imgsz=IMGSZ, batch=BATCH,
                    device=GPU_DEVICE, project="/tmp", name="yolo_full",
                    exist_ok=True, plots=False, verbose=True)

        results = model.val(data=str(data_yaml), split="val", device=GPU_DEVICE,
                            imgsz=IMGSZ, plots=False)
        val_ultralytics = {
            "map50": float(results.box.map50),
            "map50_95": float(results.box.map),
            "precision": float(results.box.mp),
            "recall": float(results.box.mr),
        }

        # --- TIDE evaluation on val3 and test3 (model.predict, original space) --
        print("TIDE evaluation on val3 ...")
        gt_val = gt_by_class_original(ds, "split3", "val")
        tide_val = evaluate_split(model, [str(p) for p in val_paths], gt_val, len(names))
        print(f"  val3 : mAP50={tide_val['map50']:.4f} TIDE10={tide_val['tide10']:.4f} "
              f"TIDE20={tide_val['tide20']:.4f} TIDE50={tide_val['tide50']:.4f}")
        print("TIDE evaluation on test3 ...")
        gt_test = gt_by_class_original(ds, "split3", "test")
        tide_test = evaluate_split(model, [str(p) for p in test_paths], gt_test, len(names))
        print(f"  test3: mAP50={tide_test['map50']:.4f} TIDE10={tide_test['tide10']:.4f} "
              f"TIDE20={tide_test['tide20']:.4f} TIDE50={tide_test['tide50']:.4f}")

        # --- MLflow metrics ------------------------------------------------------
        mlflow.log_metrics({"val_map50_ultralytics": val_ultralytics["map50"],
                           "val_map50_95_ultralytics": val_ultralytics["map50_95"],
                           "val_map50": tide_val["map50"],
                           "val_tide10": tide_val["tide10"],
                           "val_tide20": tide_val["tide20"],
                           "val_tide50": tide_val["tide50"],
                           "val_precision": tide_val["precision"],
                           "val_recall": tide_val["recall"],
                           "test_map50": tide_test["map50"],
                           "test_tide10": tide_test["tide10"],
                           "test_tide20": tide_test["tide20"],
                           "test_tide50": tide_test["tide50"],
                           "test_precision": tide_test["precision"],
                           "test_recall": tide_test["recall"]})
        run_dir = Path("/tmp/yolo_full")
        best_pt = run_dir / "weights" / "best.pt"
        last_pt = run_dir / "weights" / "last.pt"
        mlflow.log_artifact(str(best_pt))
        mlflow.log_artifact(str(last_pt))
        results_csv = run_dir / "results.csv"
        if results_csv.exists():
            mlflow.log_artifact(str(results_csv))
        mlflow.log_artifact(str(data_yaml))

        # --- S3 publish ------------------------------------------------------------
        run_s3 = f"models/{RUN_ID}/yolo"
        for local, name_ in ((best_pt, "best.pt"), (last_pt, "last.pt"),
                             (results_csv, "results.csv"), (data_yaml, "data.yaml")):
            if local.exists():
                s3.upload_file(str(local), S3_BUCKET, f"{run_s3}/{name_}")
        metrics_json = {
            "train": {"epochs": EPOCHS, "ultralytics_val": val_ultralytics},
            "val3": {k: tide_val[k] for k in ("map50", "tide10", "tide20", "tide50", "precision", "recall")},
            "test3": {k: tide_test[k] for k in ("map50", "tide10", "tide20", "tide50", "precision", "recall")},
        }
        s3.put_object(Bucket=S3_BUCKET, Key=f"{run_s3}/metrics.json",
                      Body=json.dumps(metrics_json, indent=2).encode())
        s3.put_object(Bucket=S3_BUCKET, Key=f"{run_s3}/train_args.json", Body=json.dumps({
            "model": YOLO_MODEL, "imgsz": IMGSZ, "epochs": EPOCHS, "batch": BATCH,
            "commit_id": commit, "num_classes": len(names), "split_counts": cluster_m["split_counts"],
        }).encode())

        manifest = {
            "run_id": RUN_ID,
            "mlflow_run_id": run.info.run_id,
            "mlflow_uri": MLFLOW_TRACKING_URI,
            "mlflow_experiment": "detection_voc12",
            "model": YOLO_MODEL, "imgsz": IMGSZ, "epochs": EPOCHS,
            "commit_id": commit,
            "deeplake_ref": f"{VOC12_DATASET}@{commit}",
            "run_dir_s3": f"s3://{S3_BUCKET}/{run_s3}/",
            "best_pt": f"{run_s3}/best.pt",
            "final": {k: val_ultralytics[k] for k in ("map50", "map50_95")},
            "tide": {"val3": tide_val, "test3": tide_test},
            "class_names": names,
            "stats": {"train": len(train_paths), "val": len(val_paths), "test": len(test_paths)},
        }
        mkey = f"data/{RUN_ID}/yolo_train_manifest.json"
        s3.put_object(Bucket=S3_BUCKET, Key=mkey, Body=json.dumps(manifest, indent=2).encode())
        print(f"TRAIN+EVAL OK: test3 TIDE10/20/50 = "
              f"{tide_test['tide10']:.4f}/{tide_test['tide20']:.4f}/{tide_test['tide50']:.4f}, "
              f"mAP50={tide_test['map50']:.4f}; manifest {mkey}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"train_eval_tide_voc12 finished in {time.time() - t0:.1f}s")