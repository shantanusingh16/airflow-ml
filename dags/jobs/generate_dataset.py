"""Generate a synthetic regression dataset and publish it to S3 (MinIO).

Publishes, under ``data/<RUN_ID>/``:
    train.csv, test.csv  - 80/20 split
    manifest.json        - shape/split metadata

Reads env: RUN_ID, S3_ENDPOINT, S3_BUCKET, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY
"""

from __future__ import annotations

import io
import json
import os

import boto3
import numpy as np
import pandas as pd
from botocore.config import Config


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minioadmin"),
        config=Config(s3={"addressing_style": "path"}),
        verify=False,
    )


def main() -> None:
    run_id = os.environ.get("RUN_ID", "dev")
    client = s3_client()
    bucket = os.environ["S3_BUCKET"]

    rng = np.random.default_rng(42)
    n = 5_000
    n_features = 8
    X = rng.normal(size=(n, n_features))
    w = rng.normal(size=n_features)
    y = X @ w + 0.5 * rng.normal(size=n)

    df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(n_features)])
    df["target"] = y

    split = int(n * 0.8)
    train, test = df.iloc[:split], df.iloc[split:]

    for name, part in (("train.csv", train), ("test.csv", test)):
        buf = io.BytesIO()
        part.to_csv(buf, index=False)
        buf.seek(0)  # upload_fileobj reads from the current position
        client.upload_fileobj(buf, bucket, f"data/{run_id}/{name}")

    manifest = {
        "n_rows": n,
        "n_features": n_features,
        "split": {"train": int(len(train)), "test": int(len(test))},
    }
    client.put_object(
        Bucket=bucket,
        Key=f"data/{run_id}/manifest.json",
        Body=json.dumps(manifest).encode(),
    )
    print(f"dataset published: s3://{bucket}/data/{run_id}/ (train={len(train)}, test={len(test)})")


if __name__ == "__main__":
    main()