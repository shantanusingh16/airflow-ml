# Accessing the stores from a job (MinIO · DeepLake · Qdrant)

> **Reference for every stage.** Copy-paste blocks that work verbatim inside
> any `job_task()`/`gpu_job_task()` container. Host-side variants (for
> scripts you run from your terminal) are noted per section.

## MinIO / S3 from a job

The job env gives you everything ([04 §2](04-custom-jobs-and-dags.md#2-the-job-contract-env-vars-given-to-every-job)):

```python
import boto3, os
s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["S3_ENDPOINT"],          # http://minio:9000 in-container
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],   # minioadmin
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name=os.environ.get("S3_REGION", "us-east-1"),
)
BUCKET = os.environ["S3_BUCKET"]                     # ml-artifacts

# read
body = s3.get_object(Bucket=BUCKET, Key="datasets/voc12/manifest.json")["Body"].read()
# write / publish
s3.put_object(Bucket=BUCKET, Key=f"data/{os.environ['RUN_ID']}/out.json",
              Body=json.dumps(out).encode())
# bulk download
s3.download_file(BUCKET, "datasets/voc12/VOC2012/JPEGImages/000005.jpg", "/tmp/000005.jpg")
# list what's available (raw datasets)
r = s3.list_objects_v2(Bucket=BUCKET, Prefix="datasets/", Delimiter="/")
print([p.rstrip("/").split("/")[-1] for p in r.get("CommonPrefixes", [])])
```

**Host-side** (terminal scripts): identical code with
`endpoint_url="http://localhost:9000"` — or `aws s3 --endpoint-url
http://localhost:9000 ls s3://ml-artifacts/datasets/` (aws-cli with
`aws configure set aws_access_key_id minioadmin` etc.), or `mc`
([01-ingestion.md §1.4](01-ingestion.md#14-upload-to-minio--three-ways-pick-one)).

The platform also exposes an Airflow-side helper: `s3_hook()` in
`dags/jobtask.py` (S3Hook over the `aws_default` connection) for
**Airflow-context** code (your DAG files, `PythonOperator` tasks) — jobs
themselves always use raw boto3 so they stay orchestrator-agnostic.

## DeepLake from a job

Access = the `AWS_*` env chain **plus** an explicit creds dict (jobs pass
both — belt and braces for MinIO):

```python
import os, deeplake
import numpy as np

creds = {
    "aws_access_key_id": os.environ["S3_ACCESS_KEY"],
    "aws_secret_access_key": os.environ["S3_SECRET_KEY"],
    "aws_region": os.environ.get("S3_REGION", "us-east-1"),
    "endpoint_url": os.environ["S3_ENDPOINT"],      # http://minio:9000 in-container
}

# which datasets exist (no catalog service → list the S3 prefix)
import boto3
s3 = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT"],
                  aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                  aws_secret_access_key=os.environ["S3_SECRET_KEY"])
r = s3.list_objects_v2(Bucket=os.environ["S3_BUCKET"], Prefix="deeplake/", Delimiter="/")
datasets = [p.rstrip("/").rsplit("/", 1)[-1] for p in r.get("CommonPrefixes", [])]
# -> e.g. ['feature_ds', 'voc12']

# create (fresh, idempotent-per-run) / open
ds = deeplake.empty("s3://ml-artifacts/deeplake/my_ds", creds=creds)
ds = deeplake.load("s3://ml-artifacts/deeplake/voc12", read_only=True, creds=creds)

# read tensors
n = len(ds)
row = ds["bboxes"][0].numpy()            # (N,4) float32 — per-sample shape preserved
text = ds["image_id"][0].numpy()         # bytes/str — decode defensively

# flat atomic KV metadata
print(dict(ds.info))                      # {…: str/int/float/bool only}

# versions: history + pinning
for c in ds.commits:                     # newest first
    print(c["commit"], c["time"], c["author"], c["message"])
old = deeplake.load("s3://ml-artifacts/deeplake/voc12@" + ds.commits[1]["commit"],
                    read_only=True, creds=creds)

# write + commit (a new version)
ds = deeplake.load("s3://ml-artifacts/deeplake/my_ds", read_only=False, creds=creds)
ds.create_tensor("embedding", htype="generic")    # any numeric shape, ragged rows OK
ds.create_tensor("label",   htype="text")
ds["embedding"].extend([np.float32([1, 2, 3]), np.float32([4, 5])])
ds["label"].extend(["a", "b"])
ds.info["source"] = "my_job"              # atomic values only
ds.info["n_rows"] = len(ds)
commit_id = ds.commit(message="my transformation")
```

API notes that bite in practice (all verified against `deeplake==3.9.52`):

- **No `version=` kwarg** — versioning is the `path@commit_id` suffix.
- **`ds.commits`** (list of dicts), not `ds.history`; `ds.commit_id` = head.
- **`ds.commit(message=…)`** returns the new commit id; `ds.flush()` exists,
  `ds.close()` does not in this line of releases.
- **`ds.info`** values must be atomic (str/int/float/bool); lists of scalars
  go in a tensor (e.g. `class_names`), not in `info`.
- **`ds.tensors`** is the name list; check membership before
  `create_tensor` (re-creating raises).
- htype choice: `text` for strings, `generic` for anything numeric (any
  dtype, ragged per-row shape), `image`/`jpeg` if you really want pixels in
  the dataset, `link` for external-URI samples.

Host-side: same code, `endpoint_url="http://localhost:9000"` and
`aws_access_key_id="minioadmin"`, run it with any image that has `deeplake`
(e.g. `docker run --rm --network airflow-ml-net -e AWS_… ml-jobrunner:latest
python /host/probe.py`).

## Qdrant from a job

Qdrant **has no credentials** in this stack (internal network). From a job:

```python
import os
from qdrant_client import QdrantClient, models
q = QdrantClient(url=os.environ["QDRANT_URL"])        # http://qdrant:6333

# what's there
print([c.name for c in q.get_collections()])

# platform convention (see index_embeddings.py): a pipeline may own its
# collection; vector size is DISCOVERED from the data, distance from env
DIST = {  # the complete set Qdrant core supports — no custom distances exist
    "cosine": models.Distance.COSINE, "euclid": models.Distance.EUCLID,
    "dot": models.Distance.DOT, "manhattan": models.Distance.MANHATTAN,
}[os.environ.get("QDRANT_DISTANCE", "cosine").lower()]
name = os.environ.get("QDRANT_COLLECTION", "feature_vectors")
q.delete_collection(name) if q.collection_exists(name) else None
vec = some_sample_from_deeplake.astype("float32")       # size N discovered here
q.create_collection(name, vectors_config=models.VectorParams(size=len(vec), distance=DIST))
q.upsert(name, points=[models.PointStruct(id=i, vector=v) for i, v in enumerate(vectors)])
print(q.count(name, exact=True).count)

# search
hits = q.query_points(name, query=vec, limit=10).points
for p in hits:
    print(p.id, p.score)
```

The platform's own pipeline uses exactly this pattern in
`dags/jobs/index_embeddings.py`: it reads the tensor named by
`EMBEDDING_TENSOR` (default `features`) from the DeepLake head, rebuilds the
collection `feature_vectors` from scratch each run (DeepLake is the source
of truth), and rejects ragged/non-numeric tensors at index time. Your
detection example doesn't need Qdrant — but if you add e.g. CLIP image
embeddings to your DeepLake dataset as a `generic` tensor, you can point
`EMBEDDING_TENSOR` at it (per-DAG env) or create your own collection as
above (e.g. `voc12_clip` with `distance=COSINE`).

**Host-side / human:** Qdrant REST API at <http://localhost:6333>
(`curl http://localhost:6333/collections`), the interactive dashboard at
<http://localhost:6333/dashboard>, or gRPC on `localhost:6334`.

## Where each store fits (cheat sheet)

| You want to… | Use |
|--------------|-----|
| store raw files (images, tarballs, model weights) | MinIO `ml-artifacts/datasets/…`, `models/<run_id>/…` |
| version structured, queryable data (tables, boxes, embeddings) | DeepLake dataset on `s3://ml-artifacts/deeplake/<name>` |
| attach "dataset card" facts (source, counts, timestamps) | `ds.info` (flat atomic KV) + `data/<run_id>/*.json` manifests on S3 |
| pin exactly which data a model used | the commit id in the stage's manifest; `deeplake.load(f"{path}@{commit}")` |
| nearest-neighbour over pipeline-generated vectors | Qdrant (any `generic` numeric tensor can be the source) |
| per-run traceability across all of the above | `RUN_ID` env + `data/<run_id>/` manifest convention |

**Next:** [Stage 4 — training a detection model with CUDA](06-training-cuda.md).