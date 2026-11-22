"""kNN retrieval over the Qdrant collection.

Queries are the first N_QUERIES samples of the EMBEDDING_TENSOR from the
current DeepLake head (deterministic, dataset-agnostic). Publishes
s3://<bucket>/analysis/<RUN_ID>/vector_search.json (queries + top-K neighbour
ids/scores) — the custom data-analysis artifact.

Reads env: RUN_ID, DEEPLAKE_DATASET, EMBEDDING_TENSOR, QDRANT_URL,
           QDRANT_COLLECTION, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, S3_ENDPOINT
"""

from __future__ import annotations

import json
import os

import deeplake
import numpy as np
from qdrant_client import QdrantClient

K = 10
N_QUERIES = 5


def s3_client():
    import boto3
    from botocore.config import Config

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
    url = os.environ["QDRANT_URL"]
    col = os.environ["QDRANT_COLLECTION"]
    tensor = os.environ["EMBEDDING_TENSOR"]
    path = os.environ["DEEPLAKE_DATASET"]
    client = s3_client()

    creds = {
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY", "minioadmin"),
        "aws_region": os.environ.get("S3_REGION", "us-east-1"),
        "endpoint_url": os.environ["S3_ENDPOINT"],
    }
    ds = deeplake.load(path, read_only=True, creds=creds)
    if tensor not in ds or ds.num_samples == 0:
        raise RuntimeError(f"embedding tensor {tensor!r} missing/empty in {path}")
    queries = [ds[tensor][i].numpy().astype(np.float32).tolist() for i in range(min(N_QUERIES, ds.num_samples))]

    qclient = QdrantClient(url=url)
    qclient.get_collections()  # raises if qdrant is down; runs after index_embeddings
    if not qclient.collection_exists(col):
        raise RuntimeError(f"collection {col} missing at {url} — index_embeddings failed?")

    results = []
    for i in range(len(queries)):
        res = qclient.query_points(collection_name=col, query=queries[i], limit=K)
        results.append(
            {"query_index": i, "neighbors": [{"id": p.id, "score": round(float(p.score), 6)} for p in res.points]}
        )
        top1 = results[-1]["neighbors"][0] if results[-1]["neighbors"] else None
        print(f"query {i} -> top1 {top1['id']} (score={top1['score']})" if top1 else f"query {i} -> no results")

    client.put_object(
        Bucket=bucket,
        Key=f"analysis/{run_id}/vector_search.json",
        Body=json.dumps(
            {"run_id": run_id, "collection": col, "embedding_tensor": tensor, "k": K, "queries": results}
        ).encode(),
    )
    print(f"vector search results published: s3://{bucket}/analysis/{run_id}/vector_search.json")


if __name__ == "__main__":
    main()