# Stages 5–7 — Export to Triton, evaluation, inference testing

> **You are at the final third of the pipeline.** Stage 5 exports the trained
> torch model to ONNX and deploys it to the Triton server (`yolo_voc12`,
> explicit model control over gRPC). Stage 6 proves the *served* model
> matches the trained one (mAP50 on the val split, torch vs Triton, hard
> guard). Stage 7 is you, with a custom Python script, running the deployed
> model on real images.

## 5. Stage 5 — export + deploy (`export_yolo_onnx.py`)

Runs in the GPU image (torch needed for the export). Steps:

1. Downloads `best.pt` (from the train stage's S3 manifest).
2. `model.export(format="onnx", imgsz=640, dynamic=True)` → ONNX with a
   dynamic batch dim: input `[None, 3, 640, 640]` FP32, output
   `[None, 21, 8400]` FP32 (YOLO11: 4 box coords + 20 class scores,
   no objectness head, over 8400 anchor slots at 640²).
3. Uploads `model.onnx` → `s3://ml-artifacts/models/<run_id>/yolo/`.
4. Generates `config.pbtxt` and stages it **atomically** into the shared
   Triton model repository (`triton-models/`, bind-mounted into both the
   triton service and every job container):

   ```
   triton-models/yolo_voc12/
   ├── config.pbtxt          # Triton 26.x layout: config at the MODEL ROOT
   ├── model_info.json       # input/output dims + class count (for clients)
   └── 1/
       └── model.onnx        # version 1
   ```

   ```text
   name: "yolo_voc12"
   platform: "onnxruntime"
   max_batch_size: 16            # batch dim is implicit → config dims are
   input  [ { name: "images",  data_type: TYPE_FP32, dims: [3,640,640] } ]
   output [ { name: "output0", data_type: TYPE_FP32, dims: [21,8400] } ]
   ```

   Two layout facts that cost real debugging time (both verified against the
   running 26.07 server): a `config.pbtxt` *inside the version dir is
   silently ignored* (the server auto-completes a config with
   `max_batch_size: 4` and your 16-row inference batches 404), and with
   `max_batch_size > 0` the batch dim must **not** appear in `dims`.
5. Explicit model control **over gRPC** (`tritonclient.grpc` against
   `triton:8000`) — the 26.07 HTTP `POST /v2/models/<name>/load` endpoint
   returns 404 even for existing models (server regression), while
   `get_model_repository_index` / `unload_model` / `load_model` /
   `is_model_ready` all work over gRPC: index (retried up to 60 s for the
   new model to appear) → unload (tolerated) → load → ready poll.
6. **Config verification loop:** poll `GET /v2/models/yolo_voc12/config`
   (HTTP works fine for reads) until `max_batch_size == 16`; otherwise
   re-index + reload (deadline 90 s). This is the guard against the stale
   auto-completed-config failure mode.
7. gRPC smoke inference (batch of zeros) → `EXPORT OK: 'yolo_voc12' live on
   Triton (gRPC triton:8000)`.

**Where you go to check:** Triton HTTP <http://localhost:8005> —
`/v2/health/ready`, `/v2/models/yolo_voc12/ready`,
`/v2/models/yolo_voc12/config` (no login; the server is unauthenticated by
design on an internal network). No credentials exist for Triton — the
"auth" story is network placement (published ports on localhost only).

## 6. Stage 6 — evaluation (`eval_yolo_voc12.py`)

The decisive check that *the served artifact is the trained model*:

1. Torch side: `YOLO(best.pt).val(val split)` → `mAP50`, `mAP50-95`,
   precision, recall (letterbox preprocessing, ultralytics' own matching).
2. Triton side: every val image is preprocessed in pure numpy/OpenCV
   (resize 640², BGR→RGB, /255, CHW FP32), sent to the **deployed ONNX
   model in batches of 16 over gRPC**, the raw `[1+K, A]` output is decoded
   (sigmoid-guarded class scores, box decode, numpy NMS @ 0.45) and mAP50 is
   computed in numpy against the same GT (101-point interpolated AP, VOC
   style). No torch on that inference path — exactly what a production
   client would do.
3. **Hard guard:** `|mAP50_triton − mAP50_torch| ≤ 0.05` or the task fails
   the run. (Measured deltas in practice are ~1e-4 — FP32 export noise.)
4. Publishes `models/<run_id>/yolo/eval_metrics.json` (per-class AP table
   included) + `data/<run_id>/yolo_eval_manifest.json`, and logs MLflow run
   `evaluate-<run_id>` in experiment `detection_voc12` (tag
   `inference_backend=triton`) with both metric families + the delta.

**Where you go to check:** MLflow <http://localhost:5000> → experiment
`detection_voc12` → the `evaluate-…` run (metrics: `map50_triton`,
`map50_torch`, `map50_delta`).

## 7. Stage 7 — run the deployed model with your own script

The provided client (`examples/detection/inference_yolo.py`) does: server
live check → model ready check → read `model_info.json` (input/output names
+ dims — works for *any* detection model you deploy this way) → preprocess
your image → gRPC `infer` → decode + NMS → print detections with class
names, boxes mapped back to original image coordinates.

**From the project host** (recommended; no host Python packages needed —
the GPU job image carries `tritonclient` + OpenCV):

```bash
cd /run/media/shantanu/Volume/Projects/airflow-ml
docker run --rm --network airflow-ml-net \
    -v "$PWD:/host:ro" \
    -e TRITON_GRPC_URL=triton:8000 -e TRITON_DET_MODEL=yolo_voc12 \
    ml-jobrunner-gpu:latest \
    python /host/examples/detection/inference_yolo.py \
    /host/voc12/VOC2012/JPEGImages/000005.jpg \
    /host/voc12/VOC2012/JPEGImages/000032.jpg
```

Sample output:

```
model: yolo_voc12 @ triton:8000 | input {'name': 'images', 'dims': [0, 3, 640, 640]} | 20 classes | conf>=0.25 iou<=0.45

== 000005.jpg (640x427) : 2 detections
   person     0.842  box=[  312.4  118.7  401.9  402.6]
   person     0.611  box=[  452.0  151.3  520.8  405.1]
== 000032.jpg (500x375) : 1 detections
   car        0.733  box=[   84.2  130.5  401.7  272.9]

3 total detections via Triton (yolo_voc12)
```

**From a host Python venv** (pure-localhost variant):

```bash
python3 -m venv .venv-infer && .venv-infer/bin/pip install "tritonclient[all]" opencv-python
TRITON_GRPC_URL=localhost:8000 MODELS_ROOT=triton-models \
    .venv-infer/bin/python examples/detection/inference_yolo.py voc12/VOC2012/JPEGImages/000005.jpg
```

**Plain HTTP instead of gRPC** (any language, e.g. `curl`) — binary input
as base64, output as base64:

```bash
# input: FP32 tensor [1,3,640,640] little-endian, base64-encoded
B64=$(python3 -c "import base64,numpy as np; print(base64.b64encode(np.zeros((1,3,640,640),dtype='float32').tobytes()).decode())")
curl -s http://localhost:8005/v2/models/yolo_voc12/infer -H 'Content-Type: application/json' \
  -d "{\"model_name\":\"yolo_voc12\",\"inputs\":[{\"name\":\"images\",\"shape\":[1,3,640,640],\"binary_data\":[\"$B64\"]}]}" \
  | head -c 400
```

(For real images, generate the base64 payload from your preprocessed
tensor; the gRPC client does this for you.)

## 8. The whole pipeline, end to end (fresh state)

```bash
cd /run/media/shantanu/Volume/Projects/airflow-ml
make up                                    # stack already running? `make status`
bash examples/detection/download_voc12.sh                    # stage 1 (first time)
docker run --rm -v "$PWD:/host:ro" ml-jobrunner:latest \
    python /host/examples/detection/upload_voc12.py /host/voc12/VOC2012
docker build -f jobrunner/Dockerfile.gpu -t ml-jobrunner-gpu:latest jobrunner/   # once
cp examples/detection/dags/detection_pipeline.py dags/
cp examples/detection/jobs/*.py dags/jobs/
DAG_ID=detection_voc12 make unpause
DAG_ID=detection_voc12 make trigger
DAG_ID=detection_voc12 make runinfo       # watch until all 6 tasks green
docker run --rm --network airflow-ml-net -v "$PWD:/host:ro" \
    -e TRITON_GRPC_URL=triton:8000 ml-jobrunner-gpu:latest \
    python /host/examples/detection/inference_yolo.py /host/voc12/VOC2012/JPEGImages/000005.jpg
```

**Verification matrix — where each claim is checked** (the final task
`collect_detection_metrics` automates most of this and fails the run on any
gap; it publishes `data/<run_id>/detection_summary.json`):

| Claim | Check | Where |
|-------|-------|-------|
| raw dataset uploaded | 11,435 objects + manifest | MinIO console <http://localhost:9001> → `ml-artifacts/datasets/voc12/` |
| enriched dataset | rows/tensors/commits/`ds.info` | job probe (§2.4 of [02](02-enrichment.md)) or `deeplake/voc12/` in the console |
| split pinned | commit id in `voc12_split_manifest.json` | console → `data/<run_id>/` |
| training progress + results | `train-<run_id>` run | MLflow <http://localhost:5000> → `detection_voc12` |
| model deployed | `/v2/models/yolo_voc12/ready` = 200, config `max_batch_size: 16` | <http://localhost:8005> |
| served == trained | `map50_delta` ≤ 0.05 | `models/<run_id>/yolo/eval_metrics.json` + `evaluate-<run_id>` in MLflow |
| inference works | detections printed on real VOC images | the `inference_yolo.py` run above |
| cross-store consistency | `detection_summary.json` with empty `problems` | console → `data/<run_id>/` |

That's the whole loop: **raw bytes → versioned dataset → commit-pinned
training → tracked experiment → ONNX on Triton → guarded evaluation →
your own inference script** — every hop verifiable at a URL.