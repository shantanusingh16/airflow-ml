# t_29094ca2 / impl-2

## Prompt as dispatched

````
---
factory:
  base: factory/t_29094ca2/impl-1
---
# impl-2 — t_29094ca2: harden the jobrunner pin set (EGM review findings)

Project: airflow-ml. Your checkout is at `factory/t_29094ca2/impl-1` (the base
for this window). The previous window already pinned numpy/pillow/scikit-learn/
pandas and rewrote both Dockerfiles. EGM (Claude) reviewed that result and
returned REQUEST CHANGES with two blocking defects plus one strongly-recommended
hardening. You must apply the three fixes below, EXACTLY as specified.

## Findings to fix

**B1 (blocking) — the fastdup METADATA normalisation line targets a file that
does not exist.** `Distribution.locate_file(path)` resolves paths against the
PARENT of the `.dist-info` directory (i.e. site-packages), not against the
dist-info itself. So `distribution('fastdup').locate_file('METADATA')` returns
`.../site-packages/METADATA`, which does not exist, and `read_text()` raises
`FileNotFoundError` — the RUN step fails and so does the build.
Fix: address the METADATA file via the dist-info path itself:
`Path(distribution('fastdup')._path) / 'METADATA'` (`_path` is the dist-info
directory; stable across the Python versions in our pinned base images).
Also add asserts so a mismatched replacement string fails the build loudly
instead of silently doing nothing.

**B2 (blocking) — layer order lets ultralytics pull in numpy 2.** In the
current `Dockerfile.gpu` the `ultralytics==8.4.129` layer runs BEFORE
`opencv-python==4.10.0.84` is installed. At the ultralytics layer the only
opencv constraint pip sees is `opencv-python>=4.7.0,!=4.13.0.90`, so pip picks
the newest 4.12+ release, which declares `numpy>=2,<2.3` and upgrades numpy
from 1.26.4 to 2.x. The later opencv layer cannot put it back. That is exactly
the card's original failure.
Fix: install `opencv-python==4.10.0.84` (and the apt libGL/libglib2.0-0 layer)
BEFORE the ultralytics layer. With 4.10.0.84 already installed, ultralytics'
requirement is satisfied by the installed version and numpy stays at 1.26.4.

**B3 (strongly recommended) — floating transitive deps can re-break the pins.**
Every unconstrained `pip install` layer resolves its unpinned transitive
deps to their newest releases. Verified on PyPI (2026-11-22, from the
packages' own METADATA):
- `pillow_heif` 1.8.1 (newest) requires `pillow>=11.1.0` — ALL 1.x releases
  do; the last release accepting pillow 10.x is **0.22.0** (`pillow>=10.1.0`).
  It has cp311 and cp312 manylinux_2_17 x86_64 wheels (verified). Without a
  pin, the fastdup-deps layer would upgrade pillow past deeplake's
  `pillow~=10.4.0` requirement.
- `scipy` 1.18.x (newest) requires `numpy>=2.0.0`; 1.17.x requires
  `numpy>=1.26.4` (exact-boundary); **1.16.3** requires `numpy>=1.25.2,<2.6`
  (comfortable margin) and has cp311/cp312 manylinux2014 x86_64 wheels
  (verified). scipy reaches both images via scikit-learn and mlflow.
- `matplotlib` 3.11.2 (newest, pulled by ultralytics) requires only
  `numpy>=1.25, pillow>=9` — compatible, no action needed.
- `pyarrow` 26.0.1 (newest, pulled by mlflow) declares no numpy/pillow
  requirement — compatible, no action needed.

Fix: introduce a shared `jobrunner/constraints.txt` pinning the whole
scientific stack, COPY it into the image, and pass `-c /constraints.txt` to
EVERY `pip install` (except the `pip install --upgrade pip` step and the
`--no-deps fastdup` step, which resolve nothing). With the constraints in
place, pip backtracks unpinned transitive deps to compatible older releases
instead of upgrading the pinned stack. The same file keeps CPU and GPU
lock-step.

## EXACT target contents

Replace the two Dockerfiles with exactly the content below and CREATE
`jobrunner/constraints.txt` with exactly the content below. Do not reformat,
do not add or remove lines, do not "improve" anything else.

### FILE 1: jobrunner/constraints.txt (NEW)

```
# Shared constraints for the job-runner images (Dockerfile + Dockerfile.gpu).
#
# t_29094ca2: the GPU image is forced to numpy<2 by fastdup 2.54 (its final
# release) and deeplake 3.9.52 requires pillow~=10.4.0. Every `pip install`
# in both Dockerfiles passes this file with `-c`, so unpinned transitive
# dependencies (scipy, pillow-heif, matplotlib, pyarrow, ...) can only
# resolve to releases compatible with the pins below: pip backtracks to
# older releases instead of silently upgrading the stack.
#
# Keep the CPU and GPU images in lock-step: change this file only together
# with both Dockerfiles.
numpy==1.26.4
pillow==10.4.0
scikit-learn==1.5.0
pandas==2.3.2
scipy==1.16.3
opencv-python==4.10.0.84
pillow-heif==0.22.0
```

### FILE 2: jobrunner/Dockerfile (CPU)

```
# Job-runner image: the shared workload image for the airflow-ml stack.
#
# Dual-mode, orchestrator-agnostic:
#   1. Airflow DockerOperator jobs — the DAG passes the full command:
#        python /runner.py <job-script.py> [job-args ...]
#      (see dags/jobtask.py; there is intentionally NO ENTRYPOINT so that ...).
#   2. Ray nodes (KubeRay on k8s, docker-based Ray clusters, ...) supply their
#      own command, e.g. `ray start --head --port=6379 ...` or `python job.py`.
#      Ray version is pinned here and must match the version of every node in
#      the cluster (see ray/raycluster.yaml).
#
# Extend the pip install below with whatever your jobs need
# (torch, xgboost, ...). Keep it lean-ish: the image is rebuilt with
# `docker compose --profile build build jobrunner` and reused by all jobs.
#
# The shared scientific stack (numpy/pillow/scikit-learn/pandas/scipy) is
# constrained identically in this file and in Dockerfile.gpu via
# constraints.txt (t_29094ca2), so the CPU and GPU job images stay in
# lock-step: the GPU image is forced to numpy<2 (fastdup 2.54) and
# pillow==10.4.0 (deeplake 3.9.52), and this image follows the same pins,
# so job artifacts behave identically on both.
FROM python:3.12-slim

# Shared constraints (t_29094ca2): every pip install below passes this file,
# so unpinned transitive dependencies cannot upgrade the pinned stack.
COPY constraints.txt /constraints.txt

RUN pip install --no-cache-dir --upgrade pip && \
    # staged installs: a single 12-package resolution pass exceeds pip's
    # resolver depth (tritonclient[all] + ray + mlflow graphs are deep)
    pip install --no-cache-dir -c /constraints.txt \
        "numpy==1.26.4" \
        "pandas==2.3.2" \
        "scikit-learn==1.5.0" \
        "pillow==10.4.0" \
        "boto3" \
        "requests" && \
    pip install --no-cache-dir -c /constraints.txt "deeplake==3.9.52" && \
    pip install --no-cache-dir -c /constraints.txt "mlflow==3.15.1" && \
    pip install --no-cache-dir -c /constraints.txt \
        "onnx==1.19.1" \
        "onnxruntime==1.19.2" \
        "skl2onnx==1.20.0" && \
    pip install --no-cache-dir -c /constraints.txt "qdrant-client==1.16.2" && \
    pip install --no-cache-dir -c /constraints.txt "tritonclient[all]==2.71.0" && \
    pip install --no-cache-dir -c /constraints.txt "ray[default]==2.58.0"   # [default] adds the dashboard deps so `ray start --include-dashboard` / `ray job submit` work on KubeRay nodes
COPY runner.py /runner.py
# Gate: fail the build if any installed package declares an unsatisfied
# requirement (mirrors Dockerfile.gpu; catches dependency drift).
RUN pip check
# Smoke test: import the shared stack so a broken pin fails the build here,
# not at job time.
RUN python -c "import numpy, pandas, sklearn, scipy, deeplake, mlflow, onnx"
# NOTE: no ENTRYPOINT on purpose (dual-mode image, see header comment).
```

### FILE 3: jobrunner/Dockerfile.gpu

```
# ml-jobrunner-gpu: CUDA variant of the job-runner image.
#
# Same job contract as jobrunner/Dockerfile (env-driven, stdio, no
# ENTRYPOINT, same service endpoints) plus torch (CUDA 12.8) + ultralytics
# for GPU training / export / eval jobs (see examples/detection/).
#
#   build:  docker build -f jobrunner/Dockerfile.gpu -t ml-jobrunner-gpu:latest jobrunner/
#   use:    gpu_job_task("train_yolo_voc12.py", job_id="train_yolo") in a DAG
#           (dags/jobtask.py passes device_requests=[DeviceRequest(count=1,
#           capabilities=[["gpu"]])] + shm_size to the container)
#
# Host prerequisite (already satisfied on this machine — verify with):
#   docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
# The base image bundles Python 3.11 (conda) and torch 2.7.1+cu12.8; the
# pip stack below is kept in lock-step with jobrunner/Dockerfile.
#
# Why the pins below (numpy/fastdup/pillow conflict, card t_29094ca2):
#   numpy==1.26.4    fastdup 2.54 (its final release) pins numpy<2.0. Newer
#                    scipy/opencv releases declare numpy>=2, so the shared
#                    constraints.txt (passed via `-c` to every pip install)
#                    keeps every layer on 1.26.4.
#   pillow==10.4.0   exactly what deeplake 3.9.52 requires (pillow~=10.4.0).
#                    fastdup declares Pillow==10.3.0, a test-time pin that
#                    the voc12 pipeline ran fine past in production; it is
#                    normalized in fastdup's installed metadata (see below).
#                    pillow-heif is constrained to 0.22.0 — the last release
#                    that accepts pillow 10.x (all 1.x releases require
#                    pillow>=11.1.0).
#   scikit-learn==1.5.0  fastdup's exact pin; pandas==2.3.2 is pre-3.0 and
#                    compatible with fastdup 2.54 / scikit-learn 1.5.0.
#   scipy==1.16.3    newest scipy whose numpy range (>=1.25.2,<2.6) covers
#                    1.26.4 (scipy 1.18.x requires numpy>=2.0.0).
#   opencv-python==4.10.0.84 (GUI build)  the package NAME ultralytics
#                    8.4.129 requires (headless does not satisfy it). 4.12+
#                    demands numpy 2 on all pythons; 4.10.x still accepts
#                    numpy 1.x. apt libGL/libglib make `import cv2` work
#                    headless. It MUST be installed before ultralytics (see
#                    layer order below).
FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

# Keep pins identical to jobrunner/Dockerfile (one package group per layer so
# a cache hit covers the unchanged lower layers). The shared constraints.txt
# is passed to every pip install so unpinned transitive dependencies (scipy,
# pillow-heif, matplotlib, ...) cannot pull in releases that break the
# pinned stack.
COPY constraints.txt /constraints.txt
RUN pip install --no-cache-dir --upgrade pip
# Shared scientific set — identical pins to jobrunner/Dockerfile (lock-step)
RUN pip install --no-cache-dir -c /constraints.txt numpy==1.26.4 pillow==10.4.0 scikit-learn==1.5.0 pandas==2.3.2
RUN pip install --no-cache-dir -c /constraints.txt deeplake==3.9.52
RUN pip install --no-cache-dir -c /constraints.txt mlflow==3.15.1
RUN pip install --no-cache-dir -c /constraints.txt onnx==1.19.1 onnxruntime==1.19.2 skl2onnx==1.20.0
RUN pip install --no-cache-dir -c /constraints.txt qdrant-client==1.16.2
RUN pip install --no-cache-dir -c /constraints.txt "tritonclient[all]==2.71.0"
RUN pip install --no-cache-dir -c /constraints.txt "ray[default]==2.58.0"
# GUI OpenCV must exist BEFORE ultralytics is installed (B2, t_29094ca2):
# ultralytics requires the package NAME `opencv-python` (>=4.7.0,
# !=4.13.0.90). If it were not installed yet, pip would resolve that
# requirement to the newest 4.12+ release, which declares numpy>=2 and
# would upgrade numpy from 1.26.4 to 2.x — exactly the failure this card
# fixes. The base image has no X11 libs; these make `import cv2` work
# without a display (server container).
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# 4.10.0.84: last release of the 4.10 line; still numpy-1 compatible,
# satisfies ultralytics' >=4.7.0,!=4.13.0.90.
RUN pip install --no-cache-dir -c /constraints.txt opencv-python==4.10.0.84
# Object-detection stack (YOLOv8/YOLO11 family; pulls in matplotlib —
# all reused by the example jobs). opencv-python is already pinned above, so
# ultralytics' requirement is satisfied by the installed 4.10.0.84 and
# numpy stays at 1.26.4.
RUN pip install --no-cache-dir -c /constraints.txt ultralytics==8.4.129
# fastdup 2.54 is the LAST fastdup release and pins Pillow==10.3.0 and
# opencv-python-headless>=4.8.0.0, both of which collide with this stack
# (deeplake 3.9.52 needs pillow~=10.4.0; ultralytics needs opencv-python).
# Install it without its pins, normalize exactly those two requirements in
# its installed metadata so `pip check` reflects the compatible reality,
# then install its remaining runtime dependencies normally (all compatible
# with the pins above; pillow-heif is constrained to 0.22.0, the last
# release that accepts pillow 10.x).
RUN pip install --no-cache-dir --no-deps fastdup==2.54
# Normalize the two colliding pins in fastdup's installed METADATA.
# NOTE: importlib.metadata's Distribution.locate_file() is anchored at
# site-packages (the PARENT of the dist-info dir), so the METADATA file must
# be addressed through the dist-info path itself (`_path`) — this is what
# B1 of the EGM review caught. After this edit fastdup's RECORD hashes no
# longer match its METADATA: that is intentional and harmless, `pip check`
# ignores RECORD and uninstall/reinstall still work — do not "repair" it.
RUN python -c "from pathlib import Path; from importlib.metadata import distribution; p = Path(distribution('fastdup')._path) / 'METADATA'; t = p.read_text(); assert t.count('Requires-Dist: Pillow==10.3.0') == 1, 'fastdup METADATA: Pillow pin not found'; assert t.count('Requires-Dist: opencv-python-headless>=4.8.0.0') == 1, 'fastdup METADATA: opencv pin not found'; p.write_text(t.replace('Requires-Dist: Pillow==10.3.0', 'Requires-Dist: Pillow>=10.3.0').replace('Requires-Dist: opencv-python-headless>=4.8.0.0', 'Requires-Dist: opencv-python>=4.8.0.0'))"
RUN pip install --no-cache-dir -c /constraints.txt "pyOpenSSL>=24.0.0" cryptography "joblib~=1.2.0" "PyYAML~=6.0" "requests>=2.32.4" "setuptools==78.1.1" "sentry-sdk==2.27.0" "tqdm==4.66.3" psutil pillow_heif packaging
COPY runner.py /runner.py
# Gate: fail the build if any installed package declares an unsatisfied
# requirement — this is what catches numpy/pillow/opencv drift.
RUN pip check
# Smoke test: import the GPU stack so a broken pin fails the build here,
# not at job time.
RUN python -c "import numpy, cv2, fastdup, ultralytics, deeplake"

# No ENTRYPOINT: the DAG's DockerOperator passes the explicit command
# ["python", "/runner.py", <script>]; Ray/K8s pass their own.
```

## Rules

1. Write the three files EXACTLY as above (byte-identical, including the
   trailing-newline situation: end each file with a single trailing newline).
   The build context for both images is the `jobrunner/` directory, so
   `COPY constraints.txt ...` works as written.
2. Touch ONLY `jobrunner/Dockerfile`, `jobrunner/Dockerfile.gpu`, and the
   new `jobrunner/constraints.txt`. Do not modify anything else (no .env/*,
   no .factory/*, no dags/*, no docker-compose.yml, no docker/).
3. This sandbox has no docker and no network: do NOT build the images, do
   NOT pip install anything, do not run pip check. Your job is the three
   file edits.
4. When the files are written, commit them on the current branch with the
   message: `jobrunner: shared constraints + opencv layer order + metadata path fix (t_29094ca2)`
5. Verify before finishing: re-read all three files and diff them against
   the spec above character by character; the inline `python -c` line in
   Dockerfile.gpu must contain exactly one backslash-free, dollar-free,
   double-quoted shell command with single-quoted Python strings.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/omp",
  "artifacts": [],
  "base_ref": "factory/t_29094ca2/impl-1",
  "base_sha": "b5f3036a81bddd73d32eee3ea3223afe4f341a1c",
  "binary": "/home/dev-runner/.local/bin/omp",
  "branch": "factory/t_29094ca2/impl-2",
  "executor": {
    "image": "localhost/factory-runner@sha256:469e88d8ef36f40a287cae4e0fc8defcea71b25524a5a8f84dfa6986cea4f426",
    "isolation": "container",
    "key": "sandbox",
    "kind": "podman",
    "limits": {
      "cpus": "4",
      "memory": "8g",
      "pids": 4096,
      "shm": "64m"
    },
    "services": {
      "comfyui": {
        "port": 8188
      },
      "h3-jobs": {
        "port": 8288
      },
      "llama-swap": {
        "port": 8080
      }
    },
    "via": "policy_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_29094ca2--impl-2.exit",
  "function": "bugfix_loop",
  "harness": "omp",
  "home_seed": [
    ".omp/agent/models.yml",
    ".omp/agent/config.yml",
    ".omp/agent/mcp.json",
    ".omp/plugins",
    ".pi/agent/pi-llama-swap.json"
  ],
  "install_roots": [
    "/home/dev-runner/.local",
    "/home/dev-runner/.omp/mcp",
    "/run/media/shantanu/Volume/Tools/pi-llama-swap"
  ],
  "job_dir": "/srv/factory-jobs/t_29094ca2--impl-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_29094ca2--impl-2.md",
  "prompt_sha256_prefix": "fa29c5fdf0f20f2c",
  "resolved_via": "function_default",
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [],
  "spec_sha256": "77a872a4ce953649ec7b7b2e521a8993731f59f05919ae5cab49c0ee725d2864",
  "ticket": "t_29094ca2",
  "transcript": "/srv/factory-jobs/t_29094ca2--impl-2/transcript.log",
  "transcript_sha256": "57fb8fc1f91e79a08f4f2cf0597416f35968a639bc7af12830a850da968d752d",
  "window": "impl-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
