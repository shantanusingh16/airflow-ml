# Stage 1 — Ingestion: getting a public detection dataset onto the platform

> **You are at stage 1 of 7.** Outcome: the raw dataset is stored in MinIO
> (`s3://ml-artifacts/datasets/voc12/`), verified, and described by a flat
> key-value manifest. Everything later in the pipeline reads from here.

```
 [1] INGESTION  ->  [2] ENRICHMENT  ->  [3] SAMPLING  ->  [4] TRAINING
     (this doc)        (02)               (03)             (06)
     ->  [5] EXPORT  ->  [6] EVALUATION  ->  [7] INFERENCE  (07)
```

## 1.1 Which dataset, why

**PASCAL VOC 2012 trainval** — the canonical small public detection set:

| Property | Value |
|----------|-------|
| Images | 5,717 JPEG (under your 10k cap) |
| Annotations | 5,717 PASCAL XML files (`<object><name>`, `<bndbox>`) |
| Classes | 20 objects + background (`aeroplane … tvmonitor`) |
| Size | ~1.2 GB tarball |
| License | standard research use |

A faster alternative for a 10-minute smoke test is **COCO128** (128 images)
— ultralytics auto-downloads it inside the training job, so you can skip this
entire stage: see [06-training-cuda.md](06-training-cuda.md#smoke-training-on-coco12-skips-stages-13).

## 1.2 Where you go, and what login you need

| What | URL | Login |
|------|-----|-------|
| MinIO web console (browse / single-file upload) | <http://localhost:9001> | user `minioadmin`, password `minioadmin` |
| MinIO S3 API (host-side, for `mc` / boto3 / aws-cli) | `http://localhost:9000` | same `minioadmin` / `minioadmin` |
| The bucket | `ml-artifacts` | (auto-created by the stack on first `make up`) |

These are the MinIO *root* credentials from `.env`
(`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`). For a local stack that's all the
"credential management" you need — no IAM, no STS.

## 1.3 Download the dataset on the host

```bash
cd /run/media/shantanu/Volume/Projects/airflow-ml
bash examples/detection/download_voc12.sh
```

What it does:

1. Downloads the tarball (~1.2 GB) from the `pjreddie.com` mirror
   (`https://pjreddie.com/media/files/VOCtrainval_11-May-2012.tgz`), falling
   back to the official `host.robots.ox.ac.uk` URL.
2. Extracts `VOC2012/{JPEGImages/, Annotations/, ImageSets/}`.
3. **Verifies counts** — exits non-zero unless exactly 5,717 JPEGs, 5,717 XMLs
   and a 5,717-line `trainval.txt` are present:

```
JPEGImages: 5717 (expect 5717)
Annotations: 5717 (expect 5717)
trainval.txt lines: 5717 (expect 5717)
DOWNLOAD OK: /.../airflow-ml/voc12/VOC2012 is ready to upload (see upload_voc12.py)
```

The tarball's sha256 is printed — record it; the upload manifest stores it.

## 1.4 Upload to MinIO — three ways, pick one

### Option A (recommended): the provided Python script

Bulk-parallel upload (16 workers) + verification + manifest:

```bash
docker run --rm -v "$PWD:/host:ro" \
    ml-jobrunner:latest \
    python /host/examples/detection/upload_voc12.py /host/voc12/VOC2012
```

The job image has `boto3`; the default endpoint is the host-published
`http://localhost:9000` (override with `-e S3_ENDPOINT=... -e S3_ACCESS_KEY=...
-e S3_SECRET_KEY=...` for other MinIO deployments). Expected output:

```
uploading 11435 files (5717 jpg, 5717 xml) to s3://ml-artifacts/datasets/voc12/ ...
verified: 11436 objects under s3://ml-artifacts/datasets/voc12/
manifest written to s3://ml-artifacts/datasets/voc12/manifest.json
UPLOAD OK: 5717 images + 5717 annotations available at s3://ml-artifacts/datasets/voc12/
```

Objects land as `ml-artifacts/datasets/voc12/VOC2012/JPEGImages/*.jpg`,
`.../Annotations/*.xml`, `.../ImageSets/Main/trainval.txt` — the local tree
mirrored verbatim.

### Option B: `mc` (MinIO client) on the host

```bash
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && sudo mv mc /usr/local/bin/
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mirror ./voc12/VOC2012 local/ml-artifacts/datasets/voc12/VOC2012
mc ls --recursive local/ml-artifacts/datasets/voc12/ | wc -l     # expect 11435 + manifest
```

### Option C: MinIO web console (fine for tiny sets, impractical for 5,717 files)

1. Open <http://localhost:9001>, log in with `minioadmin` / `minioadmin`.
2. **Buckets → `ml-artifacts` → New Folder** → `datasets/voc12/VOC2012/JPEGImages`
   (and `.../Annotations`, `.../ImageSets/Main`).
3. **Upload File** into each folder — the console accepts individual files /
   small zips. For a 1.2 GB tree this is impractical; use A or B.
   You *do* want the console, though, for eyeballing and for **deleting**
   objects later (tick objects → Delete).

## 1.5 How you know the upload succeeded

Three independent checks, in increasing order of rigor:

1. **Script/CLI output** — `verified: 11436 objects` (11,435 data objects +
   the manifest) as above.
2. **Console** — browse <http://localhost:9001> → `ml-artifacts` →
   `datasets/voc12/`; you should see `VOC2012/` and `manifest.json`. Spot-open
   `VOC2012/JPEGImages/000001.jpg` (image preview) and `VOC2012/Annotations/000001.xml`.
3. **Programmatic** (host or job image):

```python
import boto3
s3 = boto3.client("s3", endpoint_url="http://localhost:9000",
                  aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin")
for pfx, expect in (("datasets/voc12/VOC2012/JPEGImages/", 5717),
                    ("datasets/voc12/VOC2012/Annotations/", 5717)):
    n = sum(len(pg.get("Contents", [])) for pg in
            s3.get_paginator("list_objects_v2").paginate(Bucket="ml-artifacts", Prefix=pfx))
    print(pfx, n, "OK" if n == expect else "MISMATCH")
print(s3.get_object(Bucket="ml-artifacts", Key="datasets/voc12/manifest.json")
      ["Body"].read().decode())
```

## 1.6 Which datasets are already uploaded (and their metadata)

**Browse** — MinIO console: `ml-artifacts/datasets/` lists every raw dataset
prefix; each one has a `manifest.json` written by its upload step.

**Programmatic listing** (any host or job context — swap the endpoint):

```python
r = s3.list_objects_v2(Bucket="ml-artifacts", Prefix="datasets/", Delimiter="/")
available = [p.rstrip("/").split("/")[-1] for p in r.get("CommonPrefixes", [])]
print("raw datasets:", available)        # e.g. ['datasets/voc12']
```

**Metadata** — the flat key-value manifest (atomic types only: str/int/bool),
as written by `upload_voc12.py`:

```json
{
  "name": "voc12",
  "dataset_kind": "detection",
  "source": "PASCAL VOC 2012 trainval",
  "source_url": "https://pjreddie.com/media/files/VOCtrainval_11-May-2012.tgz",
  "s3_prefix": "s3://ml-artifacts/datasets/voc12/VOC2012/",
  "num_images": 5717,
  "num_annotations": 5717,
  "num_classes": 20,
  "annotation_format": "PASCAL VOC XML",
  "uploaded_at": "2026-08-26T...Z",
  "uploaded_by": "upload_voc12.py"
}
```

By convention every raw dataset gets this `datasets/<name>/manifest.json`, so
"what's available + what is it" is always one `get_object` away. (The
*enriched* DeepLake side of availability — versioned datasets, commits, KV
metadata — is covered in [02-enrichment.md](02-enrichment.md#listing-what-is-in-deeplake)
and [05-data-access.md](05-data-access.md#deeplake-from-a-job).)

## 1.7 You're done with stage 1 when

- [ ] `s3://ml-artifacts/datasets/voc12/` contains the full `VOC2012/` tree (counts verified)
- [ ] `s3://ml-artifacts/datasets/voc12/manifest.json` exists with the flat KV above
- [ ] you can browse it in the MinIO console

**Next:** [Stage 2 — Enrichment](02-enrichment.md): a platform job parses the
XMLs and commits a versioned DeepLake dataset, so training never touches raw
files again.