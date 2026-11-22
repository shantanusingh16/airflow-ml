#!/usr/bin/env python3
"""Stage 1 (host): bulk-upload VOC2012 into MinIO, then write a flat
key-value manifest so later steps (and humans) can list what is available.

Objects land in:   s3://ml-artifacts/datasets/voc12/VOC2012/...  (mirrors the
local tree) and the manifest at s3://ml-artifacts/datasets/voc12/manifest.json

Credentials: env S3_ENDPOINT / S3_ACCESS_KEY / S3_SECRET_KEY / S3_BUCKET
(defaults: localhost:9000 + minioadmin — i.e. run this on the HOST against
the published MinIO port, or inside a job container against http://minio:9000).

Run inside the job image (has boto3):
  docker run --rm -v "$PWD:/host:ro" \
      -e S3_ENDPOINT=http://localhost:9000 -e S3_ACCESS_KEY=minioadmin -e S3_SECRET_KEY=minioadmin \
      ml-jobrunner:latest python /host/examples/detection/upload_voc12.py /host/voc12/VOC2012
"""
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3

ENDPOINT = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
BUCKET = os.environ.get("S3_BUCKET", "ml-artifacts")
ACCESS = os.environ.get("S3_ACCESS_KEY", "minioadmin")
SECRET = os.environ.get("S3_SECRET_KEY", "minioadmin")
REGION = os.environ.get("S3_REGION", "us-east-1")
PREFIX = os.environ.get("S3_DATASET_PREFIX", "datasets/voc12")

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS,
    aws_secret_access_key=SECRET,
    region_name=REGION,
)


def to_key(path: Path, tree_root: Path) -> str:
    # .../voc12/VOC2012/JPEGImages/x.jpg -> datasets/voc12/VOC2012/JPEGImages/x.jpg
    return f"{PREFIX}/{path.relative_to(tree_root).as_posix()}"


def main() -> None:
    tree = Path(sys.argv[1] if len(sys.argv) > 1 else "voc12/VOC2012")
    if not tree.is_dir():
        sys.exit(f"dataset tree not found: {tree}")

    files = sorted(p for p in tree.rglob("*") if p.is_file())
    n_jpg = sum(1 for p in files if p.suffix == ".jpg")
    n_xml = sum(1 for p in files if p.suffix == ".xml")
    print(f"uploading {len(files)} files ({n_jpg} jpg, {n_xml} xml) to s3://{BUCKET}/{PREFIX}/ ...")

    def put(job):
        src, key = job
        s3.upload_file(str(src), BUCKET, key)
        return key

    jobs = [(f, to_key(f, tree.parent)) for f in files]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(put, jobs))

    # --- verify: what is actually in the bucket now -------------------------
    paginator = s3.get_paginator("list_objects_v2")
    n_objects = 0
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{PREFIX}/"):
        n_objects += len(page.get("Contents", []))
    print(f"verified: {n_objects} objects under s3://{BUCKET}/{PREFIX}/")

    # --- flat key-value manifest (atomic values only) -----------------------
    manifest = {
        "name": "voc12",
        "dataset_kind": "detection",
        "source": "PASCAL VOC 2012 trainval",
        "source_url": "https://pjreddie.com/media/files/VOCtrainval_11-May-2012.tgz",
        "s3_prefix": f"s3://{BUCKET}/{PREFIX}/VOC2012/",
        "num_images": n_jpg,
        "num_annotations": n_xml,
        "num_classes": 20,
        "annotation_format": "PASCAL VOC XML",
        "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "uploaded_by": "upload_voc12.py",
    }
    key = f"{PREFIX}/manifest.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(manifest, indent=2).encode())
    print(f"manifest written to s3://{BUCKET}/{key}")
    print(json.dumps(manifest, indent=2))

    if n_jpg != n_xml:
        sys.exit("upload suspicious: image/annotation counts differ")
    print(f"UPLOAD OK: {n_jpg} images + {n_xml} annotations available at s3://{BUCKET}/{PREFIX}/")


if __name__ == "__main__":
    main()