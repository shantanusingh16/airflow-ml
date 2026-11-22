"""Stage 1 of voc12_demo — upload the local VOC2012 tree to MinIO.

The ``voc12_demo`` DAG binds the local VOC2012 tree read-only into the job
container at ``/datasets/voc2012`` (staging re-exports the host tree via the
factory shim; on other hosts the operator points ``VOC_DATASET_HOST_DIR`` at
the real host path). This job copies the annotated JPEG+XML pairs from it to
``s3://<bucket>/<VOC_S3_PREFIX>/`` and writes
``ImageSets/Main/trainval.txt`` listing exactly the uploaded ids, so the
verify/ingest stages run against whatever actually landed in MinIO.

Dataset rule: an image counts iff ``Annotations/<id>.xml`` exists (the
staging tree has no ``trainval.txt`` of its own). Order is deterministic:
ids sorted; ``SAMPLE=N`` (N > 0) takes the first N ids, ``SAMPLE=0``/unset
takes all annotated pairs.

Idempotent: every object is HEADed first and an object that already exists
with the same byte size is skipped, so re-runs (and parallel demo runs on a
shared bucket) do not re-upload unchanged files.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# --- config (all env-driven; job_task() injects the S3_* + platform vars) ----
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]

# s3:// prefix (no bucket) of the uploaded VOC tree (same as verify/ingest)
VOC_S3_PREFIX = os.environ.get("VOC_S3_PREFIX", "datasets/voc12/VOC2012")
# in-container path of the read-only dataset bind mount (never the host path
# — the DAG mount's source is resolved by the daemon/shim, not by this job)
DATASET_DIR = Path(os.environ.get("VOC_DATASET_DIR", "/datasets/voc2012"))
# >0: first N ids in sorted order; 0/unset: all annotated pairs
SAMPLE = int(os.environ.get("SAMPLE", "0"))


def s3_client() -> "boto3.client":
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=S3_REGION,
    )


def put_or_skip(s3, local: Path, key: str, stats: list) -> None:
    """Upload ``local`` to ``key`` unless the object already exists with the
    same byte size (stats = [uploaded, skipped])."""
    want = local.stat().st_size
    try:
        head = s3.head_object(Bucket=S3_BUCKET, Key=key)
        if int(head["ContentLength"]) == want:
            stats[1] += 1
            return
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey"):
            raise
    s3.upload_file(str(local), S3_BUCKET, key)
    stats[0] += 1


def main() -> None:
    s3 = s3_client()
    ann_dir = DATASET_DIR / "Annotations"
    img_dir = DATASET_DIR / "JPEGImages"
    if not ann_dir.is_dir() or not img_dir.is_dir():
        sys.exit(
            f"dataset not mounted: {DATASET_DIR} (expected Annotations/ + JPEGImages/) — "
            "the voc12_demo DAG bind-mounts the VOC2012 tree read-only at "
            "/datasets/voc2012; on other hosts set VOC_DATASET_HOST_DIR to the "
            "host path of the tree"
        )

    # only annotated pairs count: id = XML stem, deterministic sorted order
    ids = sorted(p.stem for p in ann_dir.glob("*.xml"))
    if not ids:
        sys.exit(f"no .xml annotations under {ann_dir} — nothing to upload")
    if SAMPLE > 0:
        if SAMPLE >= len(ids):
            print(f"note: SAMPLE={SAMPLE} >= {len(ids)} annotated pairs — uploading all")
        else:
            print(f"SAMPLE={SAMPLE}: first {SAMPLE} of {len(ids)} annotated pairs (sorted ids)")
        ids = ids[:SAMPLE]

    # fail before a partial upload: every selected id needs its JPEG
    missing = [i for i in ids if not (img_dir / f"{i}.jpg").exists()]
    if missing:
        sys.exit(f"{len(missing)} selected ids have no JPEG in {img_dir}, e.g. {missing[:5]}"
                 " — incomplete dataset tree?")

    stats_jpg = [0, 0]   # [uploaded, skipped]
    stats_xml = [0, 0]
    for i in ids:
        put_or_skip(s3, img_dir / f"{i}.jpg", f"{VOC_S3_PREFIX}/JPEGImages/{i}.jpg", stats_jpg)
        put_or_skip(s3, ann_dir / f"{i}.xml", f"{VOC_S3_PREFIX}/Annotations/{i}.xml", stats_xml)

    # trainval.txt lists exactly the uploaded ids (verify_upload cross-checks
    # its line count against the JPEG count under the prefix)
    tv_key = f"{VOC_S3_PREFIX}/ImageSets/Main/trainval.txt"
    s3.put_object(Bucket=S3_BUCKET, Key=tv_key, Body=("\n".join(ids) + "\n").encode())
    print(f"trainval.txt written: s3://{S3_BUCKET}/{tv_key} ({len(ids)} ids)")

    print(f"UPLOAD OK: {len(ids)} pairs -> s3://{S3_BUCKET}/{VOC_S3_PREFIX}/ "
          f"(JPEG {stats_jpg[0]} uploaded / {stats_jpg[1]} skipped, "
          f"XML {stats_xml[0]} uploaded / {stats_xml[1]} skipped)")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"upload_voc12 finished in {time.time() - t0:.1f}s")
