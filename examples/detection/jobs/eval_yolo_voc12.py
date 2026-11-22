"""Stage 6 — EVALUATION: mAP50 on the val split, two backends, one guard.

* torch:    YOLO(best.pt) on the val split  (what the trainer reported)
* triton:   the ONNX model SERVED BY TRITON over gRPC — images preprocessed
            in pure numpy/OpenCV, raw output [1, 1+K, A] decoded + NMS'd in
            numpy (no torch on the inference path)

The hard guard `|mAP50_triton - mAP50_torch| <= MAP50_TOLERANCE` (default
0.05) fails the DAG if the served artifact drifts from the trained weights.
Results are logged to the MLflow experiment `detection_voc12` as run
`evaluate-<run_id>` (tag `inference_backend=triton`) and to S3:
    models/<run_id>/yolo/eval_metrics.json
    data/<run_id>/yolo_eval_manifest.json

Runs in the GPU job image (torch needed for the torch-side check).
"""
from __future__ import annotations

import json
import os
import sys
import time

import boto3
import cv2
import deeplake
import mlflow
import numpy as np
import torch
from tritonclient import grpc as gc
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
IMGSZ = int(os.environ.get("IMGSZ", "640"))
CONF_THRESH = float(os.environ.get("CONF_THRESH", "0.25"))
IOU_THRESH = float(os.environ.get("IOU_THRESH", "0.45"))
MAP50_TOLERANCE = float(os.environ.get("MAP50_TOLERANCE", "0.05"))
GPU_DEVICE = int(os.environ.get("GPU_DEVICE", "0"))
BATCH = 16
ROOT = "/tmp/voc12_eval"


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


# --- geometry -----------------------------------------------------------------
def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (4,) x1 y1 x2 y2 ; b: (N, 4) -> (N,)"""
    x1 = np.maximum(a[0], b[:, 0]); y1 = np.maximum(a[1], b[:, 1])
    x2 = np.minimum(a[2], b[:, 2]); y2 = np.minimum(a[3], b[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = np.maximum(0, b[:, 2] - b[:, 0]) * np.maximum(0, b[:, 3] - b[:, 1])
    return inter / np.maximum(1e-9, area_a + area_b - inter)


def nms(dets: np.ndarray, iou_thresh: float = IOU_THRESH) -> np.ndarray:
    """dets: (N, 6) = x1 y1 x2 y2 conf cls -> kept subset (same rows)."""
    if len(dets) == 0:
        return dets
    order = dets[:, 4].argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        iou = box_iou(dets[i][:4], dets[rest][:4])
        order = np.concatenate([[i], rest[iou < iou_thresh]])
    return dets[keep]


def decode_yolo_output(out: np.ndarray, imgsz: int) -> np.ndarray:
    """out: (1+K, A) single image, YOLO11 ONNX layout (no objectness head):
    rows 0-3 = cx cy w h (px in imgsz space), rows 4.. = class scores.
    Returns (N, 6) = x1 y1 x2 y2 conf cls."""
    boxes = out[:4].T                       # (A, 4)
    scores = out[4:].T                      # (A, K)
    if scores.max() > 1.5:                  # raw logits rather than probabilities
        scores = 1.0 / (1.0 + np.exp(-scores))
    conf = scores.max(axis=1)
    cls = scores.argmax(axis=1)
    keep = conf >= CONF_THRESH
    boxes, conf, cls = boxes[keep], conf[keep], cls[keep]
    if len(conf) == 0:
        return np.zeros((0, 6))
    x1 = np.clip(boxes[:, 0] - boxes[:, 2] / 2, 0, imgsz)
    y1 = np.clip(boxes[:, 1] - boxes[:, 3] / 2, 0, imgsz)
    x2 = np.clip(boxes[:, 0] + boxes[:, 2] / 2, 0, imgsz)
    y2 = np.clip(boxes[:, 1] + boxes[:, 3] / 2, 0, imgsz)
    dets = np.column_stack([x1, y1, x2, y2, conf, cls.astype(np.int64)])
    return nms(dets)


def ap_101(tp: list, fp: list, n_gt: int) -> float:
    """Average precision via 101-point interpolation (Pascal VOC style)."""
    if n_gt == 0:
        return 0.0
    tp = np.cumsum(np.asarray(tp, dtype=np.float64))
    fp = np.cumsum(np.asarray(fp, dtype=np.float64))
    rec = tp / n_gt
    prec = tp / np.maximum(1e-9, tp + fp)
    ap = 0.0
    for r in np.linspace(0.0, 1.0, 101):
        idx = np.where(rec >= r)[0]
        ap += (prec[idx].max() if idx.size else 0.0) / 101.0
    return float(ap)


def map50_from_dets(per_image_dets: dict, gt_by_class: dict, num_classes: int) -> dict:
    """per_image_dets: img_id -> (N, 6) [x1 y1 x2 y2 conf cls]
    gt_by_class: class -> img_id -> list of (x1, y1, x2, y2) in the SAME space
    as the detections. Returns {class: AP}."""
    ap = {}
    for c in range(num_classes):
        preds = []
        for img, dets in per_image_dets.items():
            for row in dets[dets[:, 5] == c]:
                preds.append((row[4], img, row[:4]))
        preds.sort(key=lambda p: -p[0])
        tp, fp = [], []
        used = {img: [False] * len(gt_by_class.get(c, {}).get(img, []))
                for img in per_image_dets}
        for conf, img, box in preds:
            gts = gt_by_class.get(c, {}).get(img, [])
            hit = -1
            if gts:
                ious = box_iou(box, np.asarray(gts))
                for g, iou in enumerate(ious):
                    if iou >= 0.5 and not used[img][g]:
                        hit = g
                        break
            if hit >= 0:
                used[img][hit] = True
                tp.append(1.0); fp.append(0.0)
            else:
                tp.append(0.0); fp.append(1.0)
        n_gt = sum(len(v) for v in gt_by_class.get(c, {}).values())
        ap[c] = ap_101(tp, fp, n_gt)
    return ap


# --- data ---------------------------------------------------------------------
def load_val(ds, s3) -> tuple[list, list, list]:
    """Download the val images (for the torch side) and return
    (img_ids, local_paths, dataset_row_indices) in dataset order."""
    os.makedirs(f"{ROOT}/raw", exist_ok=True)
    ids, paths, idx = [], [], []
    for i in range(len(ds)):
        if text_of(ds["split"][i].numpy()) != "val":
            continue
        img_id = text_of(ds["image_id"][i].numpy())
        key = text_of(ds["image_uri"][i].numpy()).split("/", 3)[3]
        local = os.path.join(ROOT, "raw", os.path.basename(key))
        if not os.path.exists(local):
            s3.download_file(S3_BUCKET, key, local)
        ids.append(img_id)
        paths.append(local)
        idx.append(i)
    return ids, paths, idx


def gt_by_class_640(ds, val_idx: list, imgsz: int) -> tuple[dict, int]:
    """Ground-truth boxes per class, scaled into the imgsz space (stretch),
    matching the triton-side preprocessing."""
    gt = {}
    n_classes = 0
    for i in val_idx:
        img_id = text_of(ds["image_id"][i].numpy())
        w, h = scalar_of(ds["width"][i].numpy()), scalar_of(ds["height"][i].numpy())
        cls = ds["class_ids"][i].numpy().astype(np.int64).reshape(-1)
        bb = ds["bboxes"][i].numpy().astype(np.float64)
        for c, (x1, y1, x2, y2) in zip(cls, bb):
            c = int(c)
            if c < 0:
                continue
            n_classes = max(n_classes, c + 1)
            box = (x1 * imgsz / w, y1 * imgsz / h, x2 * imgsz / w, y2 * imgsz / h)
            gt.setdefault(c, {}).setdefault(img_id, []).append(box)
    return gt, n_classes


def write_val_yaml(ds, val_idx: list, names: list) -> None:
    """YOLO layout for the torch-side validation:
    {ROOT}/val/images/*.jpg (symlinks) + {ROOT}/val/labels/*.txt."""
    os.makedirs(f"{ROOT}/val/images", exist_ok=True)
    os.makedirs(f"{ROOT}/val/labels", exist_ok=True)
    for i, img_id in zip(val_idx, [text_of(ds["image_id"][k].numpy()) for k in val_idx]):
        cls = ds["class_ids"][i].numpy().astype(np.int64).reshape(-1)
        bb = ds["bboxes"][i].numpy().astype(np.float64)
        w, h = scalar_of(ds["width"][i].numpy()), scalar_of(ds["height"][i].numpy())
        lines = []
        for c, (x1, y1, x2, y2) in zip(cls, bb):
            if c < 0:
                continue
            lines.append(f"{int(c)} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} "
                         f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
        with open(f"{ROOT}/val/labels/{img_id}.txt", "w") as f:
            f.write("\n".join(lines))
    # symlinks: raw basename is unique per image
    for i in val_idx:
        img_id = text_of(ds["image_id"][i].numpy())
        uri = text_of(ds["image_uri"][i].numpy())
        src = os.path.join(ROOT, "raw", os.path.basename(uri))
        link = f"{ROOT}/val/images/{os.path.basename(uri)}"
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(src, link)

    with open(f"{ROOT}/data.yaml", "w") as f:
        f.write(f"path: {ROOT}\nval: val\nnames: {json.dumps(names)}\n")


def main() -> None:
    if not torch.cuda.is_available():
        sys.exit("CUDA not visible in this container — the eval task must use gpu_job_task()")

    s3 = s3_client()
    creds = dl_creds()
    split_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/voc12_split_manifest.json")["Body"].read())
    train_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/yolo_train_manifest.json")["Body"].read())
    export_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/yolo_export_manifest.json")["Body"].read())

    commit = split_m["commit_id"]
    ds = deeplake.load(f"{VOC12_DATASET}@{commit}", read_only=True, creds=creds)
    names = train_m["class_names"]
    num_classes = len(names)
    model_name = export_m["triton_model"]
    in_name = export_m["input"]["name"]
    out_name = export_m["output"]["name"]

    ids, paths, val_idx = load_val(ds, s3)
    if not ids:
        sys.exit("no val images in this run's split")
    print(f"evaluating {len(ids)} val images (commit {commit[:12]})")
    gt, _ = gt_by_class_640(ds, val_idx, IMGSZ)

    # --- torch side -----------------------------------------------------------
    pt_key = train_m["best_pt"].split(f"s3://{S3_BUCKET}/", 1)[-1]
    pt_local = "/tmp/best.pt"
    s3.download_file(S3_BUCKET, pt_key, pt_local)
    write_val_yaml(ds, val_idx, names)
    model = YOLO(pt_local)
    results = model.val(data=f"{ROOT}/data.yaml", split="val", device=GPU_DEVICE, imgsz=IMGSZ, plots=False)
    torch_metrics = {
        "map50": float(results.box.map50),
        "map50_95": float(results.box.map),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
    }
    print(f"torch  mAP50={torch_metrics['map50']:.4f} mAP50-95={torch_metrics['map50_95']:.4f}")

    # --- triton side (gRPC batched inference, numpy decode + NMS) -------------
    client = gc.InferenceServerClient(url=export_m["triton_grpc"])
    if not client.is_model_ready(model_name):
        sys.exit(f"triton model '{model_name}' is not ready on {export_m['triton_grpc']}")

    per_image_dets = {}
    for b0 in range(0, len(paths), BATCH):
        chunk = paths[b0:b0 + BATCH]
        imgs, kept = [], []
        for p, img_id in zip(chunk, ids[b0:b0 + BATCH]):
            img = cv2.imread(p)
            if img is None:
                continue
            x = (cv2.resize(img, (IMGSZ, IMGSZ))[:, :, ::-1]
                 .transpose(2, 0, 1).astype(np.float32) / 255.0)
            imgs.append(x)
            kept.append(img_id)
        if not imgs:
            continue
        xs = np.stack(imgs)
        inp = gc.InferInput(in_name, list(xs.shape), "FP32")
        inp.set_data_from_numpy(xs)
        resp = client.infer(model_name=model_name, inputs=[inp])
        ys = resp.as_numpy(out_name)                     # (B, 1+K, A)
        for img_id, y in zip(kept, ys):
            per_image_dets[img_id] = decode_yolo_output(np.squeeze(y, axis=0), IMGSZ)

    triton_ap = map50_from_dets(per_image_dets, gt, num_classes)
    map50_triton = float(np.mean(list(triton_ap.values())))
    n_dets = sum(len(v) for v in per_image_dets.values())
    print(f"triton mAP50={map50_triton:.4f} ({n_dets} detections @ conf>={CONF_THRESH})")

    # --- guard ----------------------------------------------------------------
    delta = abs(torch_metrics["map50"] - map50_triton)
    if delta > MAP50_TOLERANCE:
        print(f"EVAL FAIL: |mAP50_triton - mAP50_torch| = {delta:.4f} > {MAP50_TOLERANCE} "
              f"— served model drifts from trained weights")
        sys.exit(1)

    # --- MLflow (evaluate batch) + S3 ------------------------------------------
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("detection_voc12")
    with mlflow.start_run(run_name=f"evaluate-{RUN_ID}") as run:
        mlflow.log_params({
            "triton_model": model_name,
            "triton_grpc": export_m["triton_grpc"],
            "dataset_commit": commit,
            "imgsz": IMGSZ,
            "conf_thresh": CONF_THRESH,
            "iou_thresh": IOU_THRESH,
            "val_images": len(ids),
        })
        mlflow.set_tag("batch", "evaluate")
        mlflow.set_tag("inference_backend", "triton")
        mlflow.log_metrics({
            "map50_triton": map50_triton,
            "map50_torch": torch_metrics["map50"],
            "map50_delta": delta,
            "map50_95_torch": torch_metrics["map50_95"],
            "precision_torch": torch_metrics["precision"],
            "recall_torch": torch_metrics["recall"],
        })

    eval_metrics = {
        "inference_backend": "triton",
        "triton_model": model_name,
        "map50_triton": map50_triton,
        "map50_torch": torch_metrics["map50"],
        "map50_delta": delta,
        "map50_95_torch": torch_metrics["map50_95"],
        "precision_torch": torch_metrics["precision"],
        "recall_torch": torch_metrics["recall"],
        "per_class_ap_triton": {names[c]: round(v, 4) for c, v in triton_ap.items() if c < len(names)},
        "val_images": len(ids),
        "detections": n_dets,
    }
    run_s3 = f"models/{RUN_ID}/yolo"
    s3.put_object(Bucket=S3_BUCKET, Key=f"{run_s3}/eval_metrics.json",
                  Body=json.dumps(eval_metrics, indent=2).encode())
    manifest = {
        "run_id": RUN_ID,
        "commit_id": commit,
        "triton_model": model_name,
        "map50_torch": torch_metrics["map50"],
        "map50_triton": map50_triton,
        "delta": delta,
        "tolerance": MAP50_TOLERANCE,
        "val_images": len(ids),
        "eval_metrics_s3": f"s3://{S3_BUCKET}/{run_s3}/eval_metrics.json",
    }
    mkey = f"data/{RUN_ID}/yolo_eval_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=mkey, Body=json.dumps(manifest, indent=2).encode())
    print(f"EVAL OK: mAP50 torch={torch_metrics['map50']:.4f} triton={map50_triton:.4f} "
          f"(delta {delta:.5f} <= {MAP50_TOLERANCE}); manifest {mkey}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"eval_yolo_voc12 finished in {time.time() - t0:.1f}s")