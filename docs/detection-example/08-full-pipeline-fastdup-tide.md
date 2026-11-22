# Full pipeline — fastdup data quality, cluster-pure splits, TIDE evaluation

This is the end-to-end detection pipeline as a single DAG: **one trigger
runs the whole chain** — upload verification → DeepLake ingest → fastdup
DINOv2 embeddings + duplicate analysis (PDF report) → DBSCAN cluster-pure
70/10/20 split → YOLO11 training + TIDE-framework evaluation (MLflow) →
ONNX export → Triton deployment — and leaves the model inferable from the
host with a tiny stdlib-only client.

Implemented in:

- DAG: `examples/detection/dags/voc12_full_pipeline.py`
  (deploy to `dags/` as `voc12_full_pipeline`)
- Jobs: `examples/detection/jobs/{verify_voc12_upload,ingest_voc12,
  embed_voc12,cluster_split_voc12,train_eval_tide_voc12,
  export_yolo_onnx}.py` (deploy to `dags/jobs/`)
- Host CLI: `examples/detection/infer_cli.py`

Prerequisites (stages 1–2 of this guide series): the VOC2012 raw upload in
`ml-artifacts/datasets/voc12/` (see [01-ingestion.md](01-ingestion.md)) and
the `ml-jobrunner-gpu:latest` image built (see
[06-training-cuda.md](06-training-cuda.md)).

## The pipeline

```
verify_upload ──► ingest_voc12 ──► embed_fastdup ──► cluster_split
   (CPU)            (CPU)             (GPU)              (GPU)
                                              │
                                              ▼
                                   export_triton ◄── train_tide
                                    (GPU)            (GPU)
```

| # | Task (image) | What it does | Where to see it |
|---|--------------|--------------|-----------------|
| 1 | `verify_upload` (CPU) | Lists the raw upload in MinIO: ≥ `MIN_IMAGES` JPEGs, XML count == JPEG count, `trainval.txt` line count == JPEG count. Fails fast on a partial stage-1 upload. | task log: `UPLOAD OK: …` |
| 2 | `ingest_voc12` (CPU) | Rebuilds the DeepLake dataset `voc12` from scratch on S3: parses every XML, commits tensors `image_id`, `image_uri`, `class_ids`, `bboxes`, `width`, `height` (per image, 5717 rows) + `class_names` (per class, 20 rows) + KV `num_images`/`num_boxes`/… and publishes `data/<run_id>/voc12_ingest_manifest.json` | MinIO `deeplake/voc12/`; task log: `INGEST OK: …` |
| 3 | `embed_fastdup` (GPU) | Runs **fastdup 2.54** (DINOv2, 576-dim) over every image: embeddings + similarity graph + connected components (= duplicate groups) + plain attributes (file size, brightness, mean RGB). Commits `dinov2_embedding`, `is_duplicate`, `dup_group`, `file_size`, `brightness`, `mean_r/g/b` as a **new commit** and renders a 4-page **PDF report** (summary, PCA scatter colored by dup group, dup table + most-similar pair, attribute histograms) to `s3://ml-artifacts/analysis/<run_id>/voc12_embed_report.pdf` | MinIO `analysis/<run_id>/`; task log: `EMBED OK: …` |
| 4 | `cluster_split` (GPU) | DBSCAN (`eps=0.15`, `min_samples=5`) over the DINOv2 embeddings; **whole clusters** are assigned to train/val/test at 70/10/20 — no image ever crosses two splits, so near-duplicates can never leak between train and test. Commits `cluster_id`, `split3` (train/val/test) and `split` (platform 2-way convention: val = val3+test3) | task log: split table; MinIO `deeplake/voc12/` |
| 5 | `train_tide` (GPU) | YOLO11n, 30 epochs @640, batch 16, trained on `train3`, validated on `val3`, then evaluated on **both** `val3` and `test3` with TIDE-framework metrics: 101-point mAP50 (per class + mean) and TIDE10/20/50 (localization-threshold error analysis), plus an operating point (conf ≥ 0.25, NMS IoU 0.45, per-class NMS) → precision/recall. Everything logged to MLflow experiment `detection_voc12` (run `train-<run_id>`); best weights + `yolo_train_manifest.json` (with `class_names`) published to S3 | MLflow <http://localhost:5000>; task log: `TRAIN+EVAL OK … mAP50=…` |
| 6 | `export_triton` (GPU) | `best.pt` → ONNX (dynamic batch, 640×640) → staged into the shared Triton model repo → explicit gRPC load of `yolo_voc12` (onnxruntime backend) → verified ready; publishes `yolo_export_manifest.json` + `model_info.json` (input/output dims + class names) into `triton-models/yolo_voc12/` | Triton <http://localhost:8005>; `docker compose logs triton` |

After a green run, infer from the **host** (no torch needed):

```
python3 examples/detection/infer_cli.py /path/to/image.jpg
```

prints a JSON dict with every detection (class, confidence, bbox) and writes
an annotated copy `<stem>_detected.jpg`. See
[07-export-inference.md](07-export-inference.md) for the raw-triton
alternative.

## Running it

```
cp examples/detection/dags/voc12_full_pipeline.py dags/
cp examples/detection/jobs/{verify_voc12_upload,ingest_voc12,embed_voc12,cluster_split_voc12,train_eval_tide_voc12,export_yolo_onnx}.py dags/jobs/
DAG_ID=voc12_full_pipeline make unpause && DAG_ID=voc12_full_pipeline make trigger
```

or `POST /api/v2/dags/voc12_full_pipeline/dagRuns` with a `logical_date`
(see [04-custom-jobs-and-dags.md](04-custom-jobs-and-dags.md)).

Expected wall time on this stack: verify ~1 min, ingest ~1 min, embed
~5–15 min, cluster ~1–2 min, train ~30–60 min, export ~5 min.

## Results (run `manual_20260827T000500Z`, 2026-08-27)

End-to-end verified run on this stack (RTX 4090, Airflow 3.3.1):

| Stage | Result |
|-------|--------|
| `verify_upload` | 11,435 raw objects in `datasets/voc12/VOC2012/` = 5,717 JPEG + 5,717 XML; `trainval.txt` lists all 5,717 images → `UPLOAD OK` |
| `ingest_voc12` | 5,717 images, 15,774 boxes → DeepLake `s3://ml-artifacts/deeplake/voc12` (rebuild commit); manifest `data/<run_id>/voc12_ingest_manifest.json` |
| `embed_fastdup` | fastdup 2.54 DINOv2, 576-dim, **0 duplicate groups** (all 5,717 images unique); committed `dinov2_embedding`, `is_duplicate`, `dup_group`, `file_size`, `brightness`, `mean_r/g/b`; 4-page PDF report at `s3://ml-artifacts/analysis/<run_id>/voc12_embed_report.pdf` (summary / PCA-by-dup-group / dup table / attribute histograms) |
| `cluster_split` | DBSCAN(eps=0.15, min_samples=5) on cosine distance → 20 clusters → whole-cluster split **train 3,890 / val 621 / test 1,206** (68.0% / 10.9% / 21.1% of 5,717); no image crosses two splits |
| `train_tide` | YOLO11n, 30 epochs @640, batch 16 (328 s on the 4090). Ultralytics val: **mAP50 = 0.517**, mAP50-95 = 0.390. TIDE framework (per-class NMS): val3 mAP50 = 0.386 (TIDE10/20/50 = 0.383/0.383/0.385); **test3 mAP50 = 0.508 (TIDE10/20/50 = 0.507/0.506/0.507)**, operating point conf ≥ 0.25. Logged to MLflow experiment `detection_voc12`, run `train-<run_id>` (per-epoch metrics + `best.pt`/`last.pt`/`results.csv` artifacts) |
| `export_triton` | `best.pt` → ONNX (dynamic batch/height/width/anchors) → Triton 26.07 model **`yolo_voc12`** (onnxruntime, `max_batch_size 16`, config at model root), explicit gRPC load + verified ready; gRPC smoke inference returns `(2, 24, 8400)` |

Host-side inference (no torch/ultralytics — stdlib + PIL + numpy + requests, NMS
client-side because the deployed ONNX head is NMS-free), real VOC image
`2008_000008.jpg` (rider on a horse):

```
$ python3 examples/detection/infer_cli.py 2008_000008.jpg
{
  "model": "yolo_voc12", "conf_threshold": 0.25, "nms_iou": 0.45,
  "num_detections": 3,
  "detections": [
    {"class_id": 12, "class": "horse",   "confidence": 0.9548, "bbox": [54.6, 76.7, 484.7, 441.0]},
    {"class_id": 14, "class": "person",  "confidence": 0.9397, "bbox": [155.4, 41.0, 286.9, 167.3]},
    {"class_id": 1,  "class": "bicycle", "confidence": 0.6273, "bbox": [425.0, 247.0, 467.6, 304.2]}
  ],
  "output_image": "2008_000008_detected.jpg"
}
```

The same pipeline was also executed through the Airflow platform
(`voc12_full_pipeline` trigger run: all 6 tasks green), which runs the
identical job scripts via `job_task()`/`gpu_job_task()` DockerOperator tasks.

## Gotchas found while building this (all fixed in the deployed jobs)

1. **Future `start_date` ⇒ phantom "success" runs.** If a DAG's
   `start_date` is *in the future* (e.g. `datetime(2026, 8, 27)` while today
   is 2026-08-26), Airflow 3.3.1 manual runs of that DAG finish as
   `success` with **zero task instances** in a few milliseconds — the run is
   never associated with a DAG version. The DAG parses fine, the stored
   serialized version is fine, and CPU-only DAGs with past `start_date`s run
   normally, which makes this look like a DAG-specific bug. Use a past
   `start_date`. (Reproduced and verified with a one-task probe DAG.)
2. **fastdup resolves annotation filenames against the process CWD.** The
   C++ engine only finds `input_dir` images when the process runs *from
   inside* that directory; job containers start in `/`, so `embed_voc12.py`
   does `os.chdir(IMGS_DIR)` before `fastdup.create/run`.
3. **DeepLake `len(ds)` returns the *smallest* tensor.** The `voc12` dataset
   mixes per-image tensors (5717 rows) with the per-class `class_names`
   tensor (20 rows) — by design. Iterate `range(len(ds["image_id"]))`, never
   `range(len(ds))`.
4. **`deeplake.empty()` on an existing S3 path raises.** The ingest job
   passes `overwrite=True` (rebuild-from-scratch semantics).
5. **numpy 2 vs DeepLake 3.9: `extend()` numpy arrays, not `.tolist()`.**
   DeepLake's `intelligent_cast` rejects Python ints/floats under NEP 50
   (`can_cast() does not support Python ints`); pass `np.ndarray`s.
6. **`runner.py` used to swallow `sys.exit("message")`** (string exit codes
   became a silent exit 1). It now prints the message to stderr before
   exiting.
7. **The deployed YOLO11 ONNX is the raw detection head** (`[1, 4+20, 8400]`,
   no NMS op — Triton's onnxruntime backend has no NMS). The host CLI decodes
   + NMSes client-side; see the CLI section of
   [07-export-inference.md](07-export-inference.md).
8. **matplotlib `PdfPages` + pyplot figures:** use `pdf.savefig(fig)`, never
   `fig.savefig(pdf)` — pyplot figures carry an Agg canvas with no
   `print_pdf`, so `fig.savefig(pdf)` falls back to the PNG path and crashes
   on the `PdfPages` object; also never pass `bbox_inches="tight"` to a
   `PdfPages` target (forces the same PNG path).
9. **Triton config: `backend`, not `platform`.** `onnxruntime` is a backend;
   writing `platform: "onnxruntime"` makes the model repo poll fail with
   `unexpected platform type 'onnxruntime'` and `LoadModel` with
   `failed to poll from model repository`. Dynamic graph dims map to Triton
   flexible dims (`-1`), not `0`.
10. **tritonclient's `get_model_repository_index()` hardcodes
   `IndexModelRepository(ready=False)`**, which can leave the server's repo
   snapshot stale after re-staging a model; the export job calls the raw RPC
   with `ready=True` (`client._client_stub.RepositoryIndex(...)`) before
   `load_model`, and clears any pre-existing model directory first.