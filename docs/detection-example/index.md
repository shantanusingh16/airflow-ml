# Object detection on the ML platform — example guide

A complete, runnable walkthrough of taking a small public object-detection
dataset (**PASCAL VOC 2012 trainval**: 5,717 images < the 10k cap, 20 classes)
through this platform: raw upload → enrichment (DeepLake) → sampling
(commit-pinned) → GPU training (PyTorch/YOLO11 + MLflow) → ONNX export →
Triton deployment → evaluation through the inference server → standalone
inference testing.

Everything referenced here is implemented: job scripts live in
[`examples/detection/`](../../examples/detection/), this guide set lives in
[`docs/detection-example/`](.), and the platform itself is the running
`airflow-ml` stack (Airflow 3 + MinIO + DeepLake + Qdrant + MLflow + Triton).

## Where am I? — the pipeline map

| # | Stage | What happens | Where you go (host URL) | Guide |
|---|-------|--------------|-------------------------|-------|
| 1 | **Ingestion** | Download VOC2012 on the host, bulk-upload raw images + XML annotations to MinIO (`ml-artifacts/datasets/voc12/`), verify, write a flat KV manifest | MinIO Console <http://localhost:9001> (or `mc` / the Python script) | [01-ingestion.md](01-ingestion.md) |
| 2 | **Enrichment** | A job parses the XML annotations and commits them as a versioned DeepLake dataset `voc12` on S3 (tensors `image_id`, `image_uri`, `class_ids`, `bboxes`, `width`, `height`, `class_names` + flat KV `ds.info`) | Job logs (Airflow UI) — no separate UI; verify via MinIO Console `deeplake/voc12/` | [02-enrichment.md](02-enrichment.md) |
| 3 | **Sampling** | Deterministic 80/20 train/val split stored as a `split` tensor + a **new DeepLake commit** — the commit id is the version all later stages pin | Airflow UI (task logs); commit visible in `deeplake/voc12` S3 objects | [03-sampling.md](03-sampling.md) |
| 4 | **Training** | `gpu_job_task` runs YOLO11n on the RTX 4090 against the pinned commit; per-epoch metrics stream to the MLflow experiment `detection_voc12` (run `train-<run_id>`) | MLflow <http://localhost:5000> · Airflow UI (GPU task logs) | [06-training-cuda.md](06-training-cuda.md) |
| 5 | **Export** | Torch → ONNX (dynamic batch) → staged into Triton's shared model repo → explicit gRPC load of `yolo_voc12` | Triton HTTP <http://localhost:8005> (no auth) | [07-export-inference.md](07-export-inference.md) |
| 6 | **Evaluation** | Val split scored twice — torch weights vs the model **served by Triton** over gRPC — with a hard `|ΔmAP50| ≤ 0.05` guard; logged as `evaluate-<run_id>` | MLflow <http://localhost:5000> | [07-export-inference.md](07-export-inference.md) |
| 7 | **Inference** | A standalone Python script (or `curl`) runs the deployed model on real images through Triton | gRPC `localhost:8000` / HTTP `localhost:8005` (no credentials — internal service) | [07-export-inference.md](07-export-inference.md) |

Two cross-cutting references (read these whenever you write your own):

- [04-custom-jobs-and-dags.md](04-custom-jobs-and-dags.md) — the job
  contract, writing job scripts, creating/editing/deleting DAGs in Airflow
  (URL + login), triggering runs, checking status and logs.
- [05-data-access.md](05-data-access.md) — from inside a job: MinIO/S3,
  DeepLake (load/commit/available datasets), Qdrant — with URIs, credentials,
  and copy-paste snippets.

## Quick reference: URLs and credentials

All values come from `.env` in the project root. Nothing here is secret —
this is a single-user local stack.

| Service | Host-side URL / address | Login | Notes |
|---------|-------------------------|-------|-------|
| **Airflow** (UI + REST API) | <http://localhost:2405> | user `airflow` / password `airflow` | DAGs, runs, task logs, grid view |
| **MinIO Console** (web UI) | <http://localhost:9001> | `minioadmin` / `minioadmin` | Browse/upload/delete objects |
| **MinIO S3 API** (host) | `http://localhost:9000` | `minioadmin` / `minioadmin` | `mc`, boto3, aws-cli |
| **MinIO S3 API** (inside containers) | `http://minio:9000` | same | what job containers use (env `S3_ENDPOINT`) |
| **MLflow** (UI + API) | <http://localhost:5000> | none | experiments, runs, artifacts |
| **Qdrant** (REST/WS) | <http://localhost:6333> | none | dashboard at <http://localhost:6333/dashboard> |
| **Qdrant** (gRPC) | `localhost:6334` | none | `qdrant-client` |
| **Triton** (HTTP inference) | <http://localhost:8005> | none | `/v2/...` endpoints |
| **Triton** (gRPC inference) | `localhost:8000` | none | `tritonclient` |
| **Triton** (metrics) | <http://localhost:8006> | none | Prometheus |
| **Flower** (task graph) | <http://localhost:5555> | none | optional |

Inside a job container the same services are reachable by name instead of
port (`minio:9000`, `mlflow:5000`, `qdrant:6333`, `triton:8000/8005`) — the
`job_task()` helper in `dags/jobtask.py` injects all of it as environment
variables (see [04](04-custom-jobs-and-dags.md#the-job-contract-env-vars-given-to-every-job)).

## What gets stored where

| Store | Path / name | Contents after a full run |
|-------|-------------|---------------------------|
| MinIO `ml-artifacts` | `datasets/voc12/VOC2012/…` | 5,717 raw JPEGs + 5,717 XMLs + `ImageSets/` |
| MinIO | `datasets/voc12/manifest.json` | flat KV upload manifest (source, counts, sha, timestamp) |
| MinIO | `deeplake/voc12/` | the enriched + split DeepLake dataset (commits, tensors, KV metadata) |
| MinIO | `data/<run_id>/` | per-stage JSON manifests: `voc12_ingest_manifest.json`, `voc12_split_manifest.json`, `yolo_train_manifest.json`, `yolo_export_manifest.json`, `yolo_eval_manifest.json`, `detection_summary.json` |
| MinIO | `models/<run_id>/yolo/` | `best.pt`, `last.pt`, `model.onnx`, `config.pbtxt`, `model_info.json`, `metrics.json`, `train_args.json`, `results.csv`, `eval_metrics.json` |
| DeepLake | `s3://ml-artifacts/deeplake/voc12` | tensors + `ds.info` (flat atomic KV) + commit history |
| Qdrant | collection `feature_vectors` | 8-dim platform demo vectors (detection example does not need it — see [05](05-data-access.md#qdrant-from-a-job)) |
| MLflow | experiment `detection_voc12` | runs `train-<run_id>` (params, per-epoch metrics, weight artifacts) and `evaluate-<run_id>` (triton-vs-torch metrics) |
| Triton | model `yolo_voc12` in `triton-models/` (bind-mounted repo) | `config.pbtxt` at model root + `1/model.onnx`; explicit model control |

## One-time setup, then run

```bash
# from the project root (stack must be up: `make up`)
bash examples/detection/download_voc12.sh                      # stage 1: host download (~1.2 GB)
docker run --rm -v "$PWD:/host:ro" \
    ml-jobrunner:latest python /host/examples/detection/upload_voc12.py /host/voc12/VOC2012
docker build -f jobrunner/Dockerfile.gpu -t ml-jobrunner-gpu:latest jobrunner/   # GPU job image
cp examples/detection/dags/detection_pipeline.py dags/
cp examples/detection/jobs/*.py dags/jobs/
DAG_ID=detection_voc12 make unpause
DAG_ID=detection_voc12 make trigger
DAG_ID=detection_voc12 make runinfo          # watch it
```

Expected: `ingest_voc12 → sample_voc12 → train_yolo → export_yolo →
eval_yolo → collect_detection_metrics` all green. Then test inference:

```bash
docker run --rm --network airflow-ml-net -v "$PWD:/host:ro" \
    -e TRITON_GRPC_URL=triton:8000 ml-jobrunner-gpu:latest \
    python /host/examples/detection/inference_yolo.py /host/voc12/VOC2012/JPEGImages/000005.jpg
```

**Full pipeline in one DAG:** `voc12_full_pipeline` runs the whole chain —
upload verify → ingest → **fastdup** DINOv2 embeddings + duplicate report
(PDF) → **DBSCAN cluster-pure** 70/10/20 split → YOLO11 train + **TIDE**
evaluation → ONNX → Triton — and leaves `infer_cli.py` able to score any
image from the host. Walkthrough + gotchas:
[08-full-pipeline-fastdup-tide.md](08-full-pipeline-fastdup-tide.md).

**Fast path (no dataset upload):** point the training job at ultralytics'
built-in `coco128` set (128 images, auto-downloaded by the job) —
[06-training-cuda.md](06-training-cuda.md#smoke-training-on-coco12-skips-stages-13)
shows the exact variant.

## Repository layout of the example

```
examples/detection/
├── download_voc12.sh            # stage 1: host download + count verification
├── upload_voc12.py              # stage 1: bulk MinIO upload + flat KV manifest
├── inference_yolo.py            # stage 7: standalone Triton inference test client (in-container, gRPC)
├── infer_cli.py                 # host-side CLI: JSON detections + annotated image (stdlib+PIL+numpy, client-side NMS)
├── dags/
│   ├── detection_pipeline.py    # original 6-stage DAG (copy into dags/ to activate)
│   └── voc12_full_pipeline.py   # full pipeline: verify→ingest→fastdup→cluster→train(TIDE)→export
└── jobs/
    ├── ingest_voc12.py          # stage 2: VOC XML -> DeepLake commit
    ├── sample_voc12.py          # stage 3: deterministic split + commit pin
    ├── verify_voc12_upload.py   # full-pipeline stage 1: raw upload completeness check
    ├── embed_voc12.py           # full-pipeline stage 3: fastdup DINOv2 embeddings + PDF report
    ├── cluster_split_voc12.py   # full-pipeline stage 4: DBSCAN cluster-pure 70/10/20
    ├── train_eval_tide_voc12.py # full-pipeline stage 5: YOLO11 train + TIDE eval (MLflow)
    ├── train_yolo_voc12.py      # stage 4: YOLO11n on GPU + MLflow
    ├── export_yolo_onnx.py      # stage 5: ONNX export + Triton deploy (gRPC)
    ├── eval_yolo_voc12.py       # stage 6: torch vs Triton mAP50 + guard
    └── collect_detection_metrics.py  # final cross-store verification