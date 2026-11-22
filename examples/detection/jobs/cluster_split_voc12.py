"""Task 2 of 3 — kNN clustering of the DINOv2 embeddings + cluster-pure splits.

Runs in ml-jobrunner-gpu (scikit-learn is installed there).

Why cluster-pure splits: VOC contains near-duplicate images of the same
scene/scene-object (different frames). If one lands in train and its
near-twin in val/test, the model is "tested" on data it already saw —
silently inflated val/test scores. So we:

1. load the DINOv2 embeddings committed by task 1 (`dinov2_embedding`),
2. run **DBSCAN** — the standard kNN-based density clustering: a sample's
   neighborhood is its k nearest neighbours (k = min_samples), eps bounds
   the neighbourhood radius (cosine distance on DINOv2 embeddings),
   -> each connected group of near-identical images becomes one cluster;
3. re-assign DBSCAN *noise* points to their nearest cluster centroid
   (every sample ends up in exactly one cluster),
4. assign WHOLE clusters — never individual images — to train / val / test
   in the 70/10/20 ratio (largest-first deficit fill), and commit:

     cluster_id (int64), split3 (text: train|val|test),
     split (text: train|val  — the platform's 2-way convention, val = val3+test3,
             so the existing platform jobs keep working),
     KV: n_clusters, eps, min_samples, achieved split counts …

The commit id + achieved ratios are published to
`s3://<bucket>/data/<run_id>/voc12_cluster_manifest.json` and a
platform-compatible `voc12_split_manifest.json`.
"""
from __future__ import annotations

import json
import os
import sys
import time

import boto3
import deeplake
import numpy as np
from sklearn.cluster import DBSCAN

# --- env ---------------------------------------------------------------------
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
S3_ACCESS = os.environ["S3_ACCESS_KEY"]
S3_SECRET = os.environ["S3_SECRET_KEY"]
RUN_ID = os.environ["RUN_ID"]

VOC12_DATASET = os.environ.get("DEEPLAKE_VOC12", "s3://ml-artifacts/deeplake/voc12")
DBSCAN_EPS = float(os.environ.get("DBSCAN_EPS", "0.15"))
DBSCAN_MIN_SAMPLES = int(os.environ.get("DBSCAN_MIN_SAMPLES", "5"))
TARGET = {"train": 0.70, "val": 0.10, "test": 0.20}


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
    a = np.asarray(value)
    v = a.item() if a.size == 1 else a.reshape(-1)[0]
    if isinstance(v, bytes):
        v = v.decode("utf-8")
    return str(v)


def cluster(embeddings: np.ndarray) -> tuple[np.ndarray, int]:
    """DBSCAN (kNN density clustering) on cosine distance; noise points are
    reassigned to the nearest cluster centroid. Returns (cluster_ids, n_noise)."""
    e = embeddings.astype(np.float32)
    norms = np.linalg.norm(e, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    en = e / norms
    # precomputed cosine-distance matrix (n^2 * 4B ~= 130 MB for 5717 images)
    dist = np.clip(1.0 - (en @ en.T), 0.0, 2.0)
    np.fill_diagonal(dist, 0.0)
    labels = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES,
                    metric="precomputed").fit_predict(dist)
    if not (labels >= 0).any():          # degenerate: everything is noise
        # fine-grained fallback so the whole-cluster split assignment can
        # still hit 70/10/20 (20 balanced groups ~= 5/1/2 per split)
        print("warning: DBSCAN found no dense cluster (all noise) — "
              "falling back to KMeans(20) on normalized embeddings")
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=20, n_init=4, random_state=0).fit(en)
        labels = km.labels_.astype(np.int64)
        return labels, 0
    n_noise = int((labels == -1).sum())
    if n_noise:
        centroids = np.stack([e[labels == c].mean(axis=0) for c in np.unique(labels) if c >= 0])
        centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
        noise = labels == -1
        sims = e[noise] @ centroids.T
        labels[noise] = sims.argmax(axis=1)
    n_clusters = int(len(np.unique(labels)))
    if n_clusters < 10:   # too coarse to apportion 70/10/20 whole-cluster
        print(f"warning: only {n_clusters} clusters — too coarse for the "
              "70/10/20 assignment; falling back to KMeans(20)")
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=20, n_init=4, random_state=0).fit(en)
        labels = km.labels_.astype(np.int64)
        n_noise = 0
    return labels, n_noise

def assign_splits(labels: np.ndarray, sizes: list[int], target: dict) -> tuple[dict, dict]:
    """Largest-first: give each whole cluster to the split with the biggest
    remaining deficit. Returns ({cluster_id: split}, achieved_counts)."""
    total = int(sum(sizes))
    remaining = {k: v * total for k, v in target.items()}
    assignment, achieved = {}, {k: 0 for k in target}
    for cid, size in sorted(zip(labels_unique(labels), sizes), key=lambda p: -p[1]):
        split = max(remaining, key=lambda k: remaining[k])
        assignment[cid] = split
        remaining[split] -= size
        achieved[split] += size
    return assignment, achieved


def labels_unique(labels: np.ndarray) -> list[int]:
    return [int(c) for c in np.unique(labels) if c >= 0]


def main() -> None:
    s3 = s3_client()
    creds = dl_creds()

    embed_m = json.loads(s3.get_object(
        Bucket=S3_BUCKET, Key=f"data/{RUN_ID}/voc12_embed_manifest.json")["Body"].read())
    ds = deeplake.load(VOC12_DATASET, read_only=True, creds=creds)
    n = len(ds["image_id"])
    if "dinov2_embedding" not in set(ds.tensors):
        sys.exit("tensor 'dinov2_embedding' missing — run embed_voc12 first")

    embs = np.stack([ds["dinov2_embedding"][i].numpy().astype(np.float32) for i in range(n)])
    print(f"clustering {n} x {embs.shape[1]} DINOv2 embeddings "
          f"(DBSCAN eps={DBSCAN_EPS}, min_samples={DBSCAN_MIN_SAMPLES}) ...")
    t0 = time.time()
    labels, n_noise = cluster(embs)
    print(f"clustering done in {time.time() - t0:.1f}s: "
          f"{len(set(labels))} clusters, {n_noise} noise points reassigned")

    # whole-cluster -> split assignment at 70/10/20
    uniq = labels_unique(labels)
    sizes = [int((labels == c).sum()) for c in uniq]
    assignment, achieved = assign_splits(labels, sizes, TARGET)
    split3 = [""] * n
    for i in range(n):
        split3[i] = assignment[int(labels[i])]
    counts = {k: sum(1 for s in split3 if s == k) for k in TARGET}
    achieved_ratio = {k: v / n for k, v in counts.items()}
    print("split assignment (whole clusters, no image crosses splits):")
    for k in ("train", "val", "test"):
        print(f"  {k:5s}: {counts[k]:5d} images  ({achieved_ratio[k]:.1%} of {n}; target {TARGET[k]:.0%})")

    # --- commit ----------------------------------------------------------------
    ds_w = deeplake.load(VOC12_DATASET, read_only=False, creds=creds)
    names = set(ds_w.tensors)
    if "cluster_id" not in names:
        ds_w.create_tensor("cluster_id", htype="generic")
    if "split3" not in names:
        ds_w.create_tensor("split3", htype="text")
    if "split" not in names:
        ds_w.create_tensor("split", htype="text")

    ds_w["cluster_id"].extend(np.asarray(labels, dtype=np.int64))
    ds_w["split3"].extend(split3)
    # platform 2-way convention: val = val3 + test3 (existing jobs keep working)
    ds_w["split"].extend(["train" if s == "train" else "val" for s in split3])

    ds_w.info["n_clusters"] = int(len(uniq))
    ds_w.info["dbScan_eps"] = DBSCAN_EPS
    ds_w.info["dbScan_min_samples"] = DBSCAN_MIN_SAMPLES
    ds_w.info["n_noise_reassigned"] = int(n_noise)
    ds_w.info["train3_count"] = int(counts["train"])
    ds_w.info["val3_count"] = int(counts["val"])
    ds_w.info["test3_count"] = int(counts["test"])
    ds_w.info["split3_rule"] = "whole-DBSCAN-clusters assigned train/val/test 70/10/20 (leakage-free)"
    ds_w.info["clustered_by_run"] = RUN_ID
    commit_id = ds_w.commit(message=f"DBSCAN cluster-pure 70/10/20 splits (eps={DBSCAN_EPS}, k={DBSCAN_MIN_SAMPLES})")
    print(f"DeepLake commit {commit_id[:12]}: cluster_id + split3 + split")

    # --- manifests ---------------------------------------------------------------
    cluster_sizes = sorted(sizes, reverse=True)
    cluster_m = {
        "run_id": RUN_ID,
        "dataset": VOC12_DATASET,
        "commit_id": commit_id,
        "deeplake_ref": f"{VOC12_DATASET}@{commit_id}",
        "total": n,
        "n_clusters": len(uniq),
        "n_noise_reassigned": n_noise,
        "dbScan_eps": DBSCAN_EPS,
        "dbScan_min_samples": DBSCAN_MIN_SAMPLES,
        "split_counts": counts,
        "split_ratios": {k: round(v, 4) for k, v in achieved_ratio.items()},
        "target_ratios": TARGET,
        "cluster_size_hist_top": cluster_sizes[:20],
        "largest_cluster": cluster_sizes[0] if cluster_sizes else 0,
        "info": dict(ds_w.info),
    }
    ckey = f"data/{RUN_ID}/voc12_cluster_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=ckey, Body=json.dumps(cluster_m, indent=2).encode())

    # platform-compatible 2-way manifest (val = val3 + test3)
    split_m = {
        "run_id": RUN_ID,
        "dataset": VOC12_DATASET,
        "commit_id": commit_id,
        "deeplake_ref": f"{VOC12_DATASET}@{commit_id}",
        "total": n,
        "train_count": counts["train"],
        "val_count": counts["val"] + counts["test"],
        "test_count": counts["test"],
        "val_ratio": (counts["val"] + counts["test"]) / n,
        "split_rule": "cluster-pure (DBSCAN) 3-way split; 2-way view: val = val3+test3",
        "info": dict(ds_w.info),
    }
    skey = f"data/{RUN_ID}/voc12_split_manifest.json"
    s3.put_object(Bucket=S3_BUCKET, Key=skey, Body=json.dumps(split_m, indent=2).encode())
    print(f"CLUSTER OK: {len(uniq)} clusters -> train/val/test = {counts['train']}/{counts['val']}/{counts['test']}; "
          f"manifests {ckey} + {skey}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"cluster_split_voc12 finished in {time.time() - t0:.1f}s")