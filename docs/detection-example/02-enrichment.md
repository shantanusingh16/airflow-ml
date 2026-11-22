# Stage 2 — Enrichment: raw MinIO data → versioned DeepLake dataset

> **You are at stage 2 of 7.** Outcome: the VOC2012 annotations are parsed and
> committed to the DeepLake dataset `s3://ml-artifacts/deeplake/voc12` — one
> versioned, queryable dataset instead of thousands of XML files. Every later
> stage (sampling, training, evaluation) reads *this*, pinned by commit id.

## 2.1 DeepLake on this platform — 60-second mental model

- **Storage:** DeepLake is a *library*, not a service here. Datasets are
  directories inside your MinIO bucket: `ml-artifacts/deeplake/<name>/`. No
  DeepLake server, no account, no token — your MinIO credentials are the
  access. (If you used DeepLake's hosted cloud you'd set `HF_TOKEN`; you
  don't, so don't.)
- **Dataset = tensors + KV metadata.** A tensor is a versioned column
  (`image_id`, `bboxes`, …) that can hold scalars, fixed-size arrays, or
  ragged per-sample arrays (each row may have a different shape — that's how
  `bboxes` holds a different number of boxes per image).
- **Version = commit.** `ds.commit(message=…)` produces a commit id; the
  dataset "head" is the newest commit. You can load any past version:
  `deeplake.load(f"{path}@{commit_id}")`. Re-running the pipeline creates a
  new commit (this example rebuilds the dataset from raw S3 each run — same
  convention as the platform's `feature_ds`), so nothing is ever lost.
- **`ds.info`** is the flat key-value metadata store — **atomic values only**
  (str / int / float / bool). That's your "dataset card": what it is, where
  it came from, how big, who/when built it.
- **Where you go:** there is no DeepLake web UI in this stack. You verify via
  (a) the job logs in the [Airflow UI](04-custom-jobs-and-dags.md#5-checking-run-status-and-logs),
  (b) the MinIO console (<http://localhost:9001>, bucket `ml-artifacts` →
  `deeplake/`), and (c) a 10-line Python probe below.

## 2.2 What the enrichment job does

`examples/detection/jobs/ingest_voc12.py` (runs in the CPU job image — pure
S3 reads + XML parsing, no GPU needed):

1. Lists `datasets/voc12/VOC2012/Annotations/*.xml` on MinIO and downloads
   each (they're a few KB each; the 1.2 GB of JPEGs are **never** downloaded
   at this stage).
2. Parses each PASCAL XML: image id, `<size>` (width/height), and every
   `<object>` → (class id from the fixed 20-class list, `[x1,y1,x2,y2]` box).
3. Creates a **fresh** dataset `s3://ml-artifacts/deeplake/voc12` and fills
   these tensors:

| Tensor | htype | Per sample | Notes |
|--------|-------|-----------|-------|
| `image_id` | `text` | e.g. `"000005"` | joins to the raw JPEG on S3 |
| `image_uri` | `text` | `s3://ml-artifacts/datasets/voc12/VOC2012/JPEGImages/000005.jpg` | the training job streams JPEGs from here — DeepLake itself stays tiny |
| `class_ids` | `generic` (int64, ragged) | `[3, 14, 14]` | box count varies per image |
| `bboxes` | `generic` (float32, ragged `(N,4)`) | pixel coords `x1 y1 x2 y2` | same `N` as `class_ids` |
| `width` / `height` | `generic` (int64) | image size px | from the XML `<size>` — no image download needed |
| `class_names` | `text` | one row per class (20 rows) | downstream jobs read names from the dataset instead of hardcoding |

4. Writes flat KV metadata to `ds.info`:

```
dataset_kind      = "detection"
source            = "PASCAL VOC 2012 trainval"
source_s3_prefix  = "s3://ml-artifacts/datasets/voc12/VOC2012/"
num_classes       = 20
num_images        = 5717
num_boxes         = 15296
ingested_at       = "2026-08-26T...Z"
ingested_by_run   = "<run_id>"
```

5. `commit(message="ingest VOC2012 from s3://...")` → **commit id** (the
   version).
6. Publishes `s3://ml-artifacts/data/<run_id>/voc12_ingest_manifest.json`
   containing the commit id, row/box counts, tensor list, and the `ds.info`
   dump — the artifact downstream tasks (and you) consume.

## 2.3 How to run it

**As part of the pipeline** (the normal path): activate the DAG
([04-custom-jobs-and-dags.md](04-custom-jobs-and-dags.md#3-creating-a-dag))
and trigger `detection_voc12` — `ingest_voc12` is its first task.

**Standalone** (iterate on the job without a full run):

```bash
docker run --rm --network airflow-ml-net \
    -e RUN_ID=manual-$(date +%s) -e S3_ENDPOINT=http://minio:9000 \
    -e S3_BUCKET=ml-artifacts -e S3_ACCESS_KEY=minioadmin -e S3_SECRET_KEY=minioadmin \
    -e VOC_S3_PREFIX=datasets/voc12/VOC2012 \
    -e DEEPLAKE_VOC12=s3://ml-artifacts/deeplake/voc12 \
    -v "$PWD/dags:/opt/airflow/dags:ro" \
    ml-jobrunner:latest python /runner.py /opt/airflow/dags/jobs/ingest_voc12.py
```

(`job_task()` in a DAG does exactly this for you — same image, same network,
same env block from `dags/jobtask.py`.)

Expected tail of the log:

```
found 5717 annotation files under s3://ml-artifacts/datasets/voc12/VOC2012/Annotations/
DeepLake commit a1b2c3d4e5f6... tensors: ['class_names', 'image_id', 'image_uri', 'class_ids', 'bboxes', 'width', 'height']
manifest published: s3://ml-artifacts/data/<run_id>/voc12_ingest_manifest.json
INGEST OK: 5717 images, 15296 boxes -> s3://ml-artifacts/deeplake/voc12 (commit a1b2c3d4e5f6)
```

## 2.4 How you know it worked

1. **Log** — `INGEST OK: …` line above (the job `sys.exit`s with a message on
   any failure, which turns the Airflow task red).
2. **Probe the dataset** (job image; swap `minio:9000`↔`localhost:9000` for
   host vs container):

```python
import deeplake
creds = dict(aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin",
             aws_region="us-east-1", endpoint_url="http://minio:9000")
ds = deeplake.load("s3://ml-artifacts/deeplake/voc12", read_only=True, creds=creds)
print("rows:", len(ds), "| tensors:", list(ds.tensors))
print("head commit:", ds.commit_id[:12])
print("history:", [(c["commit"][:8], c["message"]) for c in ds.commits])   # newest first
print("kv metadata:", dict(ds.info))
print("sample:", ds["image_id"][0].numpy(), "| boxes:", ds["bboxes"][0].numpy().shape)
```

3. **MinIO console** — <http://localhost:9001> → `ml-artifacts/deeplake/voc12/`
   shows the on-disk layout (chunked tensor data + `meta/` files).

## 2.5 Listing what's in DeepLake (available datasets + metadata)

DeepLake-on-S3 has no catalog service, so "which datasets exist" = **list the
`deeplake/` prefix**; everything else (commits, KV metadata, sizes) is read
per dataset:

```python
import boto3, deeplake, json
s3 = boto3.client("s3", endpoint_url="http://minio:9000",
                  aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin")
r = s3.list_objects_v2(Bucket="ml-artifacts", Prefix="deeplake/", Delimiter="/")
datasets = [p.rstrip("/").rsplit("/", 1)[-1] for p in r.get("CommonPrefixes", [])]
print("DeepLake datasets:", datasets)      # e.g. ['feature_ds', 'voc12']

for name in datasets:
    ds = deeplake.load(f"s3://ml-artifacts/deeplake/{name}", read_only=True, creds=creds)
    print(f"\n== {name}: {len(ds)} rows | head {ds.commit_id[:12]}")
    print("   commits:", [(c["commit"][:8], c["message"]) for c in ds.commits][:3])
    print("   info:", {k: v for k, v in dict(ds.info).items()})   # flat atomic KV
```

That's the full "what's available, with upload data + metadata as flat KV
tuples" answer on the DeepLake side; the raw-S3 side is
[01-ingestion.md §1.6](01-ingestion.md#16-which-datasets-are-already-uploaded-and-their-metadata).

## 2.6 Writing your own enrichment job

The whole pattern (any dataset, any target) is four steps — see the full
contract in [05-data-access.md](05-data-access.md):

```python
import os, deeplake
creds = dict(aws_access_key_id=os.environ["S3_ACCESS_KEY"],
             aws_secret_access_key=os.environ["S3_SECRET_KEY"],
             aws_region=os.environ.get("S3_REGION", "us-east-1"),
             endpoint_url=os.environ["S3_ENDPOINT"])

ds = deeplake.empty(os.environ.get("MY_DATASET", "s3://ml-artifacts/deeplake/my_ds"),
                    creds=creds)                 # or deeplake.load(path, read_only=False, creds=…)
ds.create_tensor("caption", htype="text")        # text | generic (any numpy shape, ragged ok)
ds.create_tensor("embedding", htype="generic")   # numeric tensor of any size → indexable in Qdrant
ds["caption"].extend(["a cat on a mat", ...])
ds["embedding"].extend([np.float32([...]), ...])
ds.info["source"] = "..."                        # flat atomic KV only
ds.info["num_rows"] = len(ds)
commit = ds.commit(message="enrich my dataset")  # <-- the version id you'll pin later
print("commit", commit)
```

Rules of thumb from this platform's jobs:
- **Reference big binaries, don't copy them** (`image_uri` string → raw S3
  object) unless the tensor genuinely needs the bytes.
- `htype="generic"` accepts any numpy dtype/shape per row (ragged rows OK) —
  it's the safe default for detection boxes, point clouds, token ids, …
- One **commit** per meaningful transformation; put the commit id in the
  run's S3 manifest so the next stage pins it exactly.

**Next:** [Stage 3 — Sampling](03-sampling.md): turn the enriched head into a
deterministic train/val split, again as a new commit.