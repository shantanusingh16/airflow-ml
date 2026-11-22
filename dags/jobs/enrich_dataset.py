"""Version the generated dataset into DeepLake with key-value metadata.

Inputs  (from generate_dataset):  data/<RUN_ID>/train.csv
Outputs: one DeepLake commit on s3://<bucket>/deeplake/feature_ds
         demo tensors: features (8-dim float32 rows — the default EMBEDDING_TENSOR),
         target (float32), run_id (text)
         kv metadata on ds.info: source_run, rows_added, updated_at, runs
         s3://<bucket>/data/<RUN_ID>/deeplake_commit.json  {commit, rows_added, info}

Other pipelines can commit their own numeric embedding tensors (any size/dtype)
to this dataset and point EMBEDDING_TENSOR at them; this job's `features`
tensor is what the default configuration indexes into Qdrant.

Reads env: RUN_ID, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION,
           DEEPLAKE_DATASET (s3:// path), AWS_* (DeepLake env chain)
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone

import boto3
import deeplake
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
    run_id = os.environ["RUN_ID"]
    bucket = os.environ["S3_BUCKET"]
    client = s3_client()

    df = pd.read_csv(io.BytesIO(client.get_object(Bucket=bucket, Key=f"data/{run_id}/train.csv")["Body"].read()))
    feature_cols = [c for c in df.columns if c != "target"]
    feats = df[feature_cols].values.astype(np.float32)
    targets = df["target"].values.astype(np.float32)
    n = int(len(df))

    path = os.environ["DEEPLAKE_DATASET"]
    creds = {
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY", "minioadmin"),
        "aws_region": os.environ.get("S3_REGION", "us-east-1"),
        "endpoint_url": os.environ["S3_ENDPOINT"],
    }
    if deeplake.exists(path, creds=creds):
        ds = deeplake.load(path, creds=creds)
    else:
        ds = deeplake.empty(path, creds=creds)
    for name, htype in (("features", "generic"), ("target", "generic"), ("run_id", "text")):
        if name not in ds:
            ds.create_tensor(name, htype=htype)
    # extend with numpy arrays (a list of Python floats trips NEP 50 casts in
    # deeplake 3.9.52's generic htype)
    ds["features"].extend(feats)
    ds["target"].extend(targets)
    ds["run_id"].extend([run_id] * n)

    # key-value atomic metadata (persisted with the commit)
    ds.info["source_run"] = run_id
    ds.info["rows_added"] = n
    ds.info["updated_at"] = datetime.now(timezone.utc).isoformat()
    runs = ds.info["runs"] if "runs" in ds.info else []
    runs.append(run_id)
    ds.info["runs"] = runs

    ds.flush()
    commit_id = ds.commit(message=f"enrich: {run_id}")
    info_snapshot = dict(ds.info)

    client.put_object(
        Bucket=bucket,
        Key=f"data/{run_id}/deeplake_commit.json",
        Body=json.dumps({"commit": commit_id, "rows_added": n, "info": info_snapshot}).encode(),
    )
    print(f"deeplake commit {commit_id} on {path}: +{n} rows (info={info_snapshot})")


if __name__ == "__main__":
    main()