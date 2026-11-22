# Stage 4 — Training a detection model with CUDA (PyTorch + YOLO11 + MLflow)

> **You are at stage 4 of 7.** Outcome: `yolo11n` fine-tuned on the
> commit-pinned VOC2012 split **on the RTX 4090**, with per-epoch metrics
> streaming to the MLflow experiment `detection_voc12`, and weights + results
> published to S3 for the export stage.

## 4.1 GPU prerequisites on this host (already satisfied — verify once)

| Check | Command | Result on this machine |
|-------|---------|------------------------|
| GPU + driver | `nvidia-smi` | RTX 4090, driver 595.84 |
| nvidia-container-toolkit | `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` | prints the GPU → containers can see it |
| GPU job image | `docker images ml-jobrunner-gpu` | built below |

If the `docker run … nvidia-smi` check fails on another host: install
`nvidia-container-toolkit` (`sudo apt install nvidia-container-toolkit &&
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl reload
docker`) — nothing in this platform changes, only the host.

**Build the GPU job image** (one-time; ~5 min, ~15 GB):

```bash
cd /run/media/shantanu/Volume/Projects/airflow-ml
docker build -f jobrunner/Dockerfile.gpu -t ml-jobrunner-gpu:latest jobrunner/
```

It's the CPU `ml-jobrunner` stack (deeplake, mlflow, onnx/onnxruntime,
qdrant-client, tritonclient, ray) on top of
`pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime` (Python 3.11, torch
2.7.1+cu12.8) plus `ultralytics==8.4.129` + `opencv-python-headless`.
Same job contract, no ENTRYPOINT. Verified end-to-end: CUDA visible inside
the container + a real `YOLO('yolo11n.pt').predict(...)` run on the 4090.

## 4.2 How the DAG requests the GPU

`dags/jobtask.py` provides `gpu_job_task()` — `job_task()` plus
`device_requests=[DeviceRequest(count=1, capabilities=[["gpu"]])]` (this
provider's `DockerOperator` 4.5.9 exposes `--gpus` as `device_requests`, not
a `gpus=` kwarg) and `shm_size="16g"` (torch DataLoader workers need
/dev/shm; the default 64 MB OOMs mid-epoch):

```python
from jobtask import gpu_job_task
train = gpu_job_task("train_yolo_voc12.py", job_id="train_yolo",
                     extra_env={...}, timeout=7200)
# multi-GPU host: gpu_job_task(..., device_count=2); specific cards: pass
# device_requests=[DeviceRequest(device_ids=["1"], capabilities=[["gpu"]])] yourself
```

The job itself fails **loud and early** if CUDA isn't actually visible
(`sys.exit("CUDA is not visible …")`) — so a misconfigured task is a red
task, never a silently slow CPU run.

## 4.3 What `train_yolo_voc12.py` does

`examples/detection/jobs/train_yolo_voc12.py` (runs in `ml-jobrunner-gpu`):

1. **Pin the data.** Reads `data/<run_id>/voc12_split_manifest.json` →
   `commit_id` → `deeplake.load(f"{VOC12_DATASET}@{commit_id}",
   read_only=True)` — training runs on exactly the sampled version, never on
   "latest".
2. **Materialize.** Streams the needed JPEGs from MinIO into the container
   (`/tmp/voc12/raw/`, symlinked per split) and writes YOLO label files
   (`cls cx cy w h`, normalized) **from the DeepLake tensors** — the
   enrichment payoff: zero re-parsing of raw XML.
3. **Train.** `YOLO("yolo11n.pt")` (pretrained weights auto-download on
   first run — job containers have internet; offline? pre-stage the `.pt` to
   `datasets/voc12/weights/` and load that path) →
   `model.train(data=…, epochs=EPOCHS, imgsz=640, batch=16, device=0, …)`.
4. **Track in MLflow** — experiment `detection_voc12`, run
   `train-<run_id>`:

   - `log_params`: model, imgsz, epochs, batch, GPU name, **dataset +
     commit_id**, class count, torch version;
   - a `on_train_epoch_end` callback streams every epoch's validation
     metrics (`mAP50`, `mAP50-95`, precision, recall, …) via
     `mlflow.log_metrics(…, epoch=N)`;
   - final validation metrics + artifacts: `best.pt`, `last.pt`,
     `results.csv`, `data.yaml`.
5. **Publish.** `best.pt`, `last.pt`, `results.csv`, `data.yaml`,
   `train_args.json`, `metrics.json` → `s3://ml-artifacts/models/<run_id>/yolo/`,
   plus `data/<run_id>/yolo_train_manifest.json` (commit id, S3 paths, final
   metrics, class names) — the export/eval stages read this.

## 4.4 Watching training progress — which URL you go to

| What to watch | Where | What you'll see |
|---------------|-------|-----------------|
| **Metrics over time** (the good one) | MLflow <http://localhost:5000> → **Experiments → `detection_voc12` → run `train-<run_id>`** | per-epoch curves (`mAP50`, `mAP50-95`, `precision`, `recall`, …), params, artifacts tab (weights, `results.csv`) — no login (server has no auth) |
| Live training log (loss, lr, epoch lines) | Airflow UI <http://localhost:2405> → `detection_voc12` → run → `train_yolo` → **Details → Logs** (auto-scroll) — or `docker logs -f <container>` | ultralytics' per-epoch table; the job's own `print`s (commit pinned, materialization stats, CUDA check) |
| GPU utilization (host) | `watch -n 2 nvidia-smi` | the container's PIDs using the 4090; util ~90–100% while an epoch runs, dips between epochs |
| Run health | `DAG_ID=detection_voc12 make runinfo` | `train_yolo: running/success/failed` |

**You know training succeeded when:** the task is green **and**
- `TRAIN OK: {'map50': 0.8x, …} (commit …, mlflow run …)` is in the log,
- MLflow shows `train-<run_id>` as FINISHED with the metrics curves,
- `models/<run_id>/yolo/best.pt` exists in the MinIO console.

Typical numbers on this stack: 5,717 images @ 640², batch 16, yolo11n on a
4090 ≈ 1–2 min/epoch → 30 epochs ≈ 30–60 min. mAP50-95 of a few epochs of
yolo11n on VOC2012 lands around 0.4–0.5 (mAP50 ~0.7+); more epochs → closer
to the paper numbers.

## 4.5 Writing your own PyTorch training job

Everything except the model code is the same contract
([04-custom-jobs-and-dags.md §3](04-custom-jobs-and-dags.md#3-writing-a-custom-job-script)):

```python
import os
import torch, mlflow
# torch-only skeleton (your own model/dataset loop instead of ultralytics)
assert torch.cuda.is_available(), "run me with gpu_job_task()"
dev = torch.device(int(os.environ.get("GPU_DEVICE", "0")))

mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment("my_experiments")
with mlflow.start_run(run_name=f"train-{os.environ['RUN_ID']}"):
    mlflow.log_params({"model": "resnet50", "epochs": 10, "commit": COMMIT_ID})
    for epoch in range(10):
        loss = train_one_epoch(model, dataloader, dev)   # DataLoader(num_workers>0
        val = evaluate(model, val_loader, dev)           # works: shm_size=16g is set)
        mlflow.log_metrics({"loss": loss, **val}, epoch=epoch + 1)
    torch.save(model.state_dict(), "/tmp/model.pt")
    mlflow.log_artifact("/tmp/model.pt")
    # ...and publish to S3 models/<RUN_ID>/ for the export stage
```

Practical notes:
- `device` selection: `device=0` / `torch.cuda.set_device(N)`;
  `CUDA_VISIBLE_DEVICES` (pass via `extra_env`) can restrict which card the
  container sees.
- Keep the **MLflow batch discipline of this platform**: one run per
  (stage, run_id) — `train-<run_id>` for training, a separate
  `evaluate-<run_id>` for inference-time evaluation (stage 6 does exactly
  this, mirroring the platform's `ml_pipeline` experiment convention).
- Long jobs: raise the task's `timeout=` (DAG level), e.g. 7200 s.

## 4.6 Smoke training on COCO128 (skips stages 1–3)

To validate the full GPU path in ~10 minutes without uploading VOC2012:
run `train_yolo_voc12.py`-style code with `data="coco128.yaml"`
(ultralytics downloads the 128-image set + labels into the container),
`epochs=3`. Everything else — GPU task, MLflow tracking, S3 publishing —
is identical. (The platform's DeepLake/Qdrant stages stay VOC-centric in
this guide; coco128 simply bypasses them.)

## 4.7 Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Task fails: `CUDA is not visible in this container` | task created with `job_task()` instead of `gpu_job_task()`, or host lacks nvidia-container-toolkit (§4.1) |
| `RuntimeError: CUDA out of memory` | lower `BATCH` (env) or `IMGSZ`; check `nvidia-smi` while running |
| Slow: GPU at 0% | data pipeline is the bottleneck — the job streams from MinIO on first run; reruns are faster (local `/tmp` is wiped per container, so it re-streams — on a slow MinIO raise the S3 client's connection pool / pre-stage to a host bind mount via `extra_env`) |
| First run hangs on weight download | job containers have NAT internet; if yours doesn't, pre-download `yolo11n.pt` to S3 `datasets/` and load that path |
| Nothing in MLflow UI | `MLFLOW_TRACKING_URI` env (injected by `job_task`) must be reachable — job containers use `http://mlflow:5000`; check the mlflow service is up (`make status`) |

**Next:** [Stage 5–7 — export, evaluation, and inference testing](07-export-inference.md).