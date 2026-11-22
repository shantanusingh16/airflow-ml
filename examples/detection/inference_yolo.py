#!/usr/bin/env python3
"""Standalone inference test for the YOLO model deployed on Triton.

Runs the deployed model (ONNX via the onnxruntime backend, explicit model
control) on one or more local images and prints detections with class names
read from the model's `model_info.json` (staged at the model root by the
export job).

No credentials are needed for Triton — it is an internal service; from the
host use the published ports (gRPC 8000 / HTTP 8005), from a container on
airflow-ml-net use triton:8000 / http://triton:8005.

Usage (from the project root, inside the GPU job image — it has tritonclient
+ opencv):

  docker run --rm --network airflow-ml-net \
      -v "$PWD:/host:ro" \
      -e TRITON_GRPC_URL=triton:8000 \
      -e TRITON_DET_MODEL=yolo_voc12 \
      ml-jobrunner-gpu:latest \
      python /host/examples/detection/inference_yolo.py \
      /host/voc12/VOC2012/JPEGImages/000005.jpg \
      /host/voc12/VOC2012/JPEGImages/000032.jpg

  # host-side venv variant (gRPC against the published port):
  #   python3 -m venv .venv && .venv/bin/pip install "tritonclient[all]" opencv-python
  #   TRITON_GRPC_URL=localhost:8000 .venv/bin/python examples/detection/inference_yolo.py img.jpg
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from tritonclient import grpc as gc

TRITON_GRPC_URL = os.environ.get("TRITON_GRPC_URL", "localhost:8000")
MODEL_NAME = os.environ.get("TRITON_DET_MODEL", "yolo_voc12")
IMGSZ = int(os.environ.get("IMGSZ", "640"))
CONF_THRESH = float(os.environ.get("CONF_THRESH", "0.25"))
IOU_THRESH = float(os.environ.get("IOU_THRESH", "0.45"))

# Model repository mount (readable from job containers; on the host it is
# <project>/triton-models). model_info.json lives at the model root.
MODELS_ROOT = os.environ.get("MODELS_ROOT", "/models")
MODELS_ROOT_HOST = os.environ.get("MODELS_ROOT_HOST", "triton-models")


def load_model_info(model: str) -> dict:
    for base in (MODELS_ROOT, MODELS_ROOT_HOST):
        p = Path(base) / model / "model_info.json"
        if p.exists():
            return json.loads(p.read_text())
    # fall back to the S3-published copy is overkill for a test client;
    # hardcode the known YOLO11 layout instead
    return {"input": {"name": "images", "dims": [0, 3, IMGSZ, IMGSZ]},
            "output": {"name": "output0", "dims": [0, 21, 8400]},
            "class_names": ["aeroplane", "bicycle", "bird", "boat", "bottle",
                            "bus", "car", "cat", "chair", "cow", "diningtable",
                            "dog", "horse", "motorbike", "person", "pottedplant",
                            "sheep", "sofa", "train", "tvmonitor"]}


def box_iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    ab = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / max(1e-9, aa + ab - inter)


def nms(dets, iou_thresh=IOU_THRESH):
    order = sorted(range(len(dets)), key=lambda i: -dets[i][4])
    keep, used = [], set()
    for i in order:
        if i in used:
            continue
        keep.append(i)
        for j in order:
            if j in used or j == i:
                continue
            if box_iou(dets[i][:4], dets[j][:4]) > iou_thresh:
                used.add(j)
    return [dets[i] for i in keep]


def decode(out, imgsz, conf_thresh):
    """out: (1+K, A) -> list of (conf, cls, x1, y1, x2, y2)."""
    boxes = out[:4].T
    scores = out[4:].T
    if scores.max() > 1.5:
        scores = 1.0 / (1.0 + np.exp(-scores))
    conf = scores.max(axis=1)
    cls = scores.argmax(axis=1)
    dets = []
    for a in range(len(conf)):
        if conf[a] < conf_thresh:
            continue
        cx, cy, w, h = boxes[a]
        dets.append([
            max(0.0, cx - w / 2), max(0.0, cy - h / 2),
            min(float(imgsz), cx + w / 2), min(float(imgsz), cy + h / 2),
            float(conf[a]), int(cls[a]),
        ])
    return nms(dets)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    client = gc.InferenceServerClient(url=TRITON_GRPC_URL)
    if not client.is_server_ready():
        sys.exit(f"triton server not ready at {TRITON_GRPC_URL}")
    if not client.is_model_ready(MODEL_NAME):
        sys.exit(f"model '{MODEL_NAME}' not loaded on {TRITON_GRPC_URL} "
                 f"(run the export stage or load it explicitly)")
    info = load_model_info(MODEL_NAME)
    in_name = info["input"]["name"]
    out_name = info["output"]["name"]
    names = info.get("class_names", [f"class-{i}" for i in range(info["output"]["dims"][1] - 1)])
    print(f"model: {MODEL_NAME} @ {TRITON_GRPC_URL} | input {info['input']} | "
          f"{len(names)} classes | conf>={CONF_THRESH} iou<={IOU_THRESH}\n")

    total = 0
    for image_path in sys.argv[1:]:
        img = cv2.imread(image_path)
        if img is None:
            print(f"!! cannot read {image_path}"); continue
        h, w = img.shape[:2]
        x = (cv2.resize(img, (IMGSZ, IMGSZ))[:, :, ::-1]
             .transpose(2, 0, 1).astype(np.float32) / 255.0)
        inp = gc.InferInput(in_name, [1] + list(x.shape), "FP32")
        inp.set_data_from_numpy(x)
        resp = client.infer(model_name=MODEL_NAME, inputs=[inp])
        y = resp.as_numpy(out_name)
        dets = decode(np.squeeze(y, axis=0), IMGSZ, CONF_THRESH)
        # map 640-space boxes back to the original image (undo the stretch)
        dets = [[conf, names[cls],
                 x1 * w / IMGSZ, y1 * h / IMGSZ, x2 * w / IMGSZ, y2 * h / IMGSZ]
                for (x1, y1, x2, y2, conf, cls) in dets]
        total += len(dets)
        print(f"== {os.path.basename(image_path)} ({w}x{h}) : {len(dets)} detections")
        for conf, cls_name, x1, y1, x2, y2 in sorted(dets, key=lambda d: -d[0]):
            print(f"   {cls_name:10s} {conf:.3f}  box=[{x1:6.1f} {y1:6.1f} {x2:6.1f} {y2:6.1f}]")
    print(f"\n{total} total detections via Triton ({MODEL_NAME})")


if __name__ == "__main__":
    main()