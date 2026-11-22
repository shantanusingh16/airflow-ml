"""Stage 3 — SAMPLING: deterministic 80/20 train/val split of the `voc12`
DeepLake dataset (head = the commit created by ingest_voc12.py in this run).

* The split is a hash of `image_id` (sha256, first 32 bits % 100 < 20 -> val),
  so it is STABLE across runs/machines — the same image is always train or
  always val.
* The result is stored as a new `split` tensor ("train"/"val") in the SAME
  dataset plus flat kv metadata (`train_count`, `val_count`, ...), committed
  as a NEW DeepLake commit. That commit id is what train/eval/export pin, so
  "which data was trained on" is fully reproducible from the manifest:
      s3://<bucket>/data/<run_id>/voc12_split_manifest.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import boto3
import deeplake
import numpy as np

S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]

VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")
VAL_RATIO = float(os.environ.get("VAL_RATIO", "0.2"))


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
    """DeepLake text samples come back as bytes / np.str_ depending on path;
    normalize to a plain str."""
    a = np.asarray(value)
    v = a.item() if a.size == 1 else a.reshape(-1)[0]
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    return str(v)


def split_of(image_id: str) -> str:
    h = int.from_bytes(hashlib.sha256(image_id.encode("utf-8")).digest()[:4], "big")
    return "val" if h % 100 < int(VAL_RATIO * 100) else "train"


def main() -> None:
    s3 = s3_client()
    creds = dl_creds()

    # Head of the dataset = the ingest commit from this run (stage 2).
    ds = deeplake.load(VOC12_DATASET, read_only=False, creds=creds)
    n = len(ds)
    if n == 0:
        sys.exit(f"{VOC12_DATASET} has no rows — did ingest_voc12 run?")

    splits = []
    for i in range(n):
        splits.append(split_of(text_of(ds["image_id"][i].numpy())))

    ds.create_tensor("split", htype="text")
    ds["split"].extend(splits)

    n_val = splits.count("val")
    ds.info["split_rule"] = f"sha256(image_id) % 100 < {int(VAL_RATIO * 100)} -> val"
    ds.info["val_ratio"] = VAL_RATIO
    ds.info["train_count"] = int(n - n_val)
    ds.info["val_count"] = int(n_val)
    ds.info["sampled_by_run"] = RUN_ID

    commit_id = ds.commit(message=f"deterministic {int((1 - VAL_RATIO) * 100)}/{int(VAL_RATIO * 100)} train/val split")
    print(f"split commit {commit_id[:12]}: train={n - n_val} val={n_val} (of {n})")

    manifest = {
        "run_id": RUN_ID,
        "dataset": VOC12_DATASET,
        "commit_id": commit_id,
        "total": n,
        "train_count": n - n_val,
        "val_count": n_val,
        "val_ratio": VAL_RATIO,
        "split_rule": ds.info["split_rule"],
        "info": dict(ds.info),
        # downstream jobs pin this:  deeplake.load(f"{VOC12_DATASET}@{commit_id}")
        "deeplake_ref": f"{VOC12_DATASET}@{commit_id}",
    }
    key = f"data/{RUN_ID}/voc12_split_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(manifest, indent=2).encode())
    print(f"manifest published: s3://{S3_BUCKET}/{key}")
    print(f"SAMPLING OK: pin commit {commit_id[:12]} (train={n - n_val}, val={n_val})")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"sample_voc12 finished in {time.time() - t0:.1f}s")