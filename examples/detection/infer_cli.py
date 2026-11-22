#!/usr/bin/env python3
"""Standalone detection client for the YOLO11 model deployed on Triton.

Runs on the HOST with no ML stack (Python 3.11+; needs only PIL, numpy,
requests — already present):

    python3 infer_cli.py <image_path>

prints a JSON dict with every bbox + confidence to stdout and writes an
annotated copy of the image next to it:

    <image_stem>_detected.jpg

The deployed model is the raw YOLO11 detection head (no NMS op) served by
Triton's onnxruntime backend, so the raw anchors come back unfiltered and
**this script does the post-processing itself**: letterbox/normalize ->
Triton HTTP inference -> decode [1, 4+nc, 8400] -> confidence filter ->
per-class NMS -> letterbox inverse map.

Endpoints / model knobs (env-overridable):
    TRITON_HTTP_URL  default http://localhost:8005 (published Triton port)
    TRITON_MODEL     default yolo_voc12
    MODEL_INFO_JSON  model_info.json written by the export job into the local
                     Triton repository dir; default
                     <project>/triton-models/<model>/model_info.json
                     (gives exact input/output names, imgsz, class names;
                     falls back to YOLO11 defaults when absent)
    DET_CONF         confidence threshold (default 0.25)
    DET_NMS_IOU      NMS IoU threshold (default 0.45)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

# --- configuration -----------------------------------------------------------
TRITON_HTTP_URL = os.environ.get("TRITON_HTTP_URL", "http://localhost:8005")
MODEL_NAME = os.environ.get("TRITON_MODEL", "yolo_voc12")
CONF = float(os.environ.get("DET_CONF", "0.25"))
NMS_IOU = float(os.environ.get("DET_NMS_IOU", "0.45"))

PROJECT_DIR = Path(os.environ.get("AIRFLOW_PROJ_DIR",
                                  "/run/media/shantanu/Volume/Projects/airflow-ml"))
MODEL_INFO = Path(os.environ.get(
    "MODEL_INFO_JSON", PROJECT_DIR / "triton-models" / MODEL_NAME / "model_info.json"))

# YOLO11 defaults (used when model_info.json is not present yet)
DEFAULTS = {
    "input": {"name": "images", "dims": [-1, 3, 640, 640]},
    "output": {"name": "output0", "dims": [-1, 24, 8400]},
    "imgsz": 640,
    "class_names": [
        "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car",
        "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike",
        "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor",
    ],
}

# VOC class order must match the trained dataset (ingest_voc12.py CLASS_NAMES)
VOC_NAMES = DEFAULTS["class_names"]


def load_model_info() -> dict:
    info = dict(DEFAULTS)
    if MODEL_INFO.exists():
        with open(MODEL_INFO) as f:
            data = json.load(f)
        info["input"] = data["input"]
        info["output"] = data["output"]
        info["imgsz"] = int(data.get("imgsz", 640))
        if data.get("class_names"):
            info["class_names"] = data["class_names"]
        print(f"[info] model config: {MODEL_INFO}", file=sys.stderr)
    else:
        print(f"[warn] {MODEL_INFO} not found — using YOLO11 defaults", file=sys.stderr)
    return info


# --- preprocessing (matches ultralytics LetterBox) ----------------------------
def letterbox(img: Image.Image, sz: int) -> tuple[Image.Image, float, int, int]:
    """Resize preserving aspect ratio, pad with 114 to sz x sz.
    Returns (padded, scale, pad_left, pad_top)."""
    w, h = img.size
    r = min(sz / w, sz / h)
    nw, nh = max(1, round(w * r)), max(1, round(h * r))
    canvas = Image.new("RGB", (sz, sz), (114, 114, 114))
    resized = img.resize((nw, nh), Image.BILINEAR)
    dx, dy = (sz - nw) // 2, (sz - nh) // 2
    canvas.paste(resized, (dx, dy))
    return canvas, r, dx, dy


def to_tensor(img: Image.Image, sz: int) -> np.ndarray:
    """RGB PIL -> [1, 3, sz, sz] float32 /255 (what the ONNX graph expects)."""
    padded, *_ = letterbox(img, sz)
    arr = np.asarray(padded, dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)[None]


def from_letterbox(xyxy: np.ndarray, r: float, dx: int, dy: int,
                   img_w: int, img_h: int) -> np.ndarray:
    """640-space boxes -> original image pixels (clipped)."""
    out = np.asarray(xyxy, dtype=np.float64)
    out[:, [0, 2]] = (out[:, [0, 2]] - dx) / r
    out[:, [1, 3]] = (out[:, [1, 3]] - dy) / r
    out[:, [0, 2]] = np.clip(out[:, [0, 2]], 0, img_w - 1)
    out[:, [1, 3]] = np.clip(out[:, [1, 3]], 0, img_h - 1)
    return out


# --- Triton HTTP inference -----------------------------------------------------
def triton_infer(info: dict, x: np.ndarray) -> np.ndarray:
    payload = {
        "model_name": MODEL_NAME,
        "inputs": [{"name": info["input"]["name"],
                    "shape": list(x.shape), "datatype": "FP32",
                    "data": x.ravel().tolist()}],
    }
    url = f"{TRITON_HTTP_URL}/v2/models/{MODEL_NAME}/infer"
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    body = resp.json()
    out = body["outputs"][0]
    return np.asarray(out["data"], dtype=np.float32).reshape(out["shape"])


# --- post-processing -----------------------------------------------------------
def batch_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a (N,4) xyxy, b (M,4) -> (N,M) IoU."""
    ax1, ay1, ax2, ay2 = a.T
    bx1, by1, bx2, by2 = b.T
    xx1 = np.maximum(ax1[:, None], bx1[None, :])
    yy1 = np.maximum(ay1[:, None], by1[None, :])
    xx2 = np.minimum(ax2[:, None], bx2[None, :])
    yy2 = np.minimum(ay2[:, None], by2[None, :])
    inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
    aa = np.maximum(0, ax2 - ax1) * np.maximum(0, ay2 - ay1)
    ab = np.maximum(0, bx2 - bx1) * np.maximum(0, by2 - by1)
    return inter / np.maximum(1e-9, aa[:, None] + ab[None, :] - inter)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        rest = order[1:]
        if rest.size == 0:
            break
        order = rest[batch_iou(boxes[i][None, :], boxes[rest])[0] <= iou_thr]
    return keep


def decode(info: dict, raw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """[1, 4+nc, A] -> (boxes 640-space xyxy, class_ids, confidences)."""
    anchors = raw[0].T                      # (A, 4+nc)
    boxes = anchors[:, 0:4].copy()          # cx, cy, w, h
    boxes[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    boxes[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    boxes[:, 2] = boxes[:, 0] + boxes[:, 2]
    boxes[:, 3] = boxes[:, 1] + boxes[:, 3]
    scores = anchors[:, 4:]
    class_ids = scores.argmax(axis=1)
    confs = scores[np.arange(scores.shape[0]), class_ids]
    sel = confs >= CONF
    return boxes[sel], class_ids[sel], confs[sel]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"usage: python3 {Path(sys.argv[0]).name} <image_path>")
    image_path = Path(sys.argv[1]).expanduser().resolve()
    if not image_path.exists():
        sys.exit(f"image not found: {image_path}")
    info = load_model_info()
    imgsz = int(info["imgsz"])
    names = info["class_names"]

    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size

    # --- infer ----------------------------------------------------------------
    x = to_tensor(img, imgsz)
    raw = triton_infer(info, x)
    boxes, class_ids, confs = decode(info, raw)
    if len(boxes) == 0:
        detections: list[dict] = []
        kept_idx: list[int] = []
    else:
        # per-class NMS (each class independently, like standard detector eval)
        kept_idx = []
        for c in sorted(set(class_ids.tolist())):
            idx = np.where(class_ids == c)[0]
            keep = nms(boxes[idx], confs[idx], NMS_IOU)
            kept_idx += [int(i) for i in idx[keep]]
        kept_idx.sort(key=lambda i: -confs[i])
        r, dx, dy = letterbox(img, imgsz)[1:4]
        boxes_orig = from_letterbox(boxes[kept_idx], r, dx, dy, img_w, img_h)
        detections = [{
            "class_id": int(class_ids[i]),
            "class": names[class_ids[i]] if int(class_ids[i]) < len(names)
                     else f"class_{int(class_ids[i])}",
            "confidence": round(float(confs[i]), 4),
            "bbox": [round(v, 1) for v in row],
        } for i, row in zip(kept_idx, boxes_orig)]
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        color = _class_color(det["class_id"], len(names))
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
        label = f"{det['class']} {det['confidence']:.2f}"
        ty = max(0, y1 - 14)
        draw.rectangle([x1, ty, x1 + 8 * len(label) + 6, ty + 14], fill=color)
        draw.text((x1 + 3, ty + 1), label, fill=(255, 255, 255))
    out_path = image_path.with_name(f"{image_path.stem}_detected.jpg")
    annotated.save(out_path, quality=90)

    # --- JSON to stdout ----------------------------------------------------------
    result = {
        "image": str(image_path),
        "model": MODEL_NAME,
        "triton_http_url": TRITON_HTTP_URL,
        "input_shape": [1, 3, imgsz, imgsz],
        "raw_anchor_count": int(raw.shape[-1]),
        "conf_threshold": CONF,
        "nms_iou": NMS_IOU,
        "nms_applied": "client-side (deployed ONNX head is NMS-free)",
        "image_size": [img_w, img_h],
        "num_detections": len(detections),
        "detections": detections,
        "output_image": str(out_path),
    }
    print(json.dumps(result, indent=2))


def _class_color(c: int, n: int):
    """Deterministic vivid-ish color per class (no matplotlib on the host)."""
    if n <= 1:
        return (255, 80, 80)
    hue = (c * 360) % 360
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hue / 360, 0.55, 0.85)
    return int(r * 255), int(g * 255), int(b * 255)


if __name__ == "__main__":
    main()