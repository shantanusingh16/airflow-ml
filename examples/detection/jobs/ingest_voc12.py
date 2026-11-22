"""Stage 2 — ENRICHMENT: PASCAL VOC 2012 (MinIO) -> DeepLake dataset `voc12`.

Runs inside a job container (ml-jobrunner or ml-jobrunner-gpu — pure CPU work,
no torch needed). Reads the raw XML annotations from MinIO, parses them, and
commits them as a versioned DeepLake dataset on S3:

    s3://ml-artifacts/deeplake/voc12

Design notes
------------
* Images stay as RAW S3 objects under s3://<bucket>/datasets/voc12/VOC2012/
  (stage 1). DeepLake stores only the annotations + a `image_uri` string per
  sample — the dataset stays small, and the training job streams the JPEGs it
  needs straight from MinIO.
* Each DAG run REBUILDS the dataset from the raw S3 objects (same
  rebuild-from-scratch convention as the platform's `feature_ds`): MinIO raw
  data is the source of truth, and every run yields a fresh dataset + one
  commit, so re-running the pipeline never duplicates rows.
* `ds.commit_id` of the created commit is the version downstream stages
  (sampling / training / eval / export) pin. `ds.info` is the flat key-value
  metadata store (atomic values only: str/int/float/bool).
"""
from __future__ import annotations

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import boto3
import deeplake
import numpy as np

# --- config (all env-driven; job_task() injects the S3_* + platform vars) ----
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]

# s3:// prefix (no bucket) of the uploaded VOC tree from stage 1
VOC_S3_PREFIX = os.environ.get("VOC_S3_PREFIX", "datasets/voc12/VOC2012")
# DeepLake dataset path (S3-backed) this job writes into
VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")

# Class order for the head (index = class id): the 20 classes that appear in the
# VOC2012 annotations (verified against all uploaded XMLs — `plant` is never
# annotated and is omitted; the earlier `truck` entry was a COCO class that does
# not exist in VOC and left the head slot dead). 2007 XMLs label the TV class
# "tvmonitor" and 2012 XMLs label it "TV" — both are normalized to "tvmonitor"
# below. Order follows the canonical PASCAL VOC sequence.
CLASS_NAMES = [
    "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat",
    "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor", "background",
]
CLASS_IDS = {name: i for i, name in enumerate(CLASS_NAMES)}
# XML <name> aliases -> canonical class
NAME_ALIASES = {"tv": "tvmonitor"}


def s3_client() -> "boto3.client":
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=S3_REGION,
    )


def dl_creds() -> dict:
    """DeepLake S3Provider creds (the image env already sets the AWS_* chain,
    but passing an explicit dict is the most robust path for MinIO)."""
    return {
        "aws_access_key_id": S3_ACCESS,
        "aws_secret_access_key": S3_SECRET,
        "aws_region": S3_REGION,
        "endpoint_url": S3_ENDPOINT,
    }


def parse_voc_xml(body: bytes) -> dict:
    root = ET.fromstring(body)
    size = root.find("size")
    objects = []
    for obj in root.findall("object"):
        name = NAME_ALIASES.get((obj.findtext("name") or "").strip().lower(),
                                 (obj.findtext("name") or "").strip().lower())
        bb = obj.find("bndbox")
        objects.append({
            "class": CLASS_IDS.get(name, -1),  # -1 = class not in the list
            "bbox": [int(float(bb.findtext(t))) for t in ("xmin", "ymin", "xmax", "ymax")],
        })
    return {
        "image_id": (root.findtext("filename") or "unknown").rsplit(".", 1)[0],
        "width": int(size.findtext("width")),
        "height": int(size.findtext("height")),
        "objects": objects,
    }


def main() -> None:
    s3 = s3_client()

    # --- enumerate annotations on S3 ----------------------------------------
    ann_prefix = f"{VOC_S3_PREFIX}/Annotations/"
    keys = []
    token = None
    while True:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=ann_prefix, ContinuationToken=token) if token \
            else s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=ann_prefix)
        keys += [o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith(".xml")]
        if not resp.get("IsTruncated"):
            break
        token = resp["NextContinuationToken"]
    if not keys:
        sys.exit(f"no .xml annotations found under s3://{S3_BUCKET}/{ann_prefix} — did stage 1 run?")
    print(f"found {len(keys)} annotation files under s3://{S3_BUCKET}/{ann_prefix}")

    # --- parse all XMLs ------------------------------------------------------
    rows = []
    for key in keys:
        body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
        img = parse_voc_xml(body)
        img_name = key.split("/")[-1].rsplit(".", 1)[0] + ".jpg"
        rows.append({
            "image_id": img["image_id"],
            "image_uri": f"s3://{S3_BUCKET}/{VOC_S3_PREFIX}/JPEGImages/{img_name}",
            "class_ids": np.asarray([o["class"] for o in img["objects"]], dtype=np.int64),
            "bboxes": np.asarray([o["bbox"] for o in img["objects"]], dtype=np.float32).reshape(-1, 4),
            "width": np.int64(img["width"]),
            "height": np.int64(img["height"]),
        })

    # --- commit to DeepLake ---------------------------------------------------
    creds = dl_creds()
    # Fresh dataset for this run (rebuild-from-scratch; see module docstring)
    ds = deeplake.empty(VOC12_DATASET, creds=creds, overwrite=True)
    # class_names tensor: one row per class (kept in the dataset so any
    # downstream job can read the names without hardcoding them)
    ds.create_tensor("class_names", htype="text")
    ds["class_names"].extend(CLASS_NAMES[:-1])  # exclude 'background'
    ds.create_tensor("image_id", htype="text")
    ds.create_tensor("image_uri", htype="text")
    ds.create_tensor("class_ids", htype="generic")
    ds.create_tensor("bboxes", htype="generic")
    ds.create_tensor("width", htype="generic")
    ds.create_tensor("height", htype="generic")

    ds["image_id"].extend([r["image_id"] for r in rows])
    ds["image_uri"].extend([r["image_uri"] for r in rows])
    ds["class_ids"].extend([r["class_ids"] for r in rows])
    ds["bboxes"].extend([r["bboxes"] for r in rows])
    ds["width"].extend([r["width"] for r in rows])
    ds["height"].extend([r["height"] for r in rows])

    # flat key-value metadata (atomic types only)
    n_boxes = sum(len(r["class_ids"]) for r in rows)
    ds.info["dataset_kind"] = "detection"
    ds.info["source"] = "PASCAL VOC 2012 trainval"
    ds.info["source_s3_prefix"] = f"s3://{S3_BUCKET}/{VOC_S3_PREFIX}/"
    ds.info["num_classes"] = len(CLASS_NAMES) - 1
    ds.info["num_images"] = int(len(rows))
    ds.info["num_boxes"] = int(n_boxes)
    ds.info["ingested_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ds.info["ingested_by_run"] = RUN_ID

    commit_id = ds.commit(message=f"ingest VOC2012 from s3://{S3_BUCKET}/{VOC_S3_PREFIX}/")
    print(f"DeepLake commit {commit_id[:12]} ... tensors: {list(ds.tensors)}")

    # --- publish run manifest to S3 (other jobs / humans read this) ----------
    manifest = {
        "run_id": RUN_ID,
        "dataset": VOC12_DATASET,
        "commit_id": commit_id,
        "commit_message": f"ingest VOC2012 from s3://{S3_BUCKET}/{VOC_S3_PREFIX}/",
        "image_count": len(rows),
        "box_count": n_boxes,
        "tensors": {
            t: {"rows": len(ds[t])} for t in ("image_id", "image_uri", "class_ids", "bboxes", "width", "height")
        },
        "info": dict(ds.info),
        "s3_prefix": f"s3://{S3_BUCKET}/{VOC_S3_PREFIX}/",
    }
    key = f"data/{RUN_ID}/voc12_ingest_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(manifest, indent=2).encode())
    print(f"manifest published: s3://{S3_BUCKET}/{key}")
    print(f"INGEST OK: {len(rows)} images, {n_boxes} boxes -> {VOC12_DATASET} (commit {commit_id[:12]})")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"ingest_voc12 finished in {time.time() - t0:.1f}s")