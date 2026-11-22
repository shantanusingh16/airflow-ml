"""Mirror the current DeepLake head's embedding tensor into Qdrant.

Embeddings are pipeline-generated: the tensor to index is EMBEDDING_TENSOR
(default `features`), its vector size is discovered from the first sample
(uniform size required across all samples), and its dtype is cast to float32
(Qdrant's only vector dtype; non-numeric tensors are rejected). The match
type is QDRANT_DISTANCE: cosine | euclidean | dot | manhattan — Qdrant's
complete set of built-in metrics (no custom distance functions exist in
qdrant/qdrant).

The collection is rebuilt from scratch on every run so it always mirrors the
latest head; DeepLake remains the source of truth.

Reads env: RUN_ID, DEEPLAKE_DATASET, EMBEDDING_TENSOR, QDRANT_URL,
           QDRANT_COLLECTION, QDRANT_DISTANCE,
           S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, S3_ENDPOINT
"""

from __future__ import annotations

import os
import time
import uuid

import deeplake
import numpy as np
from qdrant_client import QdrantClient, models as qm

# QDRANT_DISTANCE value -> qdrant-client Distance member (complete set)
DISTANCE_MAP = {
    "cosine": qm.Distance.COSINE,
    "euclidean": qm.Distance.EUCLID,
    "dot": qm.Distance.DOT,
    "manhattan": qm.Distance.MANHATTAN,
}


def wait_ready(client: QdrantClient, url: str, tries: int = 12, delay: float = 5.0) -> None:
    for _ in range(tries):
        try:
            client.get_collections()
            return
        except Exception:
            time.sleep(delay)
    raise RuntimeError(f"qdrant at {url} not ready after {tries * delay}s")


def main() -> None:
    run_id = os.environ["RUN_ID"]
    url = os.environ["QDRANT_URL"]
    col = os.environ["QDRANT_COLLECTION"]
    tensor = os.environ["EMBEDDING_TENSOR"]
    distance = os.environ.get("QDRANT_DISTANCE", "cosine").lower()
    if distance not in DISTANCE_MAP:
        raise RuntimeError(f"QDRANT_DISTANCE={distance!r} not supported; use one of {sorted(DISTANCE_MAP)}")
    path = os.environ["DEEPLAKE_DATASET"]
    creds = {
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY", "minioadmin"),
        "aws_region": os.environ.get("S3_REGION", "us-east-1"),
        "endpoint_url": os.environ["S3_ENDPOINT"],
    }

    ds = deeplake.load(path, read_only=True, creds=creds)
    if tensor not in ds:
        raise RuntimeError(f"EMBEDDING_TENSOR {tensor!r} not found in {path} — producing pipeline has not run")
    n = ds.num_samples
    if n == 0:
        raise RuntimeError(f"deeplake head {path} is empty — enrich (producing) job has not run")
    raw = [ds[tensor][i] for i in range(n)]
    vecs = []
    dim = None
    for i, sample in enumerate(raw):
        arr = np.asarray(sample, dtype=np.float32)  # raises on non-numeric samples
        if dim is None:
            dim = int(len(arr))
        elif len(arr) != dim:
            raise RuntimeError(
                f"ragged embeddings in {tensor!r}: sample {i} has {len(arr)} dims, first sample has {dim} — "
                "Qdrant collections require a uniform vector size"
            )
        vecs.append(arr)

    client = QdrantClient(url=url)
    wait_ready(client, url)
    if client.collection_exists(col):
        client.delete_collection(col)
    client.create_collection(col, vectors_config=qm.VectorParams(size=dim, distance=DISTANCE_MAP[distance]))

    ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{i}")) for i in range(n)]
    chunk = 500
    for i in range(0, n, chunk):
        client.upsert(col, points=[qm.PointStruct(id=ids[j], vector=vecs[j].tolist()) for j in range(i, min(i + chunk, n))])

    count = client.count(col, exact=True).count
    if count != n:
        raise RuntimeError(f"qdrant count {count} != {n} for collection {col}")
    print(f"indexed {n} vectors (tensor={tensor}, dim={dim}, distance={distance}) into {url}/{col} for run {run_id}")


if __name__ == "__main__":
    main()