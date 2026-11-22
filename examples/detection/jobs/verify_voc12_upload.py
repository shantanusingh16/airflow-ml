"""Stage 0 — verify the VOC2012 upload landed in MinIO before the DAG proceeds.

Lists ``s3://<bucket>/<VOC_S3_PREFIX>`` and fails unless:
  * JPEGImages/ has >= MIN_IMAGES JPEGs,
  * Annotations/ has the same count of XMLs,
  * ImageSets/Main/trainval.txt exists and lists exactly that many images.

This catches a partial/truncated upload (the dataset was staged through
/tmp on the host and streamed in) before we spend GPU time on it.
"""
from __future__ import annotations

import os
import sys

import boto3

S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
PREFIX = os.environ.get("VOC_S3_PREFIX", "datasets/voc12/VOC2012")
MIN_IMAGES = int(os.environ.get("MIN_IMAGES", "5000"))

client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    region_name=S3_REGION,
)


def list_keys(prefix: str) -> list[str]:
    keys = []
    token = None
    while True:
        kw = {"Bucket": S3_BUCKET, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        r = client.list_objects_v2(**kw)
        keys += [o["Key"] for o in r.get("Contents", [])]
        if not r.get("IsTruncated"):
            break
        token = r["NextContinuationToken"]
    return keys


def main() -> None:
    keys = list_keys(f"{PREFIX}/")
    jpegs = sorted(k for k in keys if k.endswith((".jpg", ".jpeg")))
    xmls = sorted(k for k in keys if k.endswith(".xml"))
    print(f"{PREFIX}/: {len(keys)} objects, {len(jpegs)} JPEGs, {len(xmls)} XMLs")
    if len(jpegs) < MIN_IMAGES:
        sys.exit(f"FAIL: only {len(jpegs)} JPEGs uploaded (expected >={MIN_IMAGES}) — partial upload?")
    if len(xmls) != len(jpegs):
        sys.exit(f"FAIL: {len(jpegs)} JPEGs vs {len(xmls)} XMLs — annotation/image mismatch")

    tv = f"{PREFIX}/ImageSets/Main/trainval.txt"
    body = client.get_object(Bucket=S3_BUCKET, Key=tv)["Body"].read().decode()
    listed = [ln.strip() for ln in body.splitlines() if ln.strip()]
    print(f"trainval.txt: {len(listed)} image refs")
    if len(listed) != len(jpegs):
        sys.exit(f"FAIL: trainval.txt lists {len(listed)} but JPEGImages has {len(jpegs)}")
    print(f"UPLOAD OK: {len(jpegs)} images + {len(xmls)} annotations verified in s3://{S3_BUCKET}/{PREFIX}/")


if __name__ == "__main__":
    main()